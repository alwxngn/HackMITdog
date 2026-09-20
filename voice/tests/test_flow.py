import os
import io
import wave
import unittest
from unittest.mock import AsyncMock, call, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from voice.app import app, sessions
from voice import providers


class CheckinTests(unittest.TestCase):
    def setUp(self):
        sessions.clear()
        self.client = TestClient(app)
        self.credentials = self.client.post('/api/sessions', json={'patient': 'Arthur', 'caregiver': 'Sarah'}).json()
        self.id = self.credentials['session_id']
        self.headers = {'Authorization': 'Bearer ' + self.credentials['caregiver_token']}
        self.phone_headers = {'Authorization': 'Bearer ' + self.credentials['phone_token']}

    def phone(self):
        return self.client.websocket_connect(f'/ws/{self.id}/phone')

    def ready(self, ws):
        ws.send_json({'token': self.credentials['phone_token']})
        self.assertFalse(ws.receive_json()['phone_ready'])
        ws.send_json({'type': 'ready'})
        self.assertTrue(ws.receive_json()['phone_ready'])

    def checkin(self, text=''):
        return self.client.post(f'/api/sessions/{self.id}/checkins', json={'text': text}, headers=self.headers)

    def test_full_checkin_delivery_and_patient_reply(self):
        with self.phone() as ws:
            self.ready(ws)
            result = self.checkin()
            self.assertEqual(result.status_code, 202)
            first = ws.receive_json()
            self.assertEqual(first['type'], 'say')
            self.assertIn('Sarah asked me', first['payload']['text'])
            self.assertEqual(ws.receive_json()['checkin']['status'], 'sent')
            ws.send_json({'type':'playback', 'utterance_id':first['payload']['utterance_id'], 'state':'delivered'})
            self.assertEqual(ws.receive_json()['checkin']['status'], 'delivered')
            ws.send_json({'type':'transcript', 'text':'Are you Sarah?', 'turn_id':'turn1', 'checkin_id':result.json()['checkin_id']})
            response = ws.receive_json()
            self.assertIn("view your message", response['payload']['text'])
            state = ws.receive_json()
            self.assertEqual(state['checkin']['status'], 'responded')
            self.assertEqual([e['type'] for e in state['events']], ['checkin','say','speech_state','transcript','say'])
            self.assertNotIn('phone_token', state)

    def test_phone_can_send_robot_command_transcript_without_checkin(self):
        with self.phone() as ws:
            self.ready(ws)
            ws.send_json({'type': 'transcript', 'text': 'Take me for a walk', 'turn_id': 'walk-1'})
            state = ws.receive_json()
            self.assertEqual(state['events'][-1]['type'], 'transcript')
            self.assertEqual(state['events'][-1]['payload']['text'], 'Take me for a walk')
            self.assertNotIn('checkin_id', state['events'][-1]['payload'])

    def test_offline_and_unstarted_phone_cannot_receive_checkins(self):
        self.assertEqual(self.checkin().status_code, 409)
        with self.phone() as ws:
            ws.send_json({'token':self.credentials['phone_token']})
            ws.receive_json()
            self.assertEqual(self.checkin().status_code, 409)

    def test_credentials_isolate_sessions_and_roles(self):
        path = f'/api/sessions/{self.id}/checkins'
        self.assertEqual(self.client.post(path, json={}, headers=self.phone_headers).status_code, 403)
        other = self.client.post('/api/sessions', json={}).json()
        self.assertEqual(self.client.post(path, json={}, headers={'Authorization':'Bearer ' + other['caregiver_token']}).status_code, 403)
        with self.phone() as ws:
            ws.send_json({'token':self.credentials['caregiver_token']})
            with self.assertRaises(WebSocketDisconnect) as caught:
                ws.receive_json()
            self.assertEqual(caught.exception.code, 4403)

    def test_duplicate_phone_is_rejected_without_disconnecting_original(self):
        with self.phone() as first:
            self.ready(first)
            with self.phone() as second:
                second.send_json({'token':self.credentials['phone_token']})
                with self.assertRaises(WebSocketDisconnect) as caught:
                    second.receive_json()
                self.assertEqual(caught.exception.code, 4409)
            self.assertEqual(self.checkin().status_code, 202)

    def test_busy_delivery_stale_ack_duplicate_transcript_and_attention(self):
        with self.phone() as ws:
            self.ready(ws)
            result = self.checkin('Thinking of you.').json()
            speech = ws.receive_json()['payload']
            ws.receive_json()
            self.assertEqual(self.checkin().status_code, 409)
            ws.send_json({'type':'transcript', 'text':'I need help', 'turn_id':'one', 'checkin_id':result['checkin_id']})
            ws.receive_json()
            state = ws.receive_json()
            self.assertTrue(state['checkin']['needs_attention'])
            self.assertEqual(state['checkin']['status'], 'responded')
            ws.send_json({'type':'playback', 'utterance_id':speech['utterance_id'], 'state':'delivered'})
            ws.send_json({'type':'transcript', 'text':'I need help', 'turn_id':'one', 'checkin_id':result['checkin_id']})
            ws.send_json({'type':'ping'})
            self.assertEqual(ws.receive_json()['type'], 'pong')
            self.assertEqual(len([e for e in sessions[self.id].events if e['type'] == 'transcript']), 1)

    def test_disconnect_never_marks_pending_audio_delivered(self):
        with self.phone() as ws:
            self.ready(ws)
            self.checkin()
            ws.receive_json(); ws.receive_json()
        self.assertFalse(sessions[self.id].ready)
        self.assertEqual(sessions[self.id].checkin['status'], 'unavailable')
        with self.phone() as ws:
            ws.send_json({'token':self.credentials['phone_token']})
            self.assertEqual(ws.receive_json()['type'], 'snapshot')
            ws.send_json({'type':'ping'})
            self.assertEqual(ws.receive_json()['type'], 'pong') # no automatic speech replay

    def test_stale_reply_does_not_attach_to_new_checkin(self):
        with self.phone() as ws:
            self.ready(ws)
            first = self.checkin().json()
            speech = ws.receive_json()['payload']; ws.receive_json()
            ws.send_json({'type':'playback', 'state':'delivered', 'utterance_id':speech['utterance_id']})
            ws.receive_json()
            self.checkin('A new message')
            ws.receive_json(); ws.receive_json()
            ws.send_json({'type':'transcript', 'text':'old response', 'turn_id':'late', 'checkin_id':first['checkin_id']})
            ws.send_json({'type':'ping'})
            self.assertEqual(ws.receive_json()['type'], 'pong')
            self.assertFalse(any(e['type'] == 'transcript' for e in sessions[self.id].events))

    def test_audio_provider_auth_limits_and_failure(self):
        path = f'/api/sessions/{self.id}/transcribe'
        self.assertEqual(self.client.post(path, content=b'audio').status_code, 403)
        self.assertEqual(self.client.post(path, content=b'audio', headers={**self.phone_headers,'Content-Type':'text/plain'}).status_code, 415)
        self.assertEqual(self.client.post(path, content=b'', headers={**self.phone_headers,'Content-Type':'audio/mp4'}).status_code, 400)
        with patch('voice.providers.transcribe', new=AsyncMock(return_value='Hello')):
            response = self.client.post(path, content=b'audio', headers={**self.phone_headers,'Content-Type':'audio/mp4'})
            self.assertEqual(response.json(), {'text':'Hello'})

    def test_voice_consent_is_required_before_provider_call(self):
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY':'test','ELEVENLABS_VOICE_ID':'test','ELEVENLABS_VOICE_CONSENT':'false'}):
            self.assertEqual(providers.capabilities()['tts'], 'browser')
            import asyncio
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(providers.synthesize('Hello'))
            self.assertEqual(caught.exception.status_code, 503)

    def test_speech_retry_reuses_audio_and_rechecks_consent(self):
        env = {'ELEVENLABS_API_KEY':'test', 'ELEVENLABS_VOICE_ID':'test', 'ELEVENLABS_VOICE_CONSENT':'true'}
        with patch.dict(os.environ, env), patch('voice.providers.synthesize', new=AsyncMock(return_value=b'mp3')) as synth:
            with self.phone() as ws:
                self.ready(ws)
                self.checkin()
                speech = ws.receive_json()['payload']; ws.receive_json()
                path = f"/api/sessions/{self.id}/speech/{speech['utterance_id']}"
                first = self.client.post(path, headers=self.phone_headers)
                second = self.client.post(path, headers=self.phone_headers)
                self.assertEqual(first.content, b'mp3')
                self.assertEqual(second.content, b'mp3')
                self.assertEqual(first.headers['content-type'], 'audio/mpeg')
                synth.assert_awaited_once()
                with patch.dict(os.environ, {'ELEVENLABS_VOICE_CONSENT':'false'}):
                    self.assertEqual(self.client.post(path, headers=self.phone_headers).status_code, 503)

    def test_html_is_available_and_name_input_is_validated(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/phone').status_code, 200)
        self.assertEqual(self.client.post('/api/sessions', json={'patient':'<script>'}).status_code, 422)
        self.assertEqual(self.client.post('/api/sessions', json={'patient':'   '}).status_code, 422)

    def test_two_voices_form_one_complete_wav_and_retry_preserves_format(self):
        env = {'ELEVENLABS_API_KEY': 'test', 'ELEVENLABS_VOICE_ID': 'agent', 'ELEVENLABS_VOICE_CONSENT': 'true'}
        intro, body = b'\x01\x00' * 24000, b'\x02\x00' * 48000
        with patch.dict(os.environ, env), \
             patch.object(app.state, 'patient_voice_id', lambda: 'clone', create=True), \
             patch('voice.providers.synthesize', new=AsyncMock(side_effect=[intro, body])) as synth:
            with self.phone() as ws:
                self.ready(ws)
                self.checkin('See you soon.')
                speech = ws.receive_json()['payload']; ws.receive_json()
                path = f"/api/sessions/{self.id}/speech/{speech['utterance_id']}"
                first = self.client.post(path, headers=self.phone_headers)
                second = self.client.post(path, headers=self.phone_headers)
                self.assertEqual(first.status_code, 200)
                self.assertEqual(first.headers['content-type'], 'audio/wav')
                self.assertEqual(second.headers['content-type'], 'audio/wav')
                self.assertEqual(second.content, first.content)
                with wave.open(io.BytesIO(first.content)) as audio:
                    self.assertEqual(audio.getframerate(), 24000)
                    self.assertEqual(audio.getnchannels(), 1)
                    self.assertEqual(audio.getsampwidth(), 2)
                    self.assertEqual(audio.getnframes(), 72000)
                    self.assertEqual(audio.readframes(72000), intro + body)
                self.assertEqual(synth.await_args_list, [
                    call('Sarah sent you this message:', 'agent', output_format='pcm_24000'),
                    call('See you soon.', 'clone', output_format='pcm_24000'),
                ])

    def test_failed_custom_voice_never_returns_intro_only_audio(self):
        env = {'ELEVENLABS_API_KEY': 'test', 'ELEVENLABS_VOICE_ID': 'agent', 'ELEVENLABS_VOICE_CONSENT': 'true'}
        with patch.dict(os.environ, env), \
             patch.object(app.state, 'patient_voice_id', lambda: 'clone', create=True), \
             patch('voice.providers.synthesize', new=AsyncMock(side_effect=[b'\x01\x00', HTTPException(502, 'Retry')])):
            with self.phone() as ws:
                self.ready(ws)
                self.checkin('See you soon.')
                speech = ws.receive_json()['payload']; ws.receive_json()
                response = self.client.post(f"/api/sessions/{self.id}/speech/{speech['utterance_id']}", headers=self.phone_headers)
                self.assertEqual(response.status_code, 502)
                self.assertIsNone(sessions[self.id].speech_cache)

    def test_lantern_response_uses_default_voice_with_clone_configured(self):
        env = {'ELEVENLABS_API_KEY': 'test', 'ELEVENLABS_VOICE_ID': 'agent', 'ELEVENLABS_VOICE_CONSENT': 'true'}
        with patch.dict(os.environ, env), \
             patch.object(app.state, 'patient_voice_id', lambda: 'clone', create=True), \
             patch('voice.providers.synthesize', new=AsyncMock(return_value=b'mp3')) as synth:
            with self.phone() as ws:
                self.ready(ws)
                checkin = self.checkin().json()
                greeting = ws.receive_json()['payload']; ws.receive_json()
                response = self.client.post(f"/api/sessions/{self.id}/speech/{greeting['utterance_id']}", headers=self.phone_headers)
                self.assertEqual(response.status_code, 200)
                synth.assert_awaited_once_with(greeting['text'], 'agent')
                ws.send_json({'type': 'playback', 'utterance_id': greeting['utterance_id'], 'state': 'delivered'})
                ws.receive_json()
                ws.send_json({'type': 'transcript', 'text': 'I feel fine', 'turn_id': 'reply1', 'checkin_id': checkin['checkin_id']})
                reply = ws.receive_json()['payload']; ws.receive_json()
                self.assertIn('view your message', reply['text'])
                synth.reset_mock()
                response = self.client.post(f"/api/sessions/{self.id}/speech/{reply['utterance_id']}", headers=self.phone_headers)
                self.assertEqual(response.status_code, 200)
                synth.assert_awaited_once_with(reply['text'], 'agent')


if __name__ == '__main__':
    unittest.main()

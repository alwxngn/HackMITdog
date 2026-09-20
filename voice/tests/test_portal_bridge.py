"""Integration with E3's real bus/store; isolated temporary event log."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from voice.app import app as voice_app, sessions


class PortalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.voice_state = dict(voice_app.state._state)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cloud' / 'server'))
        import main
        import voice_bridge
        self.main = main
        voice_bridge.install_voice(main.app)
        self.store_state = dict(main.store.__dict__)
        self.handlers = list(main.bus._handlers)
        main.bus._handlers = []
        self.temp = tempfile.TemporaryDirectory()
        main.store.__init__(Path(self.temp.name) / 'events.jsonl')
        # Onboarding values, not the voice prototype's defaults.
        main.store.projection['config'] = copy.deepcopy(main.store.projection['config'])
        main.store.projection['config']['patient']['preferred_name'] = 'Pat'
        sessions.clear()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.main.bus._handlers = self.handlers
        self.main.store.__dict__.clear()
        self.main.store.__dict__.update(self.store_state)
        voice_app.state._state.clear()
        voice_app.state._state.update(self.voice_state)
        sessions.clear()
        self.temp.cleanup()
        sys.path.pop(0)

    def test_phone_events_reach_existing_portal_timeline(self):
        credentials = self.client.post('/voice/api/sessions', json={}).json()
        sid = credentials['session_id']
        headers = {'Authorization':'Bearer ' + credentials['caregiver_token']}
        with self.client.websocket_connect(f'/voice/ws/{sid}/phone') as phone:
            phone.send_json({'token':credentials['phone_token']})
            phone.receive_json()
            phone.send_json({'type':'ready'}); phone.receive_json()
            result = self.client.post(f'/voice/api/sessions/{sid}/checkins', headers=headers, json={'from_name':'Michael'})
            self.assertEqual(result.status_code, 202)
            say = phone.receive_json()['payload']; phone.receive_json()
            self.assertIn('Hi Pat.', say['text'])
            self.assertIn('Michael asked me', say['text'])
            phone.send_json({'type':'playback', 'utterance_id':say['utterance_id'], 'state':'delivered'})
            phone.receive_json()
            phone.send_json({'type':'transcript', 'turn_id':'one', 'checkin_id':result.json()['checkin_id'], 'text':'I feel fine'})
            phone.receive_json(); phone.receive_json()
            projection = self.client.get('/api/snapshot').json()['payload']
            self.assertEqual(projection['last_transcript']['text'], 'I feel fine')
            self.assertEqual(projection['speech_state'], 'idle')
            self.assertEqual(len([e for e in projection['timeline'] if e['type'] == 'checkin']), 1)
            self.assertEqual(len([e for e in projection['timeline'] if e['type'] == 'transcript']), 1)
            self.assertEqual(len([e for e in projection['timeline'] if e['type'] == 'say']), 2)
            # Existing E3 config and map endpoints remain usable.
            self.assertEqual(self.client.post('/api/config', json={'patient':{'preferred_name':'Ada'}}).status_code, 200)
            self.assertEqual(self.client.post('/api/map-scan', json={'mode':'demo'}).status_code, 200)

    def test_phone_asset_paths_are_mounted_and_old_caregiver_redirects(self):
        response = self.client.get('/voice/phone')
        self.assertIn('/voice/assets/phone.js', response.text)
        self.assertNotIn('class="orb"', response.text)
        self.assertEqual(self.client.get('/voice/assets/phone.js').status_code, 200)
        self.assertEqual(self.client.get('/voice/', follow_redirects=False).headers['location'], '/')

    def test_safety_event_blocks_checkin(self):
        credentials = self.client.post('/voice/api/sessions', json={}).json()
        self.main.store.projection['agent_state']['state'] = 'LEAD'
        response = self.client.post(f"/voice/api/sessions/{credentials['session_id']}/checkins", json={},
                                    headers={'Authorization':'Bearer ' + credentials['caregiver_token']})
        self.assertEqual(response.status_code, 409)
        self.assertIn('safety event', response.json()['detail'])

    def test_robot_requests_forward_once_and_checkin_replies_stay_local(self):
        credentials = self.client.post('/voice/api/sessions', json={}).json()
        sid = credentials['session_id']
        with patch.object(self.main.bus, '_forward_orch', new_callable=AsyncMock) as forward:
            with self.client.websocket_connect(f'/voice/ws/{sid}/phone') as phone:
                phone.send_json({'token': credentials['phone_token']}); phone.receive_json()
                phone.send_json({'type': 'ready'}); phone.receive_json()
                checkin = self.client.post(f'/voice/api/sessions/{sid}/checkins', json={},
                    headers={'Authorization': 'Bearer ' + credentials['caregiver_token']}).json()
                phone.receive_json(); phone.receive_json()
                phone.send_json({'type': 'transcript', 'text': "let's go on a walk", 'turn_id': 'robot1', 'checkin_id': ''})
                state = phone.receive_json()
                self.assertEqual(state['checkin']['status'], 'sent')
                forward.assert_awaited_once()
                event = forward.call_args.args[0]
                self.assertNotIn('checkin_id', event['payload'])
                self.assertTrue(forward.call_args.kwargs['required'])
                # The hub's echoed transcript must not be forwarded again.
                self.client.post('/api/ingest', json=event)
                forward.assert_awaited_once()
                phone.send_json({'type': 'transcript', 'text': "let's go on a walk", 'turn_id': 'reply1', 'checkin_id': checkin['checkin_id']})
                phone.receive_json(); phone.receive_json()
                forward.assert_awaited_once()

    def test_robot_delivery_failure_is_reported_and_not_replayed(self):
        credentials = self.client.post('/voice/api/sessions', json={}).json()
        sid = credentials['session_id']
        with patch.object(self.main.bus, '_orch_url', ''):
            with self.client.websocket_connect(f'/voice/ws/{sid}/phone') as phone:
                phone.send_json({'token': credentials['phone_token']}); phone.receive_json()
                phone.send_json({'type': 'ready'}); phone.receive_json()
                phone.send_json({'type': 'transcript', 'text': "let's go on a walk", 'turn_id': 'robot1'})
                error = phone.receive_json()
                self.assertEqual(error['type'], 'error')
                self.assertIn('not configured', error['message'])
                with patch.object(self.main.bus, '_forward_orch', new_callable=AsyncMock) as forward:
                    phone.send_json({'type': 'ready'}); phone.receive_json()
                    forward.assert_not_awaited()

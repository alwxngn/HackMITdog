import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from voice import providers


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_deepgram_receives_audio_and_credentials_on_server(self):
        response = httpx.Response(200, json={'results':{'channels':[{'alternatives':[{'transcript':'Hello Susan'}]}]}}, request=httpx.Request('POST', 'https://api.deepgram.com/v1/listen'))
        with patch.dict(os.environ, {'DEEPGRAM_API_KEY':'test-secret'}), patch('voice.providers.httpx.AsyncClient') as client:
            post = client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
            self.assertEqual(await providers.transcribe(b'recorded-audio', 'audio/mp4'), 'Hello Susan')
            self.assertEqual(post.call_args.kwargs['content'], b'recorded-audio')
            self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Token test-secret')

    async def test_elevenlabs_receives_voice_and_returns_mp3(self):
        env = {'ELEVENLABS_API_KEY':'test-secret', 'ELEVENLABS_VOICE_ID':'approved-voice', 'ELEVENLABS_VOICE_CONSENT':'true'}
        response = httpx.Response(200, content=b'mp3', request=httpx.Request('POST', 'https://api.elevenlabs.io'))
        with patch.dict(os.environ, env), patch('voice.providers.httpx.AsyncClient') as client:
            post = client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
            self.assertEqual(await providers.synthesize('Hello'), b'mp3')
            self.assertTrue(post.call_args.args[0].endswith('/approved-voice'))
            self.assertEqual(post.call_args.kwargs['json']['text'], 'Hello')

    async def test_provider_rejection_is_actionable_and_does_not_leak_body(self):
        response = httpx.Response(401, text='sensitive upstream details', request=httpx.Request('POST', 'https://api.deepgram.com'))
        with patch.dict(os.environ, {'DEEPGRAM_API_KEY':'test-secret'}), patch('voice.providers.httpx.AsyncClient') as client:
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
            with self.assertRaises(HTTPException) as caught:
                await providers.transcribe(b'wave', 'audio/wav')
            self.assertIn('credentials', caught.exception.detail)
            self.assertNotIn('sensitive', caught.exception.detail)
            self.assertNotIn('test-secret', caught.exception.detail)

    def test_disabled_voice_has_explanation(self):
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY':'test', 'ELEVENLABS_VOICE_ID':'test', 'ELEVENLABS_VOICE_CONSENT':'false'}):
            self.assertTrue(any('ELEVENLABS_VOICE_CONSENT' in note for note in providers.configuration_notes()))

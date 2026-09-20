"""Onboarding upload regression tests with a mocked ElevenLabs service."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import main


class VoiceCloneTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.headers = {'Content-Type': 'audio/webm'}

    def test_empty_recording_is_rejected_before_provider_call(self):
        with patch('voice.providers.clone_voice', new_callable=AsyncMock) as clone:
            response = self.client.post('/api/onboarding/voice-clone', content=b'',
                                        headers={'Content-Type': 'audio/webm'})
            self.assertEqual(response.status_code, 400)
            clone.assert_not_awaited()

    def test_provider_errors_do_not_publish_configuration(self):
        for status, message, expected in [
            (401, 'Your subscription requires an upgrade for instant voice cloning.', 402),
            (401, 'Invalid API key', 401),
            (403, 'Missing voices_write permission', 403),
            (429, 'Rate limited', 429),
            (503, 'Unavailable', 502),
        ]:
            with self.subTest(status=status, message=message):
                upstream = httpx.Response(status, json={'detail': {'message': message}},
                    request=httpx.Request('POST', 'https://api.elevenlabs.io/v1/voices/add'))
                with patch.dict('os.environ', {'ELEVENLABS_API_KEY': 'test-key'}), \
                     patch('voice.providers.httpx.AsyncClient') as client, \
                     patch.object(main.bus, 'publish', new_callable=AsyncMock) as publish:
                    client.return_value.__aenter__.return_value.post = AsyncMock(return_value=upstream)
                    response = self.client.post('/api/onboarding/voice-clone',
                        headers=self.headers, content=b'mocked-microphone-audio')
                    self.assertEqual(response.status_code, expected)
                    if expected == 402:
                        self.assertIn('Starter', response.json()['detail'])
                    publish.assert_not_awaited()

    def test_success_publishes_existing_voice_contract(self):
        original = copy.deepcopy(main.store.projection)
        with patch('voice.providers.clone_voice', new_callable=AsyncMock, return_value='clone-id') as clone, \
             patch.object(main.bus, 'publish', new_callable=AsyncMock) as publish:
            response = self.client.post('/api/onboarding/voice-clone?name=Sarah',
                headers=self.headers, content=b'mocked-microphone-audio')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'voice_id': 'clone-id'})
            clone.assert_awaited_once_with('Sarah', b'mocked-microphone-audio', 'audio/webm')
            event = publish.call_args.args[0]
            self.assertEqual(event['type'], 'config_update')
            self.assertEqual(event['payload']['voice']['attribution_name'], 'Sarah')
            self.assertGreater(event['payload']['voice']['consent_recorded_ts'], 0)
            self.assertEqual(main.store.projection, original)


if __name__ == '__main__':
    unittest.main()

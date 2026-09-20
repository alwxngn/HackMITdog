"""Real browser decoding/playback with synthetic audio and a mocked microphone."""
import io
from pathlib import Path
import unittest
import wave

from playwright.sync_api import sync_playwright, expect


class PlaybackHandoffTests(unittest.TestCase):
    def test_listening_waits_for_both_voice_segments(self):
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b'\x01\x00' * 24000 + b'\x02\x00' * 48000)
        static = Path(__file__).resolve().parents[1] / 'static'
        common = '''
            export const BASE = '';
            export const $ = id => document.getElementById(id);
            export const showError = message => { if (message) window.errors.push(message); };
            export const api = () => fetch('/fixture.wav');
            export function connect(session, role, receive, status) {
                window.receive = receive;
                setTimeout(() => {
                    status(true);
                    receive({type:'snapshot', checkin:{checkin_id:'checkin'},
                        capabilities:{tts:'elevenlabs', stt:'browser'}});
                }, 0);
                return {send: message => window.events.push(message)};
            }
        '''
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page()
            page.add_init_script('''
                window.events = []; window.errors = []; window.micStarts = 0;
                window.SpeechRecognition = class {
                    start() { window.micStarts++; }
                    stop() {}
                    abort() {}
                };
            ''')
            def route(request):
                path = request.request.url.split('localhost')[1].split('#')[0]
                if path == '/fixture.wav':
                    request.fulfill(body=output.getvalue(), content_type='audio/wav')
                elif path == '/assets/common.js':
                    request.fulfill(body=common, content_type='application/javascript')
                elif path.startswith('/assets/'):
                    request.fulfill(path=str(static / path.removeprefix('/assets/')))
                else:
                    request.fulfill(path=str(static / 'phone.html'))
            page.route('http://localhost/**', route)
            page.goto('http://localhost/phone#session=test&token=test')
            page.locator('#start').click()
            page.evaluate("window.receive({type:'say', payload:{utterance_id:'u1', text:'Intro and custom voice', origin:'checkin'}})")
            expect(page.locator('#activity')).to_have_text('Lantern is speaking')
            # The first segment lasts one second; the second must still be playing.
            page.wait_for_timeout(1400)
            self.assertEqual(page.evaluate('window.micStarts'), 0)
            self.assertFalse(page.evaluate("window.events.some(e => e.state === 'delivered')"))
            expect(page.locator('#activity')).to_have_text('Listening. Take your time.', timeout=5000)
            self.assertEqual(page.evaluate('window.micStarts'), 1)
            self.assertEqual(page.evaluate("window.events.filter(e => e.state === 'delivered').length"), 1)
            self.assertEqual(page.evaluate('window.errors'), [])
            browser.close()


if __name__ == '__main__':
    unittest.main()

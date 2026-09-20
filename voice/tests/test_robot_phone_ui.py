"""Mobile controls with mock microphone, recognition, and robot event stream."""
from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright, expect


class RobotPhoneTests(unittest.TestCase):
    def test_separate_robot_and_checkin_recordings(self):
        static = Path(__file__).resolve().parents[1] / 'static'
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            for stt in ('browser', 'deepgram'):
                with self.subTest(stt=stt):
                    page = browser.new_page(viewport={'width': 390, 'height': 844})
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.add_init_script('''
                        window.sent = []; window.words = "let's go on a walk";
                        window.AudioContext = class { resume() { return Promise.resolve(); } };
                        Object.defineProperty(window, 'speechSynthesis', {value:{speak(){}, cancel(){}}});
                        window.SpeechRecognition = class {
                            start() {}
                            stop() { const result = [{transcript:window.words}]; result.isFinal = true;
                                this.onresult({results:[result]}); this.onend(); }
                            abort() { this.onend?.(); }
                        };
                        navigator.mediaDevices.getUserMedia = async () => ({getTracks:() => [{stop(){}}]});
                        window.MediaRecorder = class {
                            static isTypeSupported() { return true; }
                            start() { this.state = 'recording'; }
                            stop() { this.state = 'inactive'; this.ondataavailable({data:new Blob(['mock mic'])}); this.onstop?.(); }
                        };
                        window.WebSocket = class {
                            constructor() { window.robotStream = this; }
                            close() {}
                        };
                    ''')
                    common = f'''
                        export const BASE = '/voice';
                        export const $ = id => document.getElementById(id);
                        export const showError = (text = '') => {{ $('error').textContent = text; $('error').hidden = !text; }};
                        export const api = async () => ({{json:async () => ({{text:window.words}})}});
                        export function connect(session, role, receive, status) {{
                            window.receive = receive;
                            window.snapshot = {{type:'snapshot', checkin:null, capabilities:{{stt:'{stt}',tts:'browser'}}}};
                            setTimeout(() => {{ status(true); receive(window.snapshot); }}, 0);
                            return {{send: message => window.sent.push(message)}};
                        }}
                    '''
                    def route(request):
                        path = request.request.url.split('localhost')[1].split('#')[0]
                        if path == '/voice/assets/common.js':
                            request.fulfill(body=common, content_type='application/javascript')
                        elif path.startswith('/voice/assets/'):
                            request.fulfill(path=str(static / path.removeprefix('/voice/assets/')))
                        else:
                            request.fulfill(body=(static / 'phone.html').read_text(encoding='utf-8').replace('"/assets/', '"/voice/assets/'), content_type='text/html')
                    page.route('http://localhost/**', route)
                    page.goto('http://localhost/voice/phone#session=test&token=test')
                    page.locator('#start').click()
                    expect(page.locator('#record')).to_be_disabled()
                    expect(page.locator('#robot-record')).to_be_enabled()
                    page.locator('#robot-record').click()
                    expect(page.locator('#robot-record')).to_have_text('Finish and send request')
                    page.locator('#robot-record').click()
                    expect(page.locator('#robot-transcript')).to_contain_text("let's go on a walk")
                    self.assertEqual(page.evaluate("window.sent.filter(e => e.type === 'transcript').at(-1).checkin_id"), '')
                    # An existing check-in must not capture the separate robot request.
                    page.evaluate("window.snapshot.checkin = {checkin_id:'caregiver-1'}; window.receive(window.snapshot)")
                    page.locator('#robot-record').click(); page.locator('#robot-record').click()
                    expect(page.locator('#robot-record')).to_have_text('Speak a robot request')
                    self.assertEqual(page.evaluate("window.sent.filter(e => e.type === 'transcript').at(-1).checkin_id"), '')
                    page.evaluate("window.words = 'I feel fine'")
                    page.locator('#record').click()
                    expect(page.locator('#robot-record')).to_be_disabled()
                    page.locator('#record').click()
                    expect(page.locator('#activity')).to_have_text('Reply sent')
                    self.assertEqual(page.evaluate("window.sent.filter(e => e.type === 'transcript').at(-1).checkin_id"), 'caregiver-1')
                    page.evaluate("window.robotStream.onmessage({data:JSON.stringify({type:'agent_state',payload:{state:'CONFIRM_HOME'}})})")
                    expect(page.locator('#robot-confirm')).to_be_visible()
                    page.locator('#robot-yes').click()
                    self.assertEqual(page.evaluate("window.sent.at(-1).text"), 'yes')
                    self.assertEqual(page.evaluate("window.sent.at(-1).checkin_id"), '')
                    self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    self.assertEqual(errors, [])
                    if stt == 'browser':
                        output = Path(__file__).resolve().parents[1] / 'test-results'
                        output.mkdir(exist_ok=True)
                        page.screenshot(path=str(output / 'robot-phone.png'), full_page=True)
                    page.close()
            browser.close()


if __name__ == '__main__':
    unittest.main()

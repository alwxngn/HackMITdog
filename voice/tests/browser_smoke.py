"""Two real browser contexts; fake audio APIs, real HTTP/WebSocket session traffic.

Run with a server already listening on http://127.0.0.1:8000.
Set BROWSER_CHANNEL=chrome to use an installed Chrome instead of Playwright Chromium.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


FAKE_AUDIO = r"""
window.__audio = [];
window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
let speechTimers = [];
Object.defineProperty(window, 'speechSynthesis', {value: {
  speak(message) {
    window.__audio.push(message.text);
    speechTimers.push(setTimeout(() => message.onstart?.(), 10));
    speechTimers.push(setTimeout(() => message.onend?.(), 120));
  },
  cancel() { speechTimers.forEach(clearTimeout); speechTimers = []; }
}});
window.SpeechRecognition = class {
  start() { window.__recognition = this; }
  stop() {
    const result = [{transcript: 'I am feeling fine'}]; result.isFinal = true;
    this.onresult?.({results:[result]}); this.onend?.();
  }
  abort() { this.onend?.(); }
};
"""


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.getenv('BROWSER_CHANNEL') or None)
    desktop = browser.new_context(viewport={'width':1280,'height':1000})
    mobile = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
    mobile.add_init_script(FAKE_AUDIO)
    caregiver = desktop.new_page()
    phone = mobile.new_page()
    errors = []
    caregiver.on('pageerror', lambda error: errors.append(str(error)))
    phone.on('pageerror', lambda error: errors.append(str(error)))
    caregiver.goto('http://127.0.0.1:8000')
    caregiver.get_by_role('button', name='Create a session').click()
    expect(caregiver.locator('#workspace')).to_be_visible()
    link = caregiver.locator('#phone-link').input_value()
    phone.goto(link)
    expect(phone.locator('#start')).to_be_enabled()
    phone.locator('#start').click()
    expect(caregiver.locator('#connection')).to_have_text('● Phone ready')
    caregiver.locator('#send').click()
    expect(phone.locator('#spoken')).to_contain_text('Sarah asked me to check in')
    expect(caregiver.locator('#delivery')).to_contain_text('Delivered')
    phone.locator('#record').click()
    expect(phone.locator('#record')).to_have_text('Finish and send reply')
    phone.locator('#record').click()
    expect(caregiver.locator('#timeline')).to_contain_text('I am feeling fine')
    expect(phone.locator('#spoken')).to_contain_text("view your message")
    expect(caregiver.locator('#delivery')).to_have_text('Reply received')
    phone.locator('summary').click()
    phone.locator('#reply').fill('Are you Sarah?')
    phone.locator('#send-reply').click()
    expect(phone.locator('#spoken')).to_contain_text("view your message")
    phone.locator('#reply').fill('I need help')
    phone.locator('#send-reply').click()
    expect(caregiver.locator('#attention')).to_be_visible()
    expect(phone.locator('#spoken')).to_contain_text("view your message")
    assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
    Path('test-results').mkdir(exist_ok=True)
    caregiver.screenshot(path='test-results/caregiver.png', full_page=True)
    phone.screenshot(path='test-results/phone.png', full_page=True)
    phone.locator('#pause').click()
    expect(caregiver.locator('#send')).to_be_disabled()
    phone.locator('#start').click()
    expect(caregiver.locator('#send')).to_be_enabled()
    phone.close()
    expect(caregiver.locator('#connection')).to_have_text('○ Phone offline')
    assert not errors, errors
    browser.close()
    print('PASS: paired check-in, playback acknowledgment, simulated spoken reply, identity reply, attention, pause/resume, disconnect and mobile layout.')

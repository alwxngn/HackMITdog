"""Live APIs, E3 portal + minimal phone, real recording of synthetic audio.

Requires the integrated API :8000 and Vite :5173, plus configured provider keys.
Consumes API credits; no real microphone is captured.
"""
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome')
    desktop = browser.new_context(viewport={'width':1280, 'height':1000})
    mobile = browser.new_context(viewport={'width':390, 'height':844}, is_mobile=True)
    caregiver, phone = desktop.new_page(), mobile.new_page()
    errors = []
    caregiver.on('pageerror', lambda error: errors.append(str(error)))
    phone.on('pageerror', lambda error: errors.append(str(error)))
    caregiver.goto('http://127.0.0.1:5173')
    expect(caregiver.get_by_role('button', name='Continue')).to_be_visible(timeout=15000)
    Path('test-results').mkdir(exist_ok=True)
    caregiver.screenshot(path='test-results/portal-welcome.png', full_page=True)
    caregiver.get_by_role('button', name='Check in').click()
    panel = caregiver.get_by_role('dialog')
    panel.get_by_label('From', exact=True).fill('Sarah')
    panel.get_by_role('button', name='Connect phone').click()
    expect(panel.get_by_role('link', name='Open phone voice')).to_be_visible()
    phone.goto(panel.get_by_role('link', name='Open phone voice').get_attribute('href'))
    expect(phone.locator('#start')).to_be_enabled()
    phone.locator('#start').click()
    expect(panel.get_by_role('button', name='Send to robot')).to_be_enabled()
    panel.get_by_label('Check-in message').fill('Hello Arthur. How are you feeling today?')
    with phone.expect_response(lambda response: '/speech/' in response.url, timeout=60000) as audio_response:
        panel.get_by_role('button', name='Send to robot').click()
    response = audio_response.value
    assert response.status == 200, response.text()
    audio = response.body()
    expect(panel.get_by_role('status')).to_contain_text('Delivered', timeout=60000)
    phone.evaluate('''async bytes => {
      const context = new AudioContext(); await context.resume();
      const buffer = await context.decodeAudioData(new Uint8Array(bytes).buffer);
      window.__duration = buffer.duration;
      navigator.mediaDevices.getUserMedia = async () => {
        const destination = context.createMediaStreamDestination();
        const source = context.createBufferSource(); source.buffer = buffer;
        source.connect(destination); source.start(context.currentTime + 0.2);
        window.__source = source; return destination.stream;
      };
    }''', list(audio))
    phone.locator('#record').click()
    expect(phone.locator('#record')).to_have_text('Finish and send reply')
    phone.wait_for_timeout((phone.evaluate('window.__duration') + 0.5) * 1000)
    phone.locator('#record').click()
    expect(panel.get_by_test_id('checkin-reply')).to_contain_text('Arthur', timeout=60000)
    expect(panel.get_by_role('status')).to_have_text('Reply received', timeout=60000)
    expect(phone.locator('#activity')).to_contain_text('Your turn', timeout=60000)
    phone.screenshot(path='test-results/portal-phone.png', full_page=True)
    caregiver.screenshot(path='test-results/portal-checkin.png', full_page=True)
    panel.get_by_role('button', name='Close').click()
    caregiver.goto('http://127.0.0.1:5173/watch')
    expect(caregiver.get_by_role('heading', name='Tonight, at a glance')).to_be_visible()
    expect(caregiver.get_by_test_id('checkin-reply')).to_contain_text('Arthur')
    timeline = caregiver.locator('div.card').filter(has=caregiver.get_by_role('heading', name='Timeline', exact=True))
    expect(timeline).to_contain_text('patient:')
    expect(timeline).to_contain_text('How are you feeling today?')
    caregiver.screenshot(path='test-results/portal-dashboard.png', full_page=True)
    caregiver.get_by_role('link', name='Onboarding').click()
    expect(caregiver).to_have_url('http://127.0.0.1:5173/onboarding')
    assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
    print('PASS: unchanged portal entry, check-in pairing, ElevenLabs audio, recorded Deepgram reply, original timeline, session restoration, onboarding route and minimal phone layout.')

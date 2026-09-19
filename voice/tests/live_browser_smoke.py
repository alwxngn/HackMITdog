"""Explicit opt-in live test: real APIs, browser audio, synthetic microphone input.

Requires a configured server on port 8000; consumes API credits. No human audio is captured.
Run: python voice/tests/live_browser_smoke.py
"""
import os

from playwright.sync_api import expect, sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.getenv('BROWSER_CHANNEL') or 'chrome')
    caregiver = browser.new_page()
    phone = browser.new_page(viewport={'width':390, 'height':844}, is_mobile=True)
    errors = []
    phone.on('pageerror', lambda error: errors.append(str(error)))
    caregiver.goto('http://127.0.0.1:8000')
    caregiver.get_by_role('button', name='Create a session').click()
    expect(caregiver.locator('#workspace')).to_be_visible()
    expect(caregiver.locator('#mode')).to_contain_text('Deepgram recognition')
    expect(caregiver.locator('#mode')).to_contain_text('ElevenLabs voice')
    phone.goto(caregiver.locator('#phone-link').input_value())
    phone.locator('#start').click()
    expect(caregiver.locator('#send')).to_be_enabled()
    caregiver.locator('#message').fill('Hello Arthur. How are you feeling today?')
    with phone.expect_response(lambda response: '/speech/' in response.url, timeout=60000) as audio_response:
        caregiver.locator('#send').click()
    audio = audio_response.value
    assert audio.status == 200
    audio_bytes = audio.body()
    expect(caregiver.locator('#delivery')).to_contain_text('Delivered', timeout=60000)
    # Feed the known synthesized greeting to the browser's actual MediaRecorder. This checks
    # the same WebM upload/transcription path as a phone without capturing a real microphone.
    phone.evaluate('''async (bytes) => {
      const context = new AudioContext(); await context.resume();
      const buffer = await context.decodeAudioData(new Uint8Array(bytes).buffer);
      window.__fixtureDuration = buffer.duration;
      navigator.mediaDevices.getUserMedia = async () => {
        const destination = context.createMediaStreamDestination();
        const source = context.createBufferSource(); source.buffer = buffer;
        source.connect(destination); source.start(context.currentTime + 0.2);
        window.__fixtureSource = source;
        return destination.stream;
      };
    }''', list(audio_bytes))
    phone.locator('#record').click()
    expect(phone.locator('#record')).to_have_text('Finish and send reply')
    phone.wait_for_timeout((phone.evaluate('window.__fixtureDuration') + 0.5) * 1000)
    with phone.expect_response(lambda response: '/transcribe' in response.url, timeout=60000) as transcript_response:
        phone.locator('#record').click()
    response = transcript_response.value
    assert response.status == 200, response.text()
    transcript = response.json()['text']
    assert 'arthur' in transcript.lower(), transcript
    expect(caregiver.locator('#delivery')).to_have_text('Reply received', timeout=60000)
    expect(phone.locator('#activity')).to_contain_text('Your turn', timeout=60000)
    assert not errors, errors
    print('PASS: real ElevenLabs playback, browser MediaRecorder upload, real Deepgram transcription, and spoken response.')
    print(f'Synthetic microphone transcript: {transcript}')
    browser.close()

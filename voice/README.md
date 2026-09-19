# Mobile voice check-in prototype

This first E1 implementation gives Lantern a phone microphone and speaker. It includes a
small caregiver page and temporary session relay so the interaction works before the full
E3 portal or E4 orchestrator exists. It does not control the Unitree.

## Run locally (PowerShell, from the repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r voice/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn voice.app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000, create a session, and open its phone link in another tab to
test locally. On the phone view, tap **Start Lantern**. Send a check-in from the caregiver
page. The phone speaks, and **Talk to Lantern** starts a reply; tap again to finish.
A typed reply is always available. Browser speech recognition varies by browser and may
use a vendor's network service; this mode is not guaranteed offline.

For a physical phone, serve this same app through a trusted **HTTPS** endpoint (for example,
a development HTTPS tunnel to port 8000). Open the caregiver page at that HTTPS address
**before** creating/copying the phone link. Do not send the phone a `localhost` or plain HTTP
LAN link: microphone access needs a secure context. The endpoint must forward WebSockets.
No tunnel is created or deployment published by this implementation.

Keep the phone unlocked with the page foregrounded. Hiding it pauses the session and releases
the microphone. Return and tap Start to resume. A disconnect requires another Start tap;
old audio is deliberately not replayed. Only one phone can join a session at a time.

## Optional provider credentials

Copy `voice/.env.example` to `.env` at the repository root and fill only the services you use.
Restart the server after changing it. Keys stay on the server and are never returned to clients.

- `DEEPGRAM_API_KEY`: switches the phone to MediaRecorder uploads and server-side Deepgram
  transcription. This first version transcribes a **completed recording**, not a live stream.
  The browser negotiates WebM, MP4 or Ogg; replies stop after 30 seconds and uploads are limited
  to 5 MiB. Microphone tracks are stopped after each recording.
- `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` + `ELEVENLABS_VOICE_CONSENT=true`: enables
  server-generated speech with an explicitly approved voice. Without all three, the phone
  uses its own browser voice. This is an operator gate, **not** a voice-enrollment/consent UI.
  Only use a voice you have permission to use. No voice cloning is performed here.
- No LLM key is required: replies are visibly labeled **scripted**. They identify as Lantern,
  never invent family schedules, and flag some help/distress words for caregiver review.
  This simple matching is a demo behavior, not a clinical detector or an emergency service.

The first Start tap initializes audio. If mobile autoplay still blocks a later message, the
phone shows **Tap to play message**. Test on the actual demo phone, including its volume,
microphone permission, Safari/Chrome behavior and network.

## Implemented flow

1. Caregiver creates a session; server returns separate random caregiver and phone capabilities.
2. Phone joins using a private fragment link, stores its capability in sessionStorage, removes
   the fragment from the address bar, and authenticates its WebSocket in the first message.
3. Caregiver submits a check-in; disconnected/unstarted phones return an actionable error.
4. Relay records `checkin`, emits an attributed `say`, and phone plays audio.
5. Playback acknowledgments distinguish sent, speaking, delivered, failed and interrupted.
6. Patient records or types a reply; relay records `transcript`, prepares a short response,
   and updates the caregiver conversation. Turn IDs deduplicate replies, and check-in IDs
   reject replies left over from an earlier check-in.
7. **Stop speaking** or **Talk** cancels local audio and in-flight speech requests. This is
   manual interruption, not automatic hands-free barge-in.

## Boundaries and remaining work

All new code is under `/voice` to avoid creating a competing `/cloud`, `/bus`, or
`/orchestrator` implementation. `app.py` is a temporary demo host and relay. `say`, `checkin`,
and `transcript` use the documented payload concepts. Pairing, snapshots, `ready`, playback
acknowledgments and turn IDs are **local demo transport extensions**, not changes to the
frozen shared bus. E4 should map these to the actual bus during integration.

Still to build: the shared orchestrator's safety-state check-in queue, streaming STT,
automatic barge-in/echo handling, LLM dialogue with inbound/outbound guards, patient profile
storage, audited voice enrollment/revocation, persistent events, robot movement coordination,
and phone background operation. No automatic caregiver call/SMS is sent.

Run a **single server worker**. Sessions/events are in memory, bounded, expire after 12 hours,
and disappear on restart. Raw microphone audio is forwarded for transcription but not stored.
Treat the pairing link as a password: it allows access to that session's conversation. The
prototype has role-scoped capability checks, not user accounts or production authentication;
use synthetic demo data. Session creation is public with a 100-session process limit.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s voice/tests -v
node --check voice/static/phone.js
node --check voice/static/caregiver.js
```

The backend tests exercise check-in delivery, identity replies, session/role isolation,
duplicate phones, stale acknowledgments/replies, disconnects, consent gating and audio input
validation. Provider calls in automated tests are mocked: real API credentials and a physical
phone are needed to validate actual recognition and audible playback.

Browser smoke test (separate running server on port 8000):

```powershell
.\.venv\Scripts\python.exe -m pip install -r voice/requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe voice/tests/browser_smoke.py
```

## API references

- [Deepgram recorded audio](https://developers.deepgram.com/docs/pre-recorded-audio)
- [ElevenLabs speech generation](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
- [Browser microphone permissions](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [Browser speech recognition support](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- [Browser audio activation](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)

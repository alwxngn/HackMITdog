# Lantern — open-source citations
# Update this file when you add a dependency (HackMIT P1-8 / docs/10-second-pass.md).

## Cloud / portal (E3)

| Dependency | License | Use |
|---|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) | MIT | HTTP + WebSocket API |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI server |
| [Pydantic](https://github.com/pydantic/pydantic) | MIT | Message / config models |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | Fixture replay client |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Env loading |
| [Twilio Python Helper](https://github.com/twilio/twilio-python) | MIT | SMS + voice call ladder |
| [React](https://github.com/facebook/react) | MIT | Caregiver portal UI |
| [Vite](https://github.com/vitejs/vite) | MIT | Frontend toolchain |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) | MIT | Styling |
| [React Router](https://github.com/remix-run/react-router) | MIT | Portal routes |
| [qrcode](https://github.com/soldair/node-qrcode) | MIT | Phone share QR codes on the dashboard |
| [Cormorant Garamond](https://fonts.google.com/specimen/Cormorant+Garamond) | OFL | Display serif (Faire Octave substitute per `cloud/web/design.md`) |
| [Inter](https://fonts.google.com/specimen/Inter) | OFL | UI type (Suisse Intl substitute) |

## Mobile voice (E1)

- [FastAPI](https://github.com/fastapi/fastapi), MIT — HTTP API and WebSocket routing.
- [Starlette](https://github.com/Kludex/starlette), BSD-3-Clause — ASGI/static/test infrastructure via FastAPI.
- [Pydantic](https://github.com/pydantic/pydantic), MIT — input validation via FastAPI.
- [Uvicorn](https://github.com/Kludex/uvicorn), BSD-3-Clause — ASGI server and standard extras.
- [HTTPX](https://github.com/encode/httpx), BSD-3-Clause — backend provider requests and test client.
- [python-dotenv](https://github.com/theskumar/python-dotenv), BSD-3-Clause — local environment configuration.
- [Playwright](https://github.com/microsoft/playwright-python), Apache-2.0 — optional browser smoke tests.
- [Deepgram](https://developers.deepgram.com/) — optional hosted speech recognition, using the REST API.
- [ElevenLabs](https://elevenlabs.io/docs) — optional hosted speech synthesis, using the REST API.
- Browser Web Speech, MediaRecorder and Web Audio APIs — phone capture and playback; support varies by browser.

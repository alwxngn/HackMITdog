# Dependencies and services

Mobile voice prototype:

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

No external UI template, font, image asset, or robot-control code is used in this prototype.

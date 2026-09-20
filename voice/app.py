"""Single-process mobile voice prototype; temporary session relay for E1/E3/E4."""
import asyncio
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import secrets
import time
from typing import Callable, Awaitable

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, field_validator

from voice import providers
from voice.dialogue import reply_to

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env", override=True)
app = FastAPI(title="Lantern mobile voice prototype")
app.mount("/assets", StaticFiles(directory=ROOT / "static"), name="assets")


class Profile(BaseModel):
    patient: str = Field(default="Arthur", min_length=1, max_length=60)
    caregiver: str = Field(default="Sarah", min_length=1, max_length=60)

    @field_validator("patient", "caregiver")
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if not value or any(not (ch.isalpha() or ch in " '-") for ch in value):
            raise ValueError("Use a name with letters, spaces, apostrophes or hyphens.")
        return value


class Checkin(BaseModel):
    text: str = Field(default="", max_length=500)
    from_name: str | None = Field(default=None, min_length=1, max_length=60)


class PhoneEvent(BaseModel):
    type: str
    utterance_id: str = ""
    state: str = ""
    text: str = Field(default="", max_length=2000)
    turn_id: str = Field(default="", max_length=80)
    checkin_id: str = ""


@dataclass
class Session:
    id: str
    profile: Profile
    caregiver_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    phone_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    created: float = field(default_factory=time.time)
    phone: WebSocket | None = None
    ready: bool = False
    watchers: set = field(default_factory=set)
    events: deque = field(default_factory=lambda: deque(maxlen=150))
    checkin: dict | None = None
    utterance: dict | None = None
    turns: deque = field(default_factory=lambda: deque(maxlen=100))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    audio_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    speech_cache: tuple[str, bytes] | None = None
    event_sink: Callable[[dict], Awaitable[None]] | None = None
    forwarded_seq: int = 0
    forward_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def record(self, kind, payload, source="voice"):
        self.events.append({"type": kind, "ts": time.time(), "source": source,
                            "seq": getattr(self, "seq", 0) + 1, "payload": payload})
        self.seq = self.events[-1]["seq"]

    def snapshot(self):
        return {"type": "snapshot", "session_id": self.id, "profile": self.profile.model_dump(),
                "phone_online": self.phone is not None, "phone_ready": self.ready,
                "checkin": self.checkin, "utterance": self.utterance,
                "events": list(self.events), "capabilities": providers.capabilities(),
                "configuration_notes": providers.configuration_notes()}

    async def publish(self):
        if self.event_sink:
            async with self.forward_lock:
                for event in list(self.events):
                    if event["seq"] > self.forwarded_seq:
                        await self.event_sink(event)
                        self.forwarded_seq = event["seq"]
        message = self.snapshot()
        for ws in list(self.watchers):
            try:
                await asyncio.wait_for(ws.send_json(message), 3)
            except (RuntimeError, WebSocketDisconnect, TimeoutError):
                self.watchers.discard(ws)


sessions: dict[str, Session] = {}


def get_session(session_id):
    session = sessions.get(session_id)
    if session is None or time.time() - session.created > 12 * 3600:
        raise HTTPException(404, "Session expired or not found. Create a new session.")
    return session


def authorize(request, session, role):
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not secrets.compare_digest(token.encode(), getattr(session, f"{role}_token").encode()):
        raise HTTPException(403, "Invalid session credentials.")


@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "media-src 'self' blob:; img-src 'self' data:; frame-ancestors 'none'"
    )
    return response


@app.get("/")
async def caregiver_page(request: Request):
    if request.scope.get("root_path"):
        return RedirectResponse("/")
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/phone")
async def phone_page(request: Request):
    prefix = request.scope.get("root_path", "")
    html = (ROOT / "static" / "phone.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace('"/assets/', f'"{prefix}/assets/'))


@app.get("/api/health")
async def health():
    return {"status": "ok", "capabilities": providers.capabilities(),
            "configuration_notes": providers.configuration_notes()}


@app.post("/api/sessions", status_code=201)
async def create_session(profile: Profile, request: Request):
    for key, session in list(sessions.items()):
        if time.time() - session.created > 12 * 3600 and not session.watchers:
            del sessions[key]
    if len(sessions) >= 100:
        raise HTTPException(503, "Demo session limit reached. Restart the server to clear sessions.")
    session = Session(secrets.token_urlsafe(12), profile)
    session.event_sink = getattr(request.app.state, "event_sink", None)
    sessions[session.id] = session
    return {"session_id": session.id, "caregiver_token": session.caregiver_token,
            "phone_token": session.phone_token}


async def say(session, text, origin, attribution=None):
    payload = {"utterance_id": secrets.token_urlsafe(12), "text": text, "voice_id": None,
               "tone": "warm", "interruptible": True, "attribution": attribution, "origin": origin}
    session.utterance = {**payload, "state": "pending"}
    session.speech_cache = None
    session.record("say", payload, "orchestrator")
    try:
        await asyncio.wait_for(session.phone.send_json({"type": "say", "payload": payload}), 3)
    except (AttributeError, RuntimeError, WebSocketDisconnect, TimeoutError):
        session.utterance["state"] = "failed"
        session.checkin["status"] = "unavailable"
        session.ready = False


@app.post("/api/sessions/{session_id}/checkins", status_code=202)
async def check_in(session_id: str, body: Checkin, request: Request):
    session = get_session(session_id)
    authorize(request, session, "caregiver")
    async with session.lock:
        allowed = getattr(request.app.state, "checkin_allowed", None)
        if allowed and not allowed():
            raise HTTPException(409, "Lantern is handling a safety event. Please check in after it resolves.")
        if not session.ready or session.phone is None:
            raise HTTPException(409, "Start Lantern on the paired phone before sending a check-in.")
        if session.utterance and session.utterance["state"] in {"pending", "speaking"}:
            raise HTTPException(409, "Lantern is still speaking. Wait or interrupt on the phone.")
        patient_name = getattr(request.app.state, "patient_name", None)
        try:
            session.profile = Profile(
                patient=patient_name() if patient_name else session.profile.patient,
                caregiver=body.from_name.strip() if body.from_name else session.profile.caregiver,
            )
        except ValidationError:
            raise HTTPException(422, "Please use a valid patient and caregiver name.") from None
        session.checkin = {"checkin_id": secrets.token_urlsafe(12), "status": "sent",
                           "text": body.text.strip(), "needs_attention": False}
        session.record("checkin", {**session.checkin, "from_name": session.profile.caregiver}, "cloud")
        attribution = f"{session.profile.caregiver} sent you this message"
        text = (f"{attribution}: {body.text.strip()}" if body.text.strip() else
                f"Hi {session.profile.patient}. {session.profile.caregiver} asked me to check in. How are you feeling?")
        await say(session, text, "checkin", attribution)
        await session.publish()
        return session.checkin


async def handle_phone(session, event):
    if event.type == "ready":
        session.ready = True
    elif event.type == "paused":
        session.ready = False
    elif event.type == "playback":
        current = session.utterance
        if not current or event.utterance_id != current["utterance_id"]:
            return
        if event.state not in {"speaking", "delivered", "interrupted", "failed"}:
            return
        if current["state"] not in {"pending", "speaking", "failed"}:
            return
        current["state"] = event.state
        session.record("speech_state", {"state": event.state, "utterance_id": event.utterance_id})
        if current["origin"] == "checkin" and session.checkin["status"] != "responded":
            session.checkin["status"] = event.state
    elif event.type == "transcript":
        text = event.text.strip()
        if (not text or not event.turn_id or event.turn_id in session.turns or not session.ready
                or not session.checkin or event.checkin_id != session.checkin["checkin_id"]):
            return
        session.turns.append(event.turn_id)
        if session.utterance and session.utterance["state"] in {"pending", "speaking"}:
            session.utterance["state"] = "interrupted"
        session.record("transcript", {"text": text, "is_final": True, "speaker": "patient",
                                      "checkin_id": event.checkin_id})
        session.checkin["status"] = "responded"
        answer, attention = reply_to(text, session.profile.patient, session.profile.caregiver)
        session.checkin["needs_attention"] |= attention
        await say(session, answer, "companionship")
    await session.publish()


@app.websocket("/ws/{session_id}/{role}")
async def socket(ws: WebSocket, session_id: str, role: str):
    await ws.accept()
    session = None
    try:
        session = get_session(session_id)
        auth = await asyncio.wait_for(ws.receive_json(), 8)
        if (role not in {"phone", "caregiver"} or not isinstance(auth, dict)
                or not isinstance(auth.get("token"), str)
                or not secrets.compare_digest(auth["token"].encode(), getattr(session, f"{role}_token").encode())):
            await ws.close(4403)
            return
        if role == "phone":
            if session.phone is not None:
                await ws.close(4409, "A phone is already paired.")
                return
            session.phone = ws
            session.ready = False
        session.watchers.add(ws)
        await session.publish()
        while True:
            remaining = 12 * 3600 - (time.time() - session.created)
            if remaining <= 0:
                await ws.close(4403, "Session expired.")
                break
            raw = await asyncio.wait_for(ws.receive_text(), min(45, remaining))
            if len(raw) > 12000:
                await ws.close(1009)
                break
            try:
                event = PhoneEvent.model_validate_json(raw)
            except ValidationError:
                await ws.send_json({"type": "error", "message": "Invalid message."})
                continue
            if event.type == "ping":
                await ws.send_json({"type": "pong"})
            elif role == "phone":
                async with session.lock:
                    await handle_phone(session, event)
    except HTTPException:
        await ws.close(4403)
    except (WebSocketDisconnect, TimeoutError, ValueError):
        pass
    finally:
        if session:
            session.watchers.discard(ws)
            if session.phone is ws:
                session.phone = None
                session.ready = False
                if session.utterance and session.utterance["state"] in {"pending", "speaking"}:
                    session.utterance["state"] = "interrupted"
                    if session.checkin["status"] != "responded":
                        session.checkin["status"] = "unavailable"
                await session.publish()
        try:
            await ws.close()
        except RuntimeError:
            pass


@app.post("/api/sessions/{session_id}/transcribe")
async def transcribe(session_id: str, request: Request):
    session = get_session(session_id)
    authorize(request, session, "phone")
    content_type = request.headers.get("content-type", "").split(";")[0]
    if content_type not in {"audio/webm", "audio/mp4", "audio/ogg", "audio/wav"}:
        raise HTTPException(415, "Unsupported recording format.")
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > 5 * 1024 * 1024:
            raise HTTPException(413, "Recording too large. Keep replies under 30 seconds.")
    if not audio:
        raise HTTPException(400, "Empty recording.")
    async with session.audio_lock:
        return {"text": await providers.transcribe(bytes(audio), content_type)}


@app.post("/api/sessions/{session_id}/speech/{utterance_id}")
async def speech(session_id: str, utterance_id: str, request: Request):
    session = get_session(session_id)
    authorize(request, session, "phone")
    current = session.utterance
    if not current or current["utterance_id"] != utterance_id or current["state"] not in {"pending", "speaking", "failed"}:
        raise HTTPException(409, "This utterance is no longer active.")
    async with session.audio_lock:
        if providers.capabilities()["tts"] != "elevenlabs":
            raise HTTPException(503, "The selected ElevenLabs voice is not enabled.")
        if session.utterance is not current or current["state"] not in {"pending", "speaking", "failed"}:
            raise HTTPException(409, "This utterance is no longer active.")
        if session.speech_cache and session.speech_cache[0] == utterance_id:
            audio = session.speech_cache[1]
        else:
            audio = await providers.synthesize(current["text"])
            if session.utterance is not current or current["state"] not in {"pending", "speaking", "failed"}:
                raise HTTPException(409, "This utterance was interrupted.")
            session.speech_cache = (utterance_id, audio)
    return Response(audio, media_type="audio/mpeg")

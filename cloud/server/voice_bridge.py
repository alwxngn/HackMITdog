"""Mount E1's phone service and forward its existing envelopes to E3's event stream.

The portal remains the caregiver UI; pairing/playback metadata stays in the voice service.
"""
from pathlib import Path
import sys

# Also support the teammate's original `cd cloud/server; uvicorn main:app` command.
_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from voice.app import app as voice_app
from bus import bus
from store import store


async def forward_voice_event(event):
    if event["type"] not in {"checkin", "say", "transcript", "speech_state"}:
        return
    payload = dict(event["payload"])
    if event["type"] == "speech_state":
        # Local playback completion is represented by the existing bus `idle` state.
        payload["state"] = {"delivered": "idle", "failed": "idle"}.get(payload["state"], payload["state"])
    await bus.ingest({**event, "payload": payload})


def patient_name():
    patient = store.projection.get("config", {}).get("patient", {})
    return patient.get("preferred_name") or patient.get("name") or "Arthur"


def install_voice(app):
    voice_app.state.event_sink = forward_voice_event
    voice_app.state.patient_name = patient_name
    voice_app.state.checkin_allowed = lambda: store.projection.get("agent_state", {}).get("state", "IDLE") in {"IDLE", "ATTEND"}
    app.mount("/voice", voice_app)

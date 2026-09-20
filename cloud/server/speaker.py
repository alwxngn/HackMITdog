"""Lantern's voice: speaks to the patient through the paired phone (the dog's speaker).

Watches person_track / zone_event and, when the patient drifts toward danger, says a
calm line out loud on the phone that rides on the dog:

  warning zone      → "It's late. Let's go back to bed."
  danger zone       → "Let's go home."
  outside the house → "Let's go home."  (repeated, softly, while they keep walking)

It works for real tracker data and for the scripted demo walk alike, and falls back to
a portal-only `say` (timeline) when no phone is paired and started.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from bus import bus
from store import store

logger = logging.getLogger("lantern.speaker")

RANK = {"safe": 0, "watch": 1, "exit": 2, "outside": 3}

# Cycled per zone so a repeat never sounds like a stuck recording.
LINES: dict[str, list[str]] = {
    "watch": [
        "It's late, {n}. Let's go back to bed.",
        "{n}, it's the middle of the night. Let's head back to bed.",
        "Come on, {n}. Your bed is warm and waiting. Let's go back.",
    ],
    "exit": [
        "{n}, that's the way outside. Let's go home.",
        "It's late, {n}. Please come away from the door. Let's go home.",
        "{n}, let's stop here and turn around. Let's go home together.",
    ],
    "outside": [
        "{n}, it's late. Let's go home.",
        "{n}, please turn around. Let's go home together.",
        "I'm right here with you, {n}. Let's walk home.",
    ],
}

# Seconds before repeating a line while they stay in the same zone.
REPEAT_S = {"watch": 20.0, "exit": 12.0, "outside": 15.0}


class DangerSpeaker:
    def __init__(self) -> None:
        self.cls = "safe"
        self.last_spoken = 0.0
        self.last_line: str | None = None
        self._n: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self.cls = "safe"
        self.last_spoken = 0.0
        self._n.clear()

    # ---- phone --------------------------------------------------------------

    def _session(self) -> Any | None:
        try:
            from voice.app import sessions
        except Exception:
            return None
        live = [s for s in sessions.values() if s.phone is not None]
        return max(live, key=lambda s: (s.ready, s.created)) if live else None

    def status(self) -> dict[str, Any]:
        session = self._session()
        return {
            "phone_online": session is not None,
            "phone_ready": bool(session and session.ready),
            "last_line": self.last_line,
        }

    def _patient(self) -> tuple[str, str]:
        cfg = store.projection.get("config") or {}
        patient = cfg.get("patient") or {}
        name = patient.get("preferred_name") or patient.get("name") or "Susan"
        attribution = (cfg.get("voice") or {}).get("attribution_name") or "Sarah"
        return name, attribution

    def _speaking(self) -> bool:
        session = self._session()
        current = session.utterance if session else None
        return bool(current and current.get("state") in {"pending", "speaking"})

    async def speak(self, text: str) -> bool:
        """Say it on the phone if it is started; otherwise just log it to the portal."""
        _, who = self._patient()
        attribution = f"{who} recorded this for you"
        self.last_line = text
        session = self._session()
        if session is not None and session.ready:
            try:
                from voice.app import say

                await say(session, text, "policy", attribution)
                await session.publish()
                return True
            except Exception:
                logger.exception("phone speech failed — falling back to portal-only say")
        await bus.ingest(
            {
                "type": "say",
                "ts": time.time(),
                "source": "orchestrator",
                "seq": 0,
                "payload": {
                    "utterance_id": f"sp_{int(time.time() * 1000)}",
                    "text": text,
                    "voice_id": None,
                    "tone": "soothing",
                    "interruptible": True,
                    "attribution": attribution,
                    "origin": "policy",
                },
            }
        )
        return False

    # ---- policy -------------------------------------------------------------

    def _class_of(self, zone_id: str | None) -> str | None:
        if zone_id == "outside":
            return "outside"
        for z in store.projection.get("zones") or []:
            if z.get("id") == zone_id:
                return z.get("class")
        return None

    async def on_message(self, msg: dict[str, Any]) -> None:
        cfg = store.projection.get("config") or {}
        if not cfg.get("night_watch_enabled", False):
            return
        t = msg.get("type")
        p = msg.get("payload") or {}
        if t == "person_track":
            cls = self._class_of(p.get("zone"))
        elif t == "zone_event" and p.get("event") == "exited" and p.get("outside") is True:
            cls = "outside"
        else:
            return
        if cls is None:
            return
        if cls == "safe":
            self.reset()
            return

        now = time.monotonic()
        rose = RANK[cls] > RANK.get(self.cls, 0)
        due = now - self.last_spoken >= REPEAT_S[cls]
        self.cls = cls
        # Getting closer to danger interrupts; repeats wait for the last line to finish.
        if not (rose or (due and not self._speaking())):
            return
        self.last_spoken = now
        asyncio.create_task(self._say_line(cls))

    async def _say_line(self, cls: str) -> None:
        async with self._lock:
            name, _ = self._patient()
            lines = LINES[cls]
            i = self._n.get(cls, 0)
            self._n[cls] = i + 1
            try:
                await self.speak(lines[i % len(lines)].format(n=name))
            except Exception:
                logger.exception("speaker failed")


speaker = DangerSpeaker()

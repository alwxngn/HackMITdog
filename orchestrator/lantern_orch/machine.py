"""Five-state night-watch machine + Tier-0 say/command/alert."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

from lantern_bus.core import Bus

logger = logging.getLogger("lantern.orch.machine")

# Demo-compressed timers (LANTERN_FAST_SPINE=1 default for hackathon)
_FAST = os.getenv("LANTERN_FAST_SPINE", "1") == "1"
LEAD_TO_ESCALATE_S = float(os.getenv("LEAD_TO_ESCALATE_S", "5" if _FAST else "20"))
TTZ_LEAD_S = float(os.getenv("TTZ_LEAD_S", "8"))


class StateMachine:
    def __init__(self, bus: Bus, *, patient_name: str = "Susan") -> None:
        self.bus = bus
        self.patient_name = patient_name
        self.state = "IDLE"
        self.previous: str | None = None
        self.agitation = "calm"
        self.calm_mode = False
        self.since_ts = time.time()
        self._lead_since: float | None = None
        self._heading_signs: list[float] = []
        self._last_person: dict[str, Any] = {}
        self._alert_id: str | None = None
        self._cmd_n = 0
        self._say_n = 0
        self._said_for_state: set[str] = set()
        self._consent_ts: float | None = 1758290000.0
        self._voice_id = "sarah_clone_v1"
        self._attr_name = "Sarah"
        self._zones_by_id: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        self.bus.subscribe(self.on_message)
        await self._set_state("IDLE", "night watch idle", agitation="calm")

    async def on_message(self, msg: dict[str, Any]) -> None:
        t = msg.get("type")
        p = msg.get("payload") or {}
        if t == "config_update":
            patient = p.get("patient") or {}
            if patient.get("name"):
                self.patient_name = patient["name"]
            voice = p.get("voice") or {}
            if voice.get("voice_id"):
                self._voice_id = voice["voice_id"]
            if voice.get("attribution_name"):
                self._attr_name = voice["attribution_name"]
            if voice.get("consent_recorded_ts") is not None:
                self._consent_ts = float(voice["consent_recorded_ts"])
            for z in p.get("zones") or []:
                if z.get("id"):
                    self._zones_by_id[z["id"]] = z
            return
        if t == "caregiver_ack":
            await self._on_ack(p)
            return
        if t == "person_track":
            await self._on_track(p)
            return
        if t == "zone_event":
            await self._on_zone(p)
            return

    async def _on_ack(self, p: dict[str, Any]) -> None:
        by = p.get("by", "caregiver")
        action = p.get("action", "im_coming")
        self._alert_id = None
        self._lead_since = None
        self._said_for_state.clear()
        await self._set_state(
            "IDLE",
            f"caregiver ack — {by} {action}",
            agitation="calm",
        )

    async def _on_zone(self, p: dict[str, Any]) -> None:
        # True breach = left the Don't-go zone to the outdoors (mock sets outside=True).
        # Leaving front_door back into hallway is not EMERGENCY.
        if (
            p.get("zone_class") == "exit"
            and p.get("event") == "exited"
            and p.get("outside") is True
        ):
            await self._set_state(
                "EMERGENCY",
                f"dont_go_breach zone={p.get('zone_id')}",
                agitation="agitated",
            )
            await self._emit_alert(level=5, live_tracking=True)
            return
        if p.get("zone_class") == "exit" and p.get("event") in ("approaching", "entered"):
            if self.state in ("IDLE", "ATTEND", "LEAD"):
                if self.state != "LEAD":
                    await self._enter_lead(
                        f"zone_event {p.get('event')} {p.get('zone_id')}"
                    )

    async def _on_track(self, p: dict[str, Any]) -> None:
        self._last_person = p
        if p.get("posture") == "lying" and (p.get("zone") not in ("bedroom", "bed")):
            await self._set_state("EMERGENCY", "fall posture outside bed", agitation="agitated")
            await self._emit_alert(level=5, headline=f"{self.patient_name} may have fallen")
            return

        vx = float(p.get("vx") or 0)
        if abs(vx) > 0.05:
            self._heading_signs.append(1.0 if vx > 0 else -1.0)
            self._heading_signs = self._heading_signs[-8:]

        reversals = sum(
            1
            for i in range(1, len(self._heading_signs))
            if self._heading_signs[i] != self._heading_signs[i - 1]
        )

        projected = p.get("projected_zone")
        ttz = p.get("ttz_s")
        zone = p.get("zone")
        projected_exit = False
        zi = self._zones_by_id.get(projected or "")
        if zi and zi.get("class") == "exit":
            projected_exit = True
        elif projected == "front_door":
            projected_exit = True
        elif (
            isinstance(ttz, (int, float))
            and ttz is not None
            and float(ttz) < TTZ_LEAD_S
            and zone in ("hallway", "front_door")
        ):
            projected_exit = True

        if self.state == "IDLE":
            if reversals >= 3 or zone == "hallway":
                await self._set_state(
                    "ATTEND",
                    f"{reversals} direction reversals / zone={zone}",
                    agitation="unsettled",
                )
                await self._maybe_say(
                    f"It's night time, {self.patient_name}. You're home.",
                    tone="soothing",
                )
        if self.state in ("IDLE", "ATTEND") and projected_exit:
            reason = f"projected_zone={projected} ttz={ttz}s"
            await self._enter_lead(reason)

        if self.state == "LEAD" and self._lead_since is not None:
            if time.time() - self._lead_since >= LEAD_TO_ESCALATE_S:
                # Still near door?
                if zone == "front_door" or projected == "front_door" or projected_exit:
                    await self._set_state(
                        "ESCALATE",
                        f"{int(LEAD_TO_ESCALATE_S)}s no redirection",
                        agitation="agitated",
                    )
                    await self._emit_alert(level=2)
                    await self._maybe_say(
                        f"I'm here with you, {self.patient_name}. Help is on the way.",
                        tone="warm",
                    )

        # Return to bedroom while ATTEND/LEAD (not after alert) → IDLE
        if self.state in ("LEAD", "ATTEND") and zone == "bedroom" and not projected_exit:
            await self._set_state("IDLE", "returned to safe zone", agitation="calm")
            self._lead_since = None

    async def _enter_lead(self, reason: str) -> None:
        if self.state == "LEAD":
            return
        await self._set_state("LEAD", reason, agitation="agitated")
        self._lead_since = time.time()
        self._cmd_n += 1
        await self.bus.publish(
            "command",
            {
                "command_id": f"cmd_{self._cmd_n}",
                "action": "lead_to",
                "args": {"zone_id": "bedroom", "speed_max": 0.3, "standoff_m": 1.5},
            },
            source="orchestrator",
        )
        await self._maybe_say("Come with me.", tone="soothing")

    async def _set_state(self, state: str, reason: str, *, agitation: str | None = None) -> None:
        if agitation:
            self.agitation = agitation
        prev = self.state
        if prev == state and state != "IDLE":
            # Still publish IDLE→IDLE on boot only
            return
        self.previous = prev
        self.state = state
        self.since_ts = time.time()
        if state != prev:
            self._said_for_state.discard(state)
        await self.bus.publish(
            "agent_state",
            {
                "state": state,
                "previous": prev if prev != state else self.previous,
                "agitation": self.agitation,
                "calm_mode": self.calm_mode,
                "reason": reason,
                "since_ts": self.since_ts,
            },
            source="orchestrator",
        )
        logger.info("state %s → %s (%s)", prev, state, reason)

    async def _maybe_say(self, text: str, *, tone: str = "soothing") -> None:
        key = f"{self.state}:{text}"
        if key in self._said_for_state:
            return
        if self._consent_ts is None:
            logger.warning("refusing say — no consent_recorded_ts")
            return
        self._said_for_state.add(key)
        self._say_n += 1
        await self.bus.publish(
            "say",
            {
                "utterance_id": f"u_{self._say_n}",
                "text": text,
                "voice_id": self._voice_id,
                "tone": tone,
                "interruptible": True,
                "attribution": f"{self._attr_name} recorded this for you",
                "origin": "policy",
            },
            source="orchestrator",
        )

    async def _emit_alert(
        self,
        *,
        level: int = 2,
        headline: str | None = None,
        live_tracking: bool = False,
    ) -> None:
        person = self._last_person
        self._alert_id = f"al_{uuid.uuid4().hex[:6]}"
        zone = person.get("zone", "hallway")
        hx = float(person.get("x", 0))
        hy = float(person.get("y", 0))
        headline = headline or f"{self.patient_name} is heading for the front door"
        detail = (
            f"Redirection attempted for {int(LEAD_TO_ESCALATE_S)}s. "
            f"They're near {zone}."
        )
        channels = ["sms", "push"]
        if level >= 3:
            channels.append("voice_call")
        await self.bus.publish(
            "alert",
            {
                "alert_id": self._alert_id,
                "level": level,
                "headline": headline,
                "detail": detail,
                "person_position": {"x": hx, "y": hy, "zone": zone},
                "requires_ack": True,
                "channels": channels,
                "context": "night_breach",
                "live_tracking": live_tracking,
            },
            source="orchestrator",
        )

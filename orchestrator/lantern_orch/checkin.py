"""Check-in → say queue. Deliver only while IDLE (04-interfaces)."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from lantern_bus.core import Bus

logger = logging.getLogger("lantern.orch.checkin")


class CheckinQueue:
    def __init__(self, bus: Bus, machine: Any) -> None:
        self.bus = bus
        self.machine = machine
        self._q: deque[dict[str, Any]] = deque()
        self._say_n = 0

    async def start(self) -> None:
        self.bus.subscribe(self.on_message)

    async def on_message(self, msg: dict[str, Any]) -> None:
        if msg.get("type") == "checkin":
            self._q.append(msg.get("payload") or {})
            logger.info("checkin queued (%d)", len(self._q))
            await self._drain()
            return
        if msg.get("type") == "agent_state":
            await self._drain()

    async def _drain(self) -> None:
        if self.machine.state != "IDLE":
            return
        while self._q:
            p = self._q.popleft()
            self._say_n += 1
            name = p.get("from_name", "Family")
            text = p.get("text", "")
            await self.bus.publish(
                "say",
                {
                    "utterance_id": f"ck_{self._say_n}",
                    "text": text,
                    "voice_id": getattr(self.machine, "_voice_id", "sarah_clone_v1"),
                    "tone": "warm",
                    "interruptible": True,
                    "attribution": f"{name} sent you this message",
                    "origin": "checkin",
                },
                source="orchestrator",
            )
            logger.info("delivered checkin from %s", name)

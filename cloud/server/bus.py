"""Thin bus adapter. ONE file to change when E4 picks a real transport.

Current path (works today, no E4 required):
  replay.py / orchestrator  →  POST /api/ingest  →  bus.ingest()  →  store + WS clients

When E4 ships a shared transport (Redis / in-proc queue / WS hub), replace the body of
`ingest` / `publish` here only — main.py, store.py, and the React portal stay put.

Outbound cloud messages (caregiver_ack, config_update, checkin) go through `publish`,
which also locally `ingest`s so the portal sees its own writes immediately.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("lantern.bus")

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class Bus:
    def __init__(self) -> None:
        self._handlers: list[MessageHandler] = []
        self._outbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._seq = 0

    def subscribe(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    async def publish(self, msg: dict[str, Any]) -> None:
        """Cloud → bus (caregiver_ack, config_update, checkin)."""
        if "seq" not in msg:
            self._seq += 1
            msg = {**msg, "seq": self._seq}
        if "source" not in msg:
            msg = {**msg, "source": "cloud"}
        logger.info("publish %s", msg.get("type"))
        await self._outbound.put(msg)
        # Echo local publishes into handlers so the portal sees its own acks/config.
        await self.ingest(msg)

    async def ingest(self, msg: dict[str, Any]) -> None:
        """Inbound path used by fixture replay and (later) the real transport."""
        for handler in list(self._handlers):
            result = handler(msg)
            if asyncio.iscoroutine(result):
                await result

    async def drain_outbound(self) -> dict[str, Any]:
        return await self._outbound.get()


# Singleton used by main / replay / escalation
bus = Bus()

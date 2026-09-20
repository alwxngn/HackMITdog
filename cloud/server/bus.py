"""Thin bus adapter. ONE file to change when E4 picks a real transport.

Inbound (E4 spine / replay):
  orchestrator bridge  →  POST /api/ingest  →  bus.ingest()  →  store + WS clients

Outbound (caregiver_ack, config_update, checkin):
  bus.publish() → local ingest + outbound queue
  + optional POST to LANTERN_ORCH_PUBLISH_URL (bus hub /publish) so E4 hears acks.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger("lantern.bus")

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class Bus:
    def __init__(self) -> None:
        self._handlers: list[MessageHandler] = []
        self._outbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._seq = 0
        self._orch_url = os.getenv("LANTERN_ORCH_PUBLISH_URL", "").rstrip("/")

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
        if self._orch_url:
            await self._forward_orch(msg)

    async def _forward_orch(self, msg: dict[str, Any], *, required: bool = False) -> None:
        if not self._orch_url:
            if required:
                raise RuntimeError("Robot connection is not configured. Set LANTERN_ORCH_PUBLISH_URL on the cloud server.")
            return
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(f"{self._orch_url}/publish", json=msg)
                response.raise_for_status()
        except Exception as e:
            logger.warning("orch forward failed: %s", e)
            if required:
                raise RuntimeError("Could not deliver the robot request. Check the robot bridge connection before trying again.") from e

    async def ingest(self, msg: dict[str, Any]) -> None:
        """Inbound path used by fixture replay and the E4 bridge."""
        for handler in list(self._handlers):
            result = handler(msg)
            if asyncio.iscoroutine(result):
                await result
        # Inbound events may already have travelled through the orchestrator.
        # Only the originating phone bridge forwards robot-request transcripts.

    async def drain_outbound(self) -> dict[str, Any]:
        return await self._outbound.get()

    def drain_outbound_nowait(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        while True:
            try:
                out.append(self._outbound.get_nowait())
            except asyncio.QueueEmpty:
                break
        return out


# Singleton used by main / replay / escalation
bus = Bus()

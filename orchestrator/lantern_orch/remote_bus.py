"""Bus adapter for the external WebSocket hub used by the real robot stack."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from lantern_bus.core import Bus

logger = logging.getLogger("lantern.orch.remote_bus")


class RemoteBus:
    def __init__(self, local: Bus, url: str) -> None:
        self.local = local
        self.url = url
        self._ws: Any = None
        self._send_lock = asyncio.Lock()
        self._inbound = False

    async def start(self) -> None:
        self.local.subscribe(self._on_local)
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    logger.info("connected to bus hub %s", self.url)
                    async for raw in ws:
                        self._inbound = True
                        try:
                            await self.local.emit(json.loads(raw))
                        finally:
                            self._inbound = False
            except Exception as exc:
                logger.warning("bus hub connection failed: %s; retrying", exc)
                await asyncio.sleep(2)
            finally:
                self._ws = None

    async def publish(self, msg: dict[str, Any]) -> None:
        async with self._send_lock:
            if self._ws is not None:
                await self._ws.send(json.dumps(msg))

    async def _on_local(self, msg: dict[str, Any]) -> None:
        if not self._inbound:
            await self.publish(msg)

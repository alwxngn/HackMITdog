"""Bridge shared bus ↔ cloud POST /api/ingest (+ cloud outbound → bus)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from lantern_bus.core import Bus

logger = logging.getLogger("lantern.orch.bridge")

# Types cloud originates that must re-enter the orch bus
CLOUD_OUTBOUND = frozenset({"caregiver_ack", "config_update", "checkin", "map_scan_request"})


class CloudBridge:
    """Forward every bus message to cloud ingest; pull cloud publishes back."""

    def __init__(
        self,
        bus: Bus,
        cloud_base: str = "http://127.0.0.1:8000",
        *,
        skip_echo: bool = True,
    ) -> None:
        self.bus = bus
        self.cloud_base = cloud_base.rstrip("/")
        self.skip_echo = skip_echo
        self._client: httpx.AsyncClient | None = None
        self._forwarding = False
        self._seen: set[tuple[Any, ...]] = set()

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)
        self.bus.subscribe(self._on_bus)
        asyncio.create_task(self._ws_cloud_loop())
        logger.info("bridge → %s/api/ingest", self.cloud_base)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    def _key(self, msg: dict[str, Any]) -> tuple[Any, ...]:
        return (msg.get("type"), msg.get("source"), msg.get("seq"), msg.get("ts"))

    async def _on_bus(self, msg: dict[str, Any]) -> None:
        if self._forwarding:
            return
        # RemoteBus already received cloud-originated events from the shared
        # hub. Posting those back would create a cloud → hub → cloud loop.
        # Robot events still need to travel hub → orchestrator → cloud so the
        # dashboard can display real robot status.
        is_remote = getattr(self.bus, "is_remote_message", None)
        if is_remote and is_remote(msg) and msg.get("source") in {"cloud", "voice"}:
            return
        # Avoid re-POSTing messages we just pulled from cloud
        k = self._key(msg)
        if k in self._seen:
            return
        assert self._client is not None
        try:
            r = await self._client.post(f"{self.cloud_base}/api/ingest", json=msg)
            if r.status_code >= 400:
                logger.warning("ingest %s → %s %s", msg.get("type"), r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("ingest failed: %s", e)

    async def _ws_cloud_loop(self) -> None:
        """Mirror cloud-originated messages onto the orch bus (acks, checkins)."""
        url = self.cloud_base.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        while True:
            try:
                await self._connect_ws(url)
            except Exception as e:
                logger.warning("cloud ws reconnect in 2s: %s", e)
                await asyncio.sleep(2.0)

    async def _connect_ws(self, url: str) -> None:
        try:
            import websockets
        except ImportError:
            await self._poll_outbound()
            return
        async with websockets.connect(url) as ws:
            logger.info("bridged cloud WS %s", url)
            async for raw in ws:
                import json

                msg = json.loads(raw)
                if msg.get("type") == "snapshot":
                    continue
                if msg.get("type") not in CLOUD_OUTBOUND and msg.get("source") != "cloud":
                    continue
                if msg.get("type") not in CLOUD_OUTBOUND:
                    continue
                k = self._key(msg)
                self._seen.add(k)
                if len(self._seen) > 5000:
                    self._seen = set(list(self._seen)[-1000:])
                self._forwarding = True
                try:
                    await self.bus.emit(msg)
                finally:
                    self._forwarding = False

    async def _poll_outbound(self) -> None:
        """Fallback when websockets package missing: poll /api/outbound."""
        assert self._client is not None
        while True:
            try:
                r = await self._client.get(f"{self.cloud_base}/api/outbound")
                if r.status_code == 200:
                    data = r.json()
                    for msg in data.get("messages") or []:
                        if msg.get("type") in CLOUD_OUTBOUND:
                            k = self._key(msg)
                            if k in self._seen:
                                continue
                            self._seen.add(k)
                            self._forwarding = True
                            try:
                                await self.bus.emit(msg)
                            finally:
                                self._forwarding = False
            except Exception as e:
                logger.debug("outbound poll: %s", e)
            await asyncio.sleep(0.5)

"""Async adapter for the shared HTTP/WebSocket bus hub.

The normal :class:`lantern_bus.core.Bus` is process-local.  This adapter gives
the real-robot orchestrator the same small interface while connecting it to a
hub started by ``bus/run_hub.py``.  It deliberately contains no robot or
DimOS code.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import websockets

from lantern_bus.envelope import make_envelope

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]
logger = logging.getLogger("lantern.orch.remote_bus")


class RemoteBus:
    """Bus-compatible client for a running Lantern bus hub."""

    def __init__(self, url: str, *, log_path: str | Path | None = None) -> None:
        self.url = url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
        if not self.url.endswith("/ws"):
            self.url += "/ws"
        self._handlers: list[MessageHandler] = []
        self._seqs: dict[str, int] = {}
        self._ws: Any = None
        self._ready = asyncio.Event()
        self._stopping = False
        self._sent_keys: set[tuple[Any, ...]] = set()
        self.log_path = Path(log_path) if log_path else None

    def subscribe(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: MessageHandler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def connect(self) -> None:
        """Connect and start the receive/reconnect task."""
        asyncio.create_task(self._connection_loop())
        await self._ready.wait()

    async def close(self) -> None:
        self._stopping = True
        ws = self._ws
        if ws is not None:
            await ws.close()

    async def publish(
        self,
        type_: str,
        payload: dict[str, Any],
        *,
        source: str = "orchestrator",
        ts: float | None = None,
        seq: int | None = None,
    ) -> dict[str, Any]:
        """Create, dispatch, and publish an envelope through the hub."""
        if seq is None:
            self._seqs[source] = self._seqs.get(source, 0) + 1
            seq = self._seqs[source]
        msg = make_envelope(type_, payload, source=source, seq=seq, ts=ts)
        await self.emit(msg)
        await self._send(msg)
        return msg

    async def emit(self, msg: dict[str, Any]) -> None:
        """Dispatch a message to local orchestrator subscribers."""
        msg = {**msg}
        msg.setdefault("ts", time.time())
        msg.setdefault("source", "mock")
        if "seq" not in msg or msg["seq"] is None:
            source = str(msg["source"])
            self._seqs[source] = self._seqs.get(source, 0) + 1
            msg["seq"] = self._seqs[source]
        self._append_log(msg)
        for handler in list(self._handlers):
            result = handler(msg)
            if asyncio.iscoroutine(result):
                await result

    async def _send(self, msg: dict[str, Any]) -> None:
        key = self._key(msg)
        self._sent_keys.add(key)
        if len(self._sent_keys) > 5000:
            self._sent_keys = set(list(self._sent_keys)[-1000:])
        await self._ready.wait()
        await self._ws.send(json.dumps(msg))

    async def _connection_loop(self) -> None:
        while not self._stopping:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    self._ready.set()
                    logger.info("connected to bus hub %s", self.url)
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "pong":
                            continue
                        await self._dispatch_if_new(msg)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._ready.clear()
                self._ws = None
                if not self._stopping:
                    logger.warning("bus hub connection failed: %s; retrying", exc)
                    await asyncio.sleep(2)

    @staticmethod
    def _key(msg: dict[str, Any]) -> tuple[Any, ...]:
        return (msg.get("type"), msg.get("source"), msg.get("seq"), msg.get("ts"))

    async def _dispatch_if_new(self, msg: dict[str, Any]) -> None:
        if self._key(msg) in self._sent_keys:
            return
        await self.emit(msg)

    def _append_log(self, msg: dict[str, Any]) -> None:
        if not self.log_path:
            return
        try:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(msg, separators=(",", ":")) + "\n")
        except OSError:
            logger.exception("could not write bus log")

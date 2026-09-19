"""In-process asyncio bus with JSONL logging (04-interfaces rule 3)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .envelope import Source, make_envelope

logger = logging.getLogger("lantern.bus")

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]

_bus_singleton: Bus | None = None


class Bus:
    def __init__(self, log_path: str | Path | None = None) -> None:
        self._handlers: list[MessageHandler] = []
        self._seqs: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self.log_path = Path(log_path) if log_path else Path("bus_events.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def next_seq(self, source: str) -> int:
        self._seqs[source] = self._seqs.get(source, 0) + 1
        return self._seqs[source]

    def subscribe(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: MessageHandler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def publish(
        self,
        type_: str,
        payload: dict[str, Any],
        *,
        source: Source = "mock",
        ts: float | None = None,
        seq: int | None = None,
    ) -> dict[str, Any]:
        msg = make_envelope(
            type_,
            payload,
            source=source,
            seq=seq if seq is not None else self.next_seq(source),
            ts=ts,
        )
        await self.emit(msg)
        return msg

    async def emit(self, msg: dict[str, Any]) -> None:
        """Fan-out a fully-formed envelope (used by HTTP hub + local publishers)."""
        msg.setdefault("ts", time.time())
        msg.setdefault("source", "mock")
        if "seq" not in msg or msg["seq"] is None:
            msg["seq"] = self.next_seq(str(msg.get("source", "mock")))
        self._append_jsonl(msg)
        logger.debug("bus %s from %s", msg.get("type"), msg.get("source"))
        for handler in list(self._handlers):
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("handler failed on %s", msg.get("type"))

    def _append_jsonl(self, msg: dict[str, Any]) -> None:
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
        except OSError:
            logger.exception("jsonl write failed")


def get_bus(log_path: str | Path | None = None) -> Bus:
    global _bus_singleton
    if _bus_singleton is None:
        _bus_singleton = Bus(log_path=log_path)
    return _bus_singleton

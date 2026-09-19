"""Common envelope helpers. Field names match docs/04-interfaces.md exactly."""

from __future__ import annotations

import time
from typing import Any, Literal

Source = Literal["robot", "voice", "orchestrator", "cloud", "mock"]
SOURCES: tuple[str, ...] = ("robot", "voice", "orchestrator", "cloud", "mock")


def make_envelope(
    type_: str,
    payload: dict[str, Any],
    *,
    source: Source = "mock",
    seq: int = 0,
    ts: float | None = None,
) -> dict[str, Any]:
    return {
        "type": type_,
        "ts": time.time() if ts is None else ts,
        "source": source,
        "seq": seq,
        "payload": payload,
    }

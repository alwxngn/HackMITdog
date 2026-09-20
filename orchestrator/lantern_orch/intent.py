"""Deterministic speech intents, including Unitree's named sport tricks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    text: str
    command_name: str | None = None


TRICKS: dict[str, tuple[str, ...]] = {
    "Hello": ("say hello", "wave", "do a hello", "greet me"),
    "Sit": ("sit", "sit down"),
    "StandUp": ("stand", "stand up", "get up"),
    "StandDown": ("stand down", "lie down", "lay down", "down"),
    "Stretch": ("stretch", "do a stretch"),
    "Dance1": ("dance", "dance for me", "do a dance"),
    "Dance2": ("dance two", "do dance two"),
    "FrontJump": ("jump", "jump forward", "do a jump"),
    "FrontFlip": ("front flip", "do a front flip"),
    "Backflip": ("back flip", "do a backflip"),
    "Handstand": ("handstand", "do a handstand"),
    "WiggleHips": ("wiggle", "wiggle your hips", "wiggle hips"),
    "MoonWalk": ("moonwalk", "moon walk"),
    "Wallow": ("roll over", "roll around", "wallow"),
    "RecoveryStand": ("recover", "recovery stand", "get stable"),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text.lower())).strip()


def classify(text: str) -> Intent | None:
    normalized = _normalize(text)
    if not normalized:
        return None
    # Longest/specific phrases win over short aliases such as "stand".
    for command_name, phrases in sorted(TRICKS.items(), key=lambda item: max(map(len, item[1])), reverse=True):
        if any(normalized == phrase or re.search(rf"\b{re.escape(phrase)}\b", normalized) for phrase in phrases):
            return Intent("TRICK", normalized, command_name)
    return None

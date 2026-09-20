"""Deterministic voice intent recognition for walks, home, and Go2 tricks."""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Intent:
    name: str
    text: str
    command_name: str | None = None

TRICKS = {
    "Hello": ("say hello", "wave"), "Sit": ("sit", "sit down"),
    "StandUp": ("stand", "stand up", "get up"), "StandDown": ("stand down", "lie down", "lay down"),
    "Stretch": ("stretch",), "Dance1": ("dance", "dance for me"), "Dance2": ("dance two",),
    "FrontJump": ("jump", "jump forward"), "FrontFlip": ("front flip",), "Backflip": ("back flip", "backflip"),
    "Handstand": ("handstand",), "WiggleHips": ("wiggle", "wiggle hips"),
    "MoonWalk": ("moonwalk", "moon walk"), "Wallow": ("roll over", "roll around", "wallow"),
    "RecoveryStand": ("recover", "recovery stand"),
}

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text.lower())).strip()

def classify(text: str, *, awaiting_confirmation: bool = False) -> Intent | None:
    n = _normalize(text)
    if not n: return None
    if n in {"stop", "stop walking", "stop following", "never mind", "cancel"}:
        return Intent("STOP", n)
    if awaiting_confirmation:
        if n in {"yes", "yeah", "yep", "yes please", "go home", "take me home"} or re.match(r"^(yes|yeah|yep)\b", n): return Intent("CONFIRM_HOME_YES", n)
        if n in {"no", "no thanks", "not now", "stay here", "keep walking"} or re.match(r"^(no|not now)\b", n): return Intent("CONFIRM_HOME_NO", n)
        return None
    if re.search(r"\b(take me home|go home|go back home|return home|back to where we started)\b", n): return Intent("TAKE_ME_HOME", n)
    if re.search(r"\b(go for a walk|go on a walk|take a walk|take me for a walk|let's walk|lets walk|walk with me|follow me|go outside)\b", n): return Intent("START_WALK", n)
    for command, phrases in sorted(TRICKS.items(), key=lambda x: max(map(len, x[1])), reverse=True):
        if any(n == p or re.search(rf"\b{re.escape(p)}\b", n) for p in phrases): return Intent("TRICK", n, command)
    return None

"""Small, deterministic voice command recognizer for movement intents.

Movement decisions must not depend on an LLM guessing what a transcript means.
This module intentionally returns no intent for ambiguous language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    text: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text.lower())).strip()


def classify(text: str, *, awaiting_confirmation: bool = False) -> Intent | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    if awaiting_confirmation:
        if normalized in {"yes", "yeah", "yep", "yes please", "go home", "take me home"} or re.match(r"^(yes|yeah|yep)\b", normalized):
            return Intent("CONFIRM_HOME_YES", normalized)
        if normalized in {"no", "no thanks", "not now", "stay here", "keep walking"} or re.match(r"^(no|not now)\b", normalized):
            return Intent("CONFIRM_HOME_NO", normalized)
        return None

    if re.search(r"\b(take me home|go home|go back home|return home|back to where we started)\b", normalized):
        return Intent("TAKE_ME_HOME", normalized)
    if re.search(r"\b(go for a walk|go on a walk|take a walk|take me for a walk|let's walk|lets walk|walk with me|follow me|go outside|let's go outside|lets go outside)\b", normalized):
        return Intent("START_WALK", normalized)
    if normalized in {"stop", "stop walking", "stop following", "never mind", "cancel"}:
        return Intent("STOP", normalized)
    return None

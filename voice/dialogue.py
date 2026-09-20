"""Small, explicit demo dialogue. No invented family facts or medical judgments."""
import re

# Demo: always the same acknowledgement, regardless of what was said. Distress detection
# still runs underneath so the caregiver dashboard is still flagged for review.
_ACKNOWLEDGEMENT = "Thank you. Your caregiver can view your message on their dashboard."


def reply_to(text: str, patient: str, caregiver: str) -> tuple[str, bool]:
    normalized = re.sub(r"[^\w\s]", " ", text.lower())
    attention = bool(re.search(r"\b(help|hurt|pain|scared|afraid|not (?:okay|ok|well|fine))\b", normalized))
    return _ACKNOWLEDGEMENT, attention

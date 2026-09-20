"""Small, explicit demo dialogue. No invented family facts or medical judgments."""
import re


def reply_to(text: str, patient: str, caregiver: str) -> tuple[str, bool]:
    normalized = re.sub(r"[^\w\s]", " ", text.lower())
    if re.search(r"\b(who are you|are you|is that you|is this)\b", normalized) or normalized.strip() == caregiver.lower():
        return f"I'm Lantern, your robot companion. {caregiver} sent the check-in.", False
    if re.search(r"\b(help|hurt|pain|scared|afraid|not (?:okay|ok|well|fine))\b", normalized):
        return "I've marked your reply for your caregiver to review. I'm here with you.", True
    if re.search(r"\b(stop|leave me alone|be quiet)\b", normalized):
        return "Okay. I'll give you some quiet.", False
    if "where" in normalized or "when" in normalized:
        return "I don't have that information yet. Your caregiver can see your question.", False
    if re.search(r"\b(fine|good|okay|ok|well)\b", normalized):
        return f"Thank you for telling me, {patient}. Would you like to tell me about your day?", False
    return "Thank you for telling me. Your reply is on your caregiver's dashboard.", False

"""Twilio SMS + voice call. Degrades to console log when credentials missing."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("lantern.notify")


def _client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    from twilio.rest import Client

    return Client(sid, token)


def _from_number() -> str | None:
    return os.getenv("TWILIO_FROM_NUMBER")


def _to_number(contact: str = "jenny") -> str | None:
    # Map contact nicknames to env vars; default to TWILIO_TO_NUMBER.
    key = f"TWILIO_TO_{contact.upper()}"
    return os.getenv(key) or os.getenv("TWILIO_TO_NUMBER")


def send_sms(headline: str, detail: str, alert_id: str, ack_base_url: str) -> dict[str, Any]:
    body = f"{headline}\n{detail}\nAck: {ack_base_url.rstrip('/')}/api/ack?alert_id={alert_id}"
    to = _to_number()
    from_ = _from_number()
    client = _client()
    if not client or not to or not from_:
        logger.warning("Twilio not configured — SMS dry-run to=%s body=%s", to, body)
        return {"ok": False, "dry_run": True, "body": body, "to": to}
    msg = client.messages.create(body=body, from_=from_, to=to)
    logger.info("SMS sent sid=%s to=%s", msg.sid, to)
    return {"ok": True, "sid": msg.sid, "to": to}


def place_voice_call(headline: str, contact: str = "jenny") -> dict[str, Any]:
    to = _to_number(contact)
    from_ = _from_number()
    client = _client()
    # TwiML: say the headline then hang up. For demo, inline Twiml works.
    twiml = f'<Response><Say voice="alice">{headline}. Press any key if you have this. Lantern.</Say></Response>'
    if not client or not to or not from_:
        logger.warning("Twilio not configured — voice dry-run to=%s: %s", to, headline)
        return {"ok": False, "dry_run": True, "to": to, "headline": headline}
    call = client.calls.create(twiml=twiml, to=to, from_=from_)
    logger.info("Voice call sid=%s to=%s", call.sid, to)
    return {"ok": True, "sid": call.sid, "to": to}

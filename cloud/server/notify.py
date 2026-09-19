"""Twilio SMS + voice call. Degrades to console log when credentials missing.

Trial accounts (Twilio 2025+): you cannot send free-form SMS. The Messages API
`body` must be one of Twilio's predefined template names, e.g. sms_account_alerts.
Set TWILIO_TRIAL=1 (default if unset when send fails) or leave TWILIO_TRIAL=1 in .env.

Upgrade the Twilio account (add a card / pay-as-you-go) to send custom bodies —
required for the real demo headline. Until then, the phone still buzzes with a
Twilio sample SMS, and the portal shows the real alert.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

# Load cloud/.env regardless of cwd
_CLOUD_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_CLOUD_ROOT, ".env"))
load_dotenv()

logger = logging.getLogger("lantern.notify")

# Allowed trial body values — see https://www.twilio.com/docs/usage/trials/try-out-sms
TRIAL_TEMPLATES = {
    "sms_2fa",
    "sms_appointment_reminders",
    "sms_order_confirmation",
    "sms_delivery_updates",
    "sms_customer_support",
    "sms_marketing_promotions",
    "sms_event_notifications",
    "sms_account_alerts",
    "sms_feedback_surveys",
    "sms_internal_alerts",
}


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
    key = f"TWILIO_TO_{contact.upper()}"
    return os.getenv(key) or os.getenv("TWILIO_TO_NUMBER")


def _trial_mode() -> bool:
    return os.getenv("TWILIO_TRIAL", "1").strip() in {"1", "true", "True", "yes"}


def _sms_body(headline: str, detail: str, alert_id: str, ack_base_url: str) -> str:
    """Custom body for upgraded accounts; template name for trial."""
    custom = f"{headline}\n{detail}\nAck: {ack_base_url.rstrip('/')}/api/ack?alert_id={alert_id}"
    if not _trial_mode():
        return custom
    template = os.getenv("TWILIO_TRIAL_TEMPLATE", "sms_account_alerts")
    if template not in TRIAL_TEMPLATES:
        logger.warning("Unknown TWILIO_TRIAL_TEMPLATE=%s — using sms_account_alerts", template)
        template = "sms_account_alerts"
    logger.info(
        "Trial SMS: sending template %s (custom text not allowed). Real alert: %s",
        template,
        custom.replace("\n", " | "),
    )
    return template


def send_sms(headline: str, detail: str, alert_id: str, ack_base_url: str) -> dict[str, Any]:
    body = _sms_body(headline, detail, alert_id, ack_base_url)
    custom = f"{headline}\n{detail}\nAck: {ack_base_url.rstrip('/')}/api/ack?alert_id={alert_id}"
    to = _to_number()
    from_ = _from_number()
    client = _client()
    if not client or not to or not from_:
        logger.warning("Twilio not configured — SMS dry-run to=%s body=%s", to, custom)
        return {"ok": False, "dry_run": True, "body": custom, "to": to}
    try:
        msg = client.messages.create(body=body, from_=from_, to=to)
    except Exception as e:
        # Common: trial rejecting custom body — retry once with template
        err = str(e)
        if "572006" in err or "predefined SMS templates" in err or "Invalid template" in err:
            template = os.getenv("TWILIO_TRIAL_TEMPLATE", "sms_account_alerts")
            logger.warning("Twilio trial blocked custom SMS — retrying with %s", template)
            msg = client.messages.create(body=template, from_=from_, to=to)
            logger.info("SMS sent (trial template) sid=%s to=%s", msg.sid, to)
            return {
                "ok": True,
                "sid": msg.sid,
                "to": to,
                "trial_template": template,
                "custom_body_logged": custom,
            }
        raise
    logger.info("SMS sent sid=%s to=%s", msg.sid, to)
    return {
        "ok": True,
        "sid": msg.sid,
        "to": to,
        "trial": _trial_mode(),
        "custom_body_logged": custom if _trial_mode() else None,
    }


def place_voice_call(headline: str, contact: str = "jenny") -> dict[str, Any]:
    to = _to_number(contact)
    from_ = _from_number()
    client = _client()
    twiml = (
        f'<Response><Say voice="alice">{headline}. '
        f"Press any key if you have this. Lantern.</Say></Response>"
    )
    if not client or not to or not from_:
        logger.warning("Twilio not configured — voice dry-run to=%s: %s", to, headline)
        return {"ok": False, "dry_run": True, "to": to, "headline": headline}
    call = client.calls.create(twiml=twiml, to=to, from_=from_)
    logger.info("Voice call sid=%s to=%s", call.sid, to)
    return {"ok": True, "sid": call.sid, "to": to}

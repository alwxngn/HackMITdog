"""One-shot Twilio SMS spike. Run after filling cloud/.env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notify  # noqa: E402


def main() -> None:
    missing = [
        k
        for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_TO_NUMBER")
        if not os.getenv(k)
    ]
    if missing:
        print("Missing env:", ", ".join(missing))
        print("Copy cloud/.env.example → cloud/.env and fill Twilio trial credentials.")
        print("Running dry-run anyway…")
    base = os.getenv("ACK_BASE_URL", "http://127.0.0.1:8000")
    try:
        result = notify.send_sms(
            "Susan is heading for the front door",
            "Lantern Twilio spike — tap ack if you got this.",
            "al_spike",
            base,
        )
    except Exception as e:
        print("FAILED:", e)
        print(
            "\nIf you see error 572006: trial accounts cannot send custom SMS.\n"
            "Keep TWILIO_TRIAL=1 in cloud/.env (uses sms_account_alerts template),\n"
            "or upgrade the Twilio account to send the real Lantern headline."
        )
        raise SystemExit(1) from e
    print(result)
    if result.get("ok") and result.get("trial_template"):
        print(
            "\nPhone should buzz with a Twilio sample alert (trial template).\n"
            "Portal still shows the real headline. Upgrade Twilio for custom SMS text."
        )
    elif result.get("ok"):
        print("\nSMS sent. Check your phone.")


if __name__ == "__main__":
    main()

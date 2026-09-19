"""One-shot Twilio SMS spike. Run after filling cloud/.env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Allow importing notify from this folder
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
    result = notify.send_sms(
        "Arthur is heading for the front door",
        "Lantern Twilio spike — tap ack if you got this.",
        "al_spike",
        base,
    )
    print(result)


if __name__ == "__main__":
    main()

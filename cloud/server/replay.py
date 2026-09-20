"""Replay a JSONL fixture at wall-clock rate into the bus.

Usage (from cloud/server, with server already running OR embedded):

  # Standalone: POST each message to a live server
  python replay.py --fixture ../fixtures/exit_seeking.jsonl --url http://127.0.0.1:8000/api/ingest

  # Speed: --rate 4 plays 4x faster
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

FIXTURE_DEFAULT = Path(__file__).resolve().parent.parent / "fixtures" / "exit_seeking.jsonl"


async def replay(path: Path, url: str, rate: float, loop: bool) -> None:
    raw = path.read_text(encoding="utf-8").strip().splitlines()
    messages = [json.loads(line) for line in raw if line.strip()]
    if not messages:
        print("empty fixture", file=sys.stderr)
        return

    # Normalize relative offsets from first ts
    t0 = messages[0]["ts"]
    offsets = [m["ts"] - t0 for m in messages]

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            wall0 = time.monotonic()
            for msg, off in zip(messages, offsets):
                target = wall0 + (off / rate)
                delay = target - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                # Rewrite ts to now so the portal feels live
                out = {**msg, "ts": time.time()}
                r = await client.post(url, json=out)
                r.raise_for_status()
                print(f"→ {out['type']:16s} seq={out.get('seq')} status={r.status_code}")
            if not loop:
                break
            print("--- loop ---")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", type=Path, default=FIXTURE_DEFAULT)
    ap.add_argument("--url", default="http://127.0.0.1:8000/api/ingest")
    ap.add_argument("--rate", type=float, default=1.0, help="playback speed multiplier")
    ap.add_argument("--loop", action="store_true")
    args = ap.parse_args()
    asyncio.run(replay(args.fixture, args.url, args.rate, args.loop))


if __name__ == "__main__":
    main()

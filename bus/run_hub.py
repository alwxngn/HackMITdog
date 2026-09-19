#!/usr/bin/env python3
"""Standalone bus hub: python run_hub.py [--port 9000]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn

from lantern_bus.core import get_bus
from lantern_bus.server import create_app


def main() -> None:
    p = argparse.ArgumentParser(description="Lantern shared event bus hub")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--log", default=str(ROOT / "bus_events.jsonl"))
    args = p.parse_args()
    bus = get_bus(args.log)
    app = create_app(bus)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

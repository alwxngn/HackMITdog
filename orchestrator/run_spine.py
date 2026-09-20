#!/usr/bin/env python3
"""Spine on mocks — bus + mock_patient + mock_robot + state machine + cloud bridge.

Prereq: cloud API on :8000
  cd cloud && source .venv/bin/activate && cd server && uvicorn main:app --port 8000

Run:
  cd orchestrator && python run_spine.py --scenario exit_seeking

Then open http://127.0.0.1:5173/watch
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bus"))
sys.path.insert(0, str(ROOT / "orchestrator"))

from lantern_bus.core import get_bus  # noqa: E402
from lantern_bus.server import create_app  # noqa: E402
from lantern_orch.bridge import CloudBridge  # noqa: E402
from lantern_orch.checkin import CheckinQueue  # noqa: E402
from lantern_orch.machine import StateMachine  # noqa: E402
from lantern_orch.zones import DEFAULT_ZONES  # noqa: E402
from mocks.mock_patient import MockPatient  # noqa: E402
from mocks.mock_robot import MockRobot  # noqa: E402

logger = logging.getLogger("lantern.spine")

DEFAULT_CONFIG = {
    "zones": DEFAULT_ZONES,
    "escalation": [
        {"level": 2, "contact": "jenny", "channel": "sms", "after_s": 0},
        {"level": 3, "contact": "jenny", "channel": "voice_call", "after_s": 60},
        {"level": 4, "contact": "mark", "channel": "voice_call", "after_s": 120},
        {
            "level": 5,
            "contact": "jenny",
            "channel": "voice_call",
            "after_s": 0,
            "trigger": "dont_go_breach",
        },
    ],
    "voice": {
        "voice_id": "sarah_clone_v1",
        "consent_recorded_ts": 1758290000.0,
        "attribution_name": "Sarah",
    },
    "patient": {
        "name": "Susan",
        "preferred_name": "",
        "calming_topics": ["fishing at Moosehead", "Bella the dog"],
        "avoid_topics": ["the loss of a spouse"],
        "music_url": "/media/susan_playlist.mp3",
        "schedule": {
            "wake_time": "07:30",
            "meals": ["08:00", "12:30", "18:00"],
            "walk_window": ["15:00", "16:30"],
            "notes": "likes the porch after lunch",
        },
        "home": {"x": 0.0, "y": 0.0, "lat": None, "lon": None},
        "route_id": None,
    },
}


async def run(args: argparse.Namespace) -> None:
    log_path = Path(args.log)
    bus = get_bus(log_path)
    # Reset log for clean demo
    if log_path.exists() and args.fresh_log:
        log_path.write_text("")

    machine = StateMachine(bus, patient_name="Susan")
    checkins = CheckinQueue(bus, machine)
    robot = MockRobot(bus, fail_rate=args.fail_rate)
    patient = MockPatient(bus, args.scenario, rate_hz=args.rate)
    bridge = CloudBridge(bus, cloud_base=args.cloud)

    await machine.start()
    await checkins.start()
    await robot.start()
    await bridge.start()

    # Optional local hub for other CLIs (voice teammate, etc.)
    hub_task = None
    if args.hub_port:
        import uvicorn

        config = uvicorn.Config(
            create_app(bus),
            host="0.0.0.0",
            port=args.hub_port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        hub_task = asyncio.create_task(server.serve())
        logger.info("bus hub on :%s", args.hub_port)

    await bus.publish("config_update", DEFAULT_CONFIG, source="cloud")
    logger.info("config seeded — running mock_patient --scenario %s", args.scenario)

    # Reset cloud projection so dashboard matches this run
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(f"{args.cloud.rstrip('/')}/api/reset", timeout=5.0)
            # Re-ingest config after reset
            await asyncio.sleep(0.2)
    except Exception as e:
        logger.warning("cloud reset skipped: %s (is uvicorn up?)", e)

    await bus.publish("config_update", DEFAULT_CONFIG, source="cloud")

    await patient.run(once=True)
    logger.info("patient scenario finished — waiting %ss for ack / idle", args.hold)
    await asyncio.sleep(args.hold)
    robot.stop()
    await bridge.stop()
    if hub_task:
        hub_task.cancel()
    logger.info("spine done — events in %s", log_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser(description="Lantern spine on mocks")
    p.add_argument("--scenario", default="exit_seeking")
    p.add_argument("--cloud", default="http://127.0.0.1:8000")
    p.add_argument("--rate", type=float, default=4.0)
    p.add_argument("--fail-rate", type=float, default=0.0)
    p.add_argument("--hold", type=float, default=8.0, help="seconds to wait after scenario")
    p.add_argument("--log", default=str(Path(__file__).parent / "spine_events.jsonl"))
    p.add_argument("--fresh-log", action="store_true", default=True)
    p.add_argument("--hub-port", type=int, default=9000, help="0 to disable HTTP hub")
    args = p.parse_args()
    if args.hub_port == 0:
        args.hub_port = None
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

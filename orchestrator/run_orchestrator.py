#!/usr/bin/env python3
"""Run the Lantern orchestrator against a real bus, without mock devices.

Prerequisites: cloud API on ``:8000`` and ``bus/run_hub.py`` on ``:9000``.
This process owns the intent/state machine and check-in queue only.  DimOS and
``robot/dimos_command_bridge.py`` remain separate hardware-facing processes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from lantern_orch.bridge import CloudBridge
from lantern_orch.checkin import CheckinQueue
from lantern_orch.machine import StateMachine
from lantern_orch.remote_bus import RemoteBus
from lantern_orch.zones import DEFAULT_ZONES

logger = logging.getLogger("lantern.orchestrator.runner")

DEFAULT_CONFIG = {
    "zones": DEFAULT_ZONES,
    "escalation": [],
    "voice": {
        "voice_id": "sarah_clone_v1",
        "consent_recorded_ts": 1758290000.0,
        "attribution_name": "Sarah",
    },
    "patient": {
        "name": "Arthur",
        "preferred_name": "Art",
        "home": {"x": 0.0, "y": 0.0, "lat": None, "lon": None},
    },
}


async def run(args: argparse.Namespace) -> None:
    bus = RemoteBus(args.bus_url, log_path=args.log)
    machine = StateMachine(bus, patient_name=args.patient_name)
    checkins = CheckinQueue(bus, machine)
    cloud = CloudBridge(bus, cloud_base=args.cloud)

    await bus.connect()
    await machine.start()
    await checkins.start()
    await cloud.start()
    await bus.publish("config_update", DEFAULT_CONFIG, source="cloud")
    logger.info("orchestrator ready; no mock patient or mock robot is running")

    try:
        await asyncio.Future()
    finally:
        await cloud.stop()
        await bus.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Lantern orchestrator without mock devices")
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--cloud", default="http://127.0.0.1:8000")
    parser.add_argument("--patient-name", default="Arthur")
    parser.add_argument("--log", default=str(Path(__file__).with_name("orchestrator_events.jsonl")))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        logger.info("orchestrator stopped")


if __name__ == "__main__":
    main()

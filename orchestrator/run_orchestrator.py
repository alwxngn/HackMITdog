#!/usr/bin/env python3
"""Run the real voice orchestrator without mock patient/robot processes."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bus"))
sys.path.insert(0, str(ROOT / "orchestrator"))

from lantern_bus.core import Bus  # noqa: E402
from lantern_orch.bridge import CloudBridge  # noqa: E402
from lantern_orch.machine import StateMachine  # noqa: E402
from lantern_orch.remote_bus import RemoteBus  # noqa: E402


async def run(args: argparse.Namespace) -> None:
    local = Bus(log_path=args.log)
    machine = StateMachine(local, patient_name=args.patient)
    remote = RemoteBus(local, args.bus_url)
    cloud = CloudBridge(local, cloud_base=args.cloud)
    await machine.start()
    await cloud.start()
    asyncio.create_task(remote.start())
    logging.getLogger("lantern.orchestrator.runner").info(
        "orchestrator ready; no mock patient or mock robot is running"
    )
    await asyncio.Event().wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="Lantern real robot orchestrator")
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--cloud", default="http://127.0.0.1:8000", help="kept for CLI compatibility")
    parser.add_argument("--patient", default="Susan")
    parser.add_argument("--log", default="orchestrator_events.jsonl")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

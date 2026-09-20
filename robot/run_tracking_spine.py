"""Run existing bus + orchestrator without a scripted patient. No robot SDKs."""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bus"))
sys.path.insert(0, str(ROOT / "orchestrator"))

from lantern_bus.core import Bus
from lantern_bus.server import create_app
from lantern_orch.machine import StateMachine
from lantern_orch.bridge import CloudBridge
from mocks.mock_robot import MockRobot


async def run(args):
    import uvicorn
    config = json.loads(Path(args.config).read_text())
    config = config.get("payload", config)
    bus = Bus(args.log)
    machine = StateMachine(bus, patient_name=(config.get("patient") or {}).get("name", "Susan"))
    await machine.start()
    bridge = CloudBridge(bus, cloud_base=args.cloud) if args.cloud else None
    robot = MockRobot(bus) if args.mock_robot else None
    if bridge:
        await bridge.start()
    if robot:
        await robot.start()
    await bus.publish("config_update", config, source="cloud")
    logging.info("Tracking spine ready; no mock patient. Robot consumer: %s", "mock" if robot else "external/none")
    try:
        await uvicorn.Server(uvicorn.Config(create_app(bus), host="127.0.0.1", port=args.port)).serve()
    finally:
        if robot:
            robot.stop()
        if bridge:
            await bridge.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="current config payload or config_update envelope JSON")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--log", default="tracking_bus_events.jsonl")
    parser.add_argument("--cloud", help="optional cloud API base, e.g. http://127.0.0.1:8000")
    parser.add_argument("--mock-robot", action="store_true", help="software test only; never combine with a real robot consumer")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(parser.parse_args()))

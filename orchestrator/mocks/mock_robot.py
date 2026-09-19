"""mock_robot — accepts command, emits pose + robot_status."""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bus"))
sys.path.insert(0, str(ROOT / "orchestrator"))

from lantern_bus.core import Bus, get_bus  # noqa: E402
from lantern_orch.zones import DEFAULT_ZONES, centroid  # noqa: E402

logger = logging.getLogger("lantern.mock_robot")


class MockRobot:
    def __init__(
        self,
        bus: Bus,
        *,
        fail_rate: float = 0.0,
        pose_hz: float = 5.0,
        map_id: str = "home_v3",
    ) -> None:
        self.bus = bus
        self.fail_rate = fail_rate
        self.pose_hz = pose_hz
        self.map_id = map_id
        self.x = 0.6
        self.y = 0.5
        self.theta = 0.0
        self.battery = 72.0
        self.mode = "standing"
        self._cmd: dict[str, Any] | None = None
        self._target: tuple[float, float] | None = None
        self._person: tuple[float, float] | None = None
        self._running = False
        self._zones = {z["id"]: z for z in DEFAULT_ZONES}

    async def start(self) -> None:
        self._running = True
        self.bus.subscribe(self._on_msg)
        asyncio.create_task(self._pose_loop())

    def stop(self) -> None:
        self._running = False

    async def _on_msg(self, msg: dict[str, Any]) -> None:
        t = msg.get("type")
        p = msg.get("payload") or {}
        if t == "person_track":
            self._person = (float(p.get("x", 0)), float(p.get("y", 0)))
            return
        if t != "command":
            return
        if random.random() < self.fail_rate:
            await self.bus.publish(
                "robot_status",
                {
                    "command_id": p.get("command_id"),
                    "state": "failed",
                    "detail": "mock fail_rate",
                    "distance_to_person_m": self._dist_person(),
                },
                source="mock",
            )
            return
        self._cmd = p
        action = p.get("action")
        args = p.get("args") or {}
        if action in ("lead_to", "goto"):
            zid = args.get("zone_id")
            z = self._zones.get(zid) if zid else None
            if z:
                self._target = centroid(z["polygon"])
            self.mode = "walking"
        elif action == "approach_person" and self._person:
            self._target = self._person
            self.mode = "walking"
        elif action == "stop":
            self._target = None
            self.mode = "standing"
        elif action == "yield":
            self._target = None
            self.mode = "standing"
            await self.bus.publish(
                "robot_status",
                {
                    "command_id": p.get("command_id"),
                    "state": "yielded",
                    "detail": "yield command",
                    "distance_to_person_m": self._dist_person(),
                },
                source="mock",
            )
            return
        await self.bus.publish(
            "robot_status",
            {
                "command_id": p.get("command_id"),
                "state": "accepted",
                "detail": action,
                "distance_to_person_m": self._dist_person(),
            },
            source="mock",
        )
        await self.bus.publish(
            "robot_status",
            {
                "command_id": p.get("command_id"),
                "state": "executing",
                "detail": action,
                "distance_to_person_m": self._dist_person(),
            },
            source="mock",
        )

    def _dist_person(self) -> float | None:
        if not self._person:
            return None
        return round(math.hypot(self.x - self._person[0], self.y - self._person[1]), 2)

    async def _pose_loop(self) -> None:
        dt = 1.0 / self.pose_hz
        while self._running:
            if self._target:
                tx, ty = self._target
                dx, dy = tx - self.x, ty - self.y
                dist = math.hypot(dx, dy)
                step = 0.25 * dt * 5  # ~0.25 m/s
                if dist < 0.15:
                    self.x, self.y = tx, ty
                    self._target = None
                    self.mode = "standing"
                    if self._cmd:
                        await self.bus.publish(
                            "robot_status",
                            {
                                "command_id": self._cmd.get("command_id"),
                                "state": "done",
                                "detail": None,
                                "distance_to_person_m": self._dist_person(),
                            },
                            source="mock",
                        )
                        self._cmd = None
                else:
                    self.x += dx / dist * step
                    self.y += dy / dist * step
                    self.theta = math.atan2(dy, dx)
                    # Yield if too close to person (safety envelope)
                    d = self._dist_person()
                    if d is not None and d < 1.2 and self._cmd:
                        await self.bus.publish(
                            "robot_status",
                            {
                                "command_id": self._cmd.get("command_id"),
                                "state": "yielded",
                                "detail": "proximity < 1.2m",
                                "distance_to_person_m": d,
                            },
                            source="mock",
                        )
                        self._target = None
                        self.mode = "standing"
                        self._cmd = None
            self.battery = max(5.0, self.battery - 0.001)
            await self.bus.publish(
                "pose",
                {
                    "x": round(self.x, 3),
                    "y": round(self.y, 3),
                    "theta": round(self.theta, 3),
                    "battery_pct": round(self.battery, 1),
                    "mode": self.mode,
                    "map_id": self.map_id,
                },
                source="mock",
            )
            await asyncio.sleep(dt)


async def _run_cli(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO)
    bus = get_bus(args.log)
    robot = MockRobot(bus, fail_rate=args.fail_rate)
    await robot.start()
    if args.hub:
        import httpx

        async def to_hub(msg: dict[str, Any]) -> None:
            if msg.get("source") != "mock":
                return
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{args.hub.rstrip('/')}/publish", json=msg, timeout=5.0)
            except Exception as e:
                logger.warning("hub publish: %s", e)

        bus.subscribe(to_hub)
        # Pull commands from hub WS
        import json

        import websockets

        uri = args.hub.replace("http://", "ws://").replace("https://", "wss://").rstrip("/") + "/ws"

        async def listen() -> None:
            async with websockets.connect(uri) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "command":
                        await bus.emit(msg)

        await listen()
    else:
        logger.info("mock_robot idle (pose loop). Ctrl+C to stop.")
        while True:
            await asyncio.sleep(3600)


def main() -> None:
    p = argparse.ArgumentParser(description="mock_robot — command → pose/status")
    p.add_argument("--fail-rate", type=float, default=0.0)
    p.add_argument("--hub", default="")
    p.add_argument("--log", default="bus_events.jsonl")
    args = p.parse_args()
    asyncio.run(_run_cli(args))


if __name__ == "__main__":
    main()

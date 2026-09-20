"""mock_patient — scripted person_track + zone_event scenarios."""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bus"))
sys.path.insert(0, str(ROOT / "orchestrator"))

from lantern_bus.core import Bus, get_bus  # noqa: E402
from lantern_orch.zones import DEFAULT_ZONES, zone_at  # noqa: E402

logger = logging.getLogger("lantern.mock_patient")

# Waypoints: (x, y, dwell_s) — exit_seeking walks bedroom → hallway pace → door
SCENARIOS: dict[str, list[tuple[float, float, float]]] = {
    "calm": [
        (0.5, 0.55, 2.0),
        (0.55, 0.5, 2.0),
        (0.45, 0.55, 2.0),
        (0.5, 0.55, 2.0),
    ],
    "pacing": [
        (0.5, 0.55, 0.8),
        (1.1, 0.55, 0.8),
        (0.9, 0.55, 0.8),
        (1.2, 0.55, 0.8),
        (1.0, 0.55, 0.8),
        (1.15, 0.55, 0.8),
        (1.05, 0.55, 0.8),
    ],
    "exit_seeking": [
        (0.5, 0.55, 1.0),
        (0.7, 0.55, 0.8),
        (1.1, 0.55, 0.8),
        (1.0, 0.55, 0.7),  # reverse — pacing cue
        (1.2, 0.55, 0.8),
        (1.4, 0.45, 0.7),
        (1.55, 0.35, 0.7),
        (1.7, 0.25, 2.5),  # linger at Don't-go so LEAD→ESCALATE (~5s) can fire
        (1.75, 0.22, 3.0),
        (1.72, 0.28, 2.0),
        (0.8, 0.5, 1.5),  # return after alert window
    ],
    "fall": [
        (0.5, 0.55, 1.0),
        (1.1, 0.55, 1.0),
        (1.2, 0.4, 0.5),
    ],
}


class MockPatient:
    def __init__(
        self,
        bus: Bus,
        scenario: str = "exit_seeking",
        *,
        rate_hz: float = 5.0,
        person_id: str = "p1",
        zones: list[dict[str, Any]] | None = None,
    ) -> None:
        self.bus = bus
        self.scenario = scenario
        self.rate_hz = rate_hz
        self.person_id = person_id
        self.zones = zones or list(DEFAULT_ZONES)
        self._waypoints = list(SCENARIOS.get(scenario, SCENARIOS["exit_seeking"]))
        self._last_zone: str | None = None
        self._running = False

    async def run(self, once: bool = True) -> None:
        self._running = True
        dt = 1.0 / self.rate_hz
        idx = 0
        while self._running and idx < len(self._waypoints):
            x0, y0, dwell = self._waypoints[idx]
            x1, y1, _ = self._waypoints[min(idx + 1, len(self._waypoints) - 1)]
            steps = max(1, int(dwell / dt))
            for s in range(steps):
                if not self._running:
                    return
                t = (s + 1) / steps
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t
                vx = (x1 - x0) / max(dwell, 0.1)
                vy = (y1 - y0) / max(dwell, 0.1)
                await self._emit_track(x, y, vx, vy)
                await asyncio.sleep(dt)
            idx += 1
            if not once and idx >= len(self._waypoints):
                idx = 0
        self._running = False

    def stop(self) -> None:
        self._running = False

    async def _emit_track(self, x: float, y: float, vx: float, vy: float) -> None:
        z = zone_at(x, y, self.zones)
        zone_id = z["id"] if z else "unknown"
        zone_class = z["class"] if z else "safe"
        heading = math.atan2(vy, vx) if (abs(vx) + abs(vy)) > 1e-6 else 0.0

        # Project ~3s ahead for projected_zone / ttz
        px, py = x + vx * 3.0, y + vy * 3.0
        pz = zone_at(px, py, self.zones)
        projected = pz["id"] if pz else zone_id
        ttz_s: float | None = None
        if pz and pz.get("class") == "exit" and zone_class != "exit":
            dist = math.hypot(px - x, py - y)
            speed = math.hypot(vx, vy) or 0.15
            ttz_s = max(0.0, dist / speed)
        elif zone_class == "exit":
            ttz_s = 0.0

        posture = "lying" if self.scenario == "fall" and zone_id == "hallway" else "standing"

        await self.bus.publish(
            "person_track",
            {
                "person_id": self.person_id,
                "tracker": "mock",
                "x": round(x, 3),
                "y": round(y, 3),
                "vx": round(vx, 3),
                "vy": round(vy, 3),
                "heading": round(heading, 3),
                "confidence": 0.9,
                "posture": posture,
                "zone": zone_id,
                "projected_zone": projected,
                "ttz_s": ttz_s,
                "lat": None,
                "lon": None,
            },
            source="mock",
        )

        if self._last_zone != zone_id:
            if self._last_zone is not None:
                prev = next((zz for zz in self.zones if zz["id"] == self._last_zone), None)
                if prev:
                    # only mark outside=True when leaving an exit zone to nowhere indoor
                    outside = prev.get("class") == "exit" and (
                        z is None or z.get("class") not in ("safe", "watch", "exit")
                    )
                    payload = {
                        "person_id": self.person_id,
                        "zone_id": prev["id"],
                        "zone_class": prev["class"],
                        "event": "exited",
                    }
                    if prev.get("class") == "exit":
                        payload["outside"] = outside
                    await self.bus.publish("zone_event", payload, source="mock")
            if z:
                event = "approaching" if zone_class == "exit" else "entered"
                await self.bus.publish(
                    "zone_event",
                    {
                        "person_id": self.person_id,
                        "zone_id": zone_id,
                        "zone_class": zone_class,
                        "event": event,
                    },
                    source="mock",
                )
                if zone_class == "exit" and event == "approaching":
                    await self.bus.publish(
                        "zone_event",
                        {
                            "person_id": self.person_id,
                            "zone_id": zone_id,
                            "zone_class": zone_class,
                            "event": "entered",
                        },
                        source="mock",
                    )
            self._last_zone = zone_id


async def _run_cli(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO)
    if args.hub:
        import httpx

        bus = get_bus()

        async def forward(msg: dict[str, Any]) -> None:
            async with httpx.AsyncClient() as client:
                await client.post(f"{args.hub.rstrip('/')}/publish", json=msg, timeout=5.0)

        bus.subscribe(forward)
        patient = MockPatient(bus, args.scenario, rate_hz=args.rate)
        await patient.run(once=True)
    else:
        bus = get_bus(args.log)
        patient = MockPatient(bus, args.scenario, rate_hz=args.rate)
        await patient.run(once=True)


def main() -> None:
    p = argparse.ArgumentParser(description="mock_patient — scripted tracks")
    p.add_argument(
        "--scenario",
        default="exit_seeking",
        choices=list(SCENARIOS.keys()),
    )
    p.add_argument("--rate", type=float, default=5.0, help="tracks per second")
    p.add_argument("--hub", default="", help="POST envelopes to bus hub URL")
    p.add_argument("--log", default="bus_events.jsonl")
    args = p.parse_args()
    asyncio.run(_run_cli(args))


if __name__ == "__main__":
    main()

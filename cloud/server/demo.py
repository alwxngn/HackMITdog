"""Scripted demo walk: safe zone → warning zone → danger zone → out of the house.

Emits the same envelopes the real spine does (person_track, zone_event, agent_state,
alert, say, pose, ...) straight into the cloud bus, so the portal, SMS/voice
escalation and morning report all react exactly as they would to the real thing.
It needs no orchestrator process. Positions come from the zones the caregiver painted.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from bus import bus
from store import store

logger = logging.getLogger("lantern.demo")

TICK_S = 0.25
INDOOR_SPEED = 0.45  # m/s inside the 2 x 2 m table-top home
OUTDOOR_SPEED = 6.0  # m/s — sped up so the outdoor leg takes ~25 s on stage
FOLLOW_INDOOR_M = 0.6
FOLLOW_OUTDOOR_M = 5.0
TRACK_TTL_S = 600.0
DEMO_HOME_LATLON = (42.3601, -71.0942)
M_PER_DEG_LAT = 111_320.0

# (forward, left) metres from the front door, forward = away from the house.
OUTSIDE_PATH: list[tuple[float, float]] = [
    (6, 3), (18, 4), (30, 10), (48, 12), (64, 24), (72, 44), (84, 64), (100, 78),
]

STEPS = [
    "Resting in the safe zone",
    "In the warning zone",
    "In the danger zone",
    "Left the house",
    "Live tracking",
]


def _in_poly(x: float, y: float, poly: list[list[float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _centroid(poly: list[list[float]]) -> tuple[float, float]:
    return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)


class DemoWalk:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._seq = 0
        self._hooks: dict[str, Callable[[dict[str, Any]], Awaitable[None]]] = {}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ---- public -------------------------------------------------------------

    async def start(self, reset: Callable[[], Awaitable[None]]) -> dict[str, Any]:
        if self.running:
            return {"ok": False, "error": "The demo is already running."}
        problem = self._prepare()
        if problem:
            return {"ok": False, "error": problem}
        await reset()
        self._task = asyncio.create_task(self._run())
        return {"ok": True}

    async def stop(self, reset: Callable[[], Awaitable[None]]) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await reset()

    # ---- setup --------------------------------------------------------------

    def _prepare(self) -> str | None:
        proj = store.projection
        zones = proj.get("zones") or []
        map_ready = proj.get("map_ready") or {}
        self.w = float(map_ready.get("width_m") or 2.0)
        self.h = float(map_ready.get("height_m") or 2.0)
        self.zones = [z for z in zones if z.get("polygon")]

        def first(cls: str) -> dict[str, Any] | None:
            return next((z for z in self.zones if z.get("class") == cls), None)

        exit_zone, watch_zone, safe_zone = first("exit"), first("watch"), first("safe")
        if not exit_zone:
            return "Paint a danger zone first (Settings → Edit home)."
        self.exit_c = _centroid(exit_zone["polygon"])
        self.watch_c = _centroid(watch_zone["polygon"]) if watch_zone else None
        self.start_c = _centroid(safe_zone["polygon"]) if safe_zone else (self.w * 0.25, self.h * 0.5)

        # Outward = from the middle of the home through the front door.
        ux, uy = self.exit_c[0] - self.w / 2, self.exit_c[1] - self.h / 2
        norm = math.hypot(ux, uy) or 1.0
        self.out = (ux / norm, uy / norm)

        cfg = proj.get("config") or {}
        patient = cfg.get("patient") or {}
        self.name = patient.get("preferred_name") or patient.get("name") or "Susan"
        home = patient.get("home") or {}
        if home.get("lat") is not None and home.get("lon") is not None:
            self.home_latlon = (float(home["lat"]), float(home["lon"]))
        else:
            self.home_latlon = DEMO_HOME_LATLON
        self.home_xy = (float(home.get("x") or 0.0), float(home.get("y") or 0.0))
        self.map_id = map_ready.get("map_id") or "demo_home_v1"

        self._hooks = {"exit": self._on_exit, "outside": self._on_outside}
        if self.watch_c:
            self._hooks["watch"] = self._on_watch
        self.pos = self.start_c
        self.dog = (max(0.05, self.start_c[0] - 0.4), self.start_c[1])
        self.last_dir = (self.out[0], self.out[1])
        self.zone_id = ""
        self.zone_cls = ""
        self.agent_state = "IDLE"
        self.alert_n = 0
        return None

    @staticmethod
    def _place(zone: dict[str, Any], generic: str) -> str:
        """A zone's own name, unless it is just the generic 'Warning'/'Danger' label."""
        label = zone.get("label") or ""
        return generic if label.lower() in {"", "warning", "danger", "watch", "don't go"} else label

    def _enabled(self) -> bool:
        """Danger zones are only enforced while Night Watch is on."""
        return bool((store.projection.get("config") or {}).get("night_watch_enabled", False))

    # ---- geometry -----------------------------------------------------------

    def _zone_at(self, x: float, y: float) -> dict[str, Any]:
        if not (0 <= x <= self.w and 0 <= y <= self.h):
            return {"id": "outside", "class": "outside", "label": "Outside"}
        order = {"exit": 0, "watch": 1, "safe": 2}
        hits = [z for z in self.zones if _in_poly(x, y, z["polygon"])]
        if not hits:
            return {"id": "home", "class": "safe", "label": "Home"}
        hits.sort(key=lambda z: order.get(z.get("class", "safe"), 9))
        return hits[0]

    def _latlon(self, x: float, y: float) -> tuple[float, float]:
        lat0, lon0 = self.home_latlon
        lat = lat0 + (y - self.home_xy[1]) / M_PER_DEG_LAT
        lon = lon0 + (x - self.home_xy[0]) / (M_PER_DEG_LAT * math.cos(math.radians(lat0)))
        return round(lat, 7), round(lon, 7)

    def _outside_point(self, f: float, l: float) -> tuple[float, float]:
        ux, uy = self.out
        return (
            self.exit_c[0] + f * ux - l * uy,
            self.exit_c[1] + f * uy + l * ux,
        )

    # ---- emit helpers -------------------------------------------------------

    async def _emit(self, type_: str, payload: dict[str, Any], source: str) -> None:
        self._seq += 1
        await bus.ingest(
            {"type": type_, "ts": time.time(), "source": source, "seq": self._seq, "payload": payload}
        )

    async def _status(self, index: int, running: bool = True) -> None:
        await self._emit(
            "demo_status",
            {"running": running, "step": STEPS[index] if running else None, "step_index": index + 1, "total": len(STEPS)},
            "cloud",
        )

    async def _state(self, state: str, reason: str, agitation: str) -> None:
        previous = self.agent_state
        self.agent_state = state
        await self._emit(
            "agent_state",
            {
                "state": state,
                "previous": previous,
                "agitation": agitation,
                "calm_mode": False,
                "reason": reason,
                "since_ts": time.time(),
            },
            "orchestrator",
        )

    async def _alert(
        self,
        level: int,
        headline: str,
        detail: str,
        *,
        requires_ack: bool,
        channels: list[str],
        context: str,
        live: bool = False,
    ) -> None:
        self.alert_n += 1
        await self._emit(
            "alert",
            {
                "alert_id": f"al_{uuid.uuid4().hex[:6]}",
                "level": level,
                "headline": headline,
                "detail": detail,
                "person_position": {"x": round(self.pos[0], 3), "y": round(self.pos[1], 3), "zone": self.zone_id},
                "requires_ack": requires_ack,
                "channels": channels,
                "context": context,
                "live_tracking": live,
            },
            "orchestrator",
        )

    # ---- movement -----------------------------------------------------------

    async def _track(self, x: float, y: float, vx: float, vy: float) -> None:
        self.pos = (x, y)
        zone = self._zone_at(x, y)
        cls = zone.get("class", "safe")
        speed = math.hypot(vx, vy)
        if speed > 1e-6:
            self.last_dir = (vx / speed, vy / speed)
        pz = self._zone_at(x + vx * 3.0, y + vy * 3.0)
        ttz: float | None = None
        if cls == "exit":
            ttz = 0.0
        elif pz.get("class") == "exit" and speed > 1e-6:
            ttz = round(math.hypot(vx * 3.0, vy * 3.0) / speed, 2)
        lat, lon = self._latlon(x, y)
        await self._emit(
            "person_track",
            {
                "person_id": "p1",
                "tracker": "mock",
                "x": round(x, 3),
                "y": round(y, 3),
                "vx": round(vx, 3),
                "vy": round(vy, 3),
                "heading": round(math.atan2(vy, vx), 3) if speed > 1e-6 else 0.0,
                "confidence": 0.9,
                "posture": "standing",
                "zone": zone["id"],
                "projected_zone": pz["id"],
                "ttz_s": ttz,
                "lat": lat,
                "lon": lon,
            },
            "mock",
        )
        await self._move_dog(x, y, cls)

        if zone["id"] != self.zone_id:
            prev_cls, self.zone_id, self.zone_cls = self.zone_cls, zone["id"], cls
            if prev_cls == "exit" and cls == "outside":
                await self._emit(
                    "zone_event",
                    {"person_id": "p1", "zone_id": "front_door", "zone_class": "exit", "event": "exited", "outside": True},
                    "mock",
                )
            if cls in ("watch", "exit"):
                base = {"person_id": "p1", "zone_id": zone["id"], "zone_class": cls, "zone_label": zone.get("label")}
                if cls == "exit":
                    await self._emit("zone_event", {**base, "event": "approaching"}, "mock")
                await self._emit("zone_event", {**base, "event": "entered"}, "mock")
            hook = self._hooks.pop(cls, None)
            if cls == "exit":
                self._hooks.pop("watch", None)  # walked straight to the door — skip the warning beat
            if hook:
                await hook(zone)

    async def _move_dog(self, px: float, py: float, cls: str) -> None:
        follow = FOLLOW_OUTDOOR_M if cls == "outside" else FOLLOW_INDOOR_M
        tx, ty = px - self.last_dir[0] * follow, py - self.last_dir[1] * follow
        dx, dy = tx - self.dog[0], ty - self.dog[1]
        self.dog = (self.dog[0] + dx * 0.5, self.dog[1] + dy * 0.5)
        lat, lon = self._latlon(*self.dog)
        await self._emit(
            "pose",
            {
                "x": round(self.dog[0], 3),
                "y": round(self.dog[1], 3),
                "theta": round(math.atan2(self.last_dir[1], self.last_dir[0]), 3),
                "battery_pct": 72,
                "mode": "walking",
                "map_id": self.map_id,
                "lat": lat,
                "lon": lon,
            },
            "mock",
        )

    async def _walk_to(self, tx: float, ty: float, speed: float) -> None:
        while True:
            x, y = self.pos
            dx, dy = tx - x, ty - y
            dist = math.hypot(dx, dy)
            step = speed * TICK_S
            if dist <= step:
                await self._track(tx, ty, 0.0, 0.0)
                return
            vx, vy = dx / dist * speed, dy / dist * speed
            await self._track(x + vx * TICK_S, y + vy * TICK_S, vx, vy)
            await asyncio.sleep(TICK_S)

    async def _hold(self, seconds: float, tick: float = TICK_S) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            x, y = self.pos
            await self._track(x + random.uniform(-0.01, 0.01), y + random.uniform(-0.01, 0.01), 0.0, 0.0)
            await asyncio.sleep(tick)

    # ---- story beats --------------------------------------------------------

    async def _on_watch(self, zone: dict[str, Any]) -> None:
        await self._status(1)
        if not self._enabled():
            return await self._hold(4.0)
        label = self._place(zone, "the warning zone")
        await self._state("ATTEND", f"{self.name} is in the warning zone", "unsettled")
        await self._alert(
            1,
            f"{self.name} is in the warning zone",
            f"Entered {label}. Lantern is keeping an eye on them.",
            requires_ack=False,
            channels=["push"],
            context="zone_watch",
        )
        await self._hold(4.0)

    async def _on_exit(self, zone: dict[str, Any]) -> None:
        await self._status(2)
        if not self._enabled():
            return await self._hold(8.0)
        label = self._place(zone, "the danger zone")
        await self._state("LEAD", f"{self.name} reached the danger zone", "agitated")
        await self._emit(
            "command",
            {"command_id": "demo_cmd_1", "action": "lead_to", "args": {"zone_id": "bedroom", "speed_max": 0.3, "standoff_m": 1.5}},
            "orchestrator",
        )
        # Lantern's speaker (speaker.py) reacts to this zone change and says "let's go home".
        await asyncio.sleep(1.0)
        await self._alert(
            2,
            f"{self.name} is in the danger zone",
            f"At {label}. Lantern asked them to go home, but they haven't turned around.",
            requires_ack=True,
            channels=["sms", "push"],
            context="night_breach",
        )
        await self._hold(8.0)

    async def _on_outside(self, zone: dict[str, Any]) -> None:
        await self._status(3)
        if not self._enabled():
            return
        await self._state("EMERGENCY", f"{self.name} left the house", "agitated")
        await self._alert(
            5,
            f"{self.name} has left the house",
            "Lantern is following at a distance. Open live tracking to see where they are.",
            requires_ack=True,
            channels=["sms", "push", "voice_call"],
            context="night_breach",
            live=True,
        )
        await self._state("FOLLOW", "Lantern is following at a distance", "agitated")
        await self._emit(
            "robot_status",
            {"command_id": "demo_cmd_2", "state": "executing", "detail": "following outside", "distance_to_person_m": FOLLOW_OUTDOOR_M},
            "robot",
        )

    # ---- script -------------------------------------------------------------

    async def _run(self) -> None:
        try:
            await self._state("IDLE", "night watch idle", "calm")
            await self._status(0)
            await self._track(*self.start_c, 0.0, 0.0)
            await self._hold(2.5)
            if self.watch_c:
                await self._walk_to(*self.watch_c, INDOOR_SPEED)
            await self._walk_to(*self.exit_c, INDOOR_SPEED)
            # Ignores Lantern and walks out, then follows a street-like path.
            await self._walk_to(*self._outside_point(2.0, 0.0), INDOOR_SPEED)
            for f, l in OUTSIDE_PATH:
                await self._walk_to(*self._outside_point(f, l), OUTDOOR_SPEED)
            await self._status(4)
            await self._hold(TRACK_TTL_S, tick=2.0)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("demo walk failed")
        finally:
            await self._emit("demo_status", {"running": False, "step": None}, "cloud")


demo = DemoWalk()

#!/usr/bin/env python3
"""Bridge Lantern's frozen bus messages to deterministic DimOS tools.

The bridge is intentionally motion-disabled by default.  Passing
``--motion-enabled`` means an operator has already verified the controller-level
speed cap, doorway exclusion, and yield reflex on the connected robot.

This process owns no policy decisions: E4 publishes ``command`` messages and
this adapter validates and executes the small real-robot subset.  Painted exit
zones are mirrored into DimOS without introducing a new bus message type.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import time
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

logger = logging.getLogger("lantern.robot.dimos_runtime_bridge")

Publisher = Callable[[dict[str, Any]], Awaitable[None]]


def _valid_polygon(value: object) -> list[list[float]] | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    points: list[list[float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        try:
            x, y = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        points.append([x, y])
    return points


def _zone_fingerprint(zone: dict[str, Any]) -> str:
    return json.dumps(
        {"class": zone["class"], "polygon": zone["polygon"]},
        sort_keys=True,
        separators=(",", ":"),
    )


def _decoded_json_values(value: object, *, depth: int = 0) -> list[object]:
    """Return nested JSON values, including JSON embedded in MCP text blocks."""
    if depth > 8:
        return []
    values = [value]
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.startswith(("{", "[")):
            try:
                values.extend(_decoded_json_values(json.loads(candidate), depth=depth + 1))
            except json.JSONDecodeError:
                pass
    elif isinstance(value, dict):
        for child in value.values():
            values.extend(_decoded_json_values(child, depth=depth + 1))
    elif isinstance(value, list):
        for child in value:
            values.extend(_decoded_json_values(child, depth=depth + 1))
    return values


def _raise_for_dimos_failure(output: str) -> None:
    """Reject explicit MCP/SkillResult failures even when the CLI exits zero."""
    for value in _decoded_json_values(output):
        if not isinstance(value, dict):
            continue
        failed = value.get("success") is False or value.get("isError") is True
        if not failed:
            continue
        detail = value.get("message") or value.get("error") or value.get("error_code")
        if isinstance(detail, dict):
            detail = detail.get("message") or json.dumps(detail, sort_keys=True)
        raise RuntimeError(str(detail or "DimOS tool reported failure")[-500:])


class DimosCli:
    """Small async wrapper around the already-supported ``dimos mcp call`` CLI."""

    def __init__(self, binary: str = "dimos") -> None:
        self.binary = binary

    async def call(
        self, tool: str, args: dict[str, Any], *, timeout_s: float = 120.0
    ) -> str:
        process = await asyncio.create_subprocess_exec(
            self.binary,
            "mcp",
            "call",
            tool,
            "--timeout",
            str(max(1, int(timeout_s))),
            "--json-args",
            json.dumps(args),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        detail = (stdout or stderr).decode(errors="replace").strip()
        if process.returncode:
            error = (stderr or stdout).decode(errors="replace").strip()
            raise RuntimeError(f"{tool} exited {process.returncode}: {error[-500:]}")
        _raise_for_dimos_failure(detail)
        return detail


class RuntimeBridge:
    """Synchronize zones and execute the real-robot subset of ``command``."""

    def __init__(
        self,
        *,
        dimos: DimosCli,
        publish: Publisher,
        motion_enabled: bool = False,
        interaction_speed_cap_mps: float = 0.3,
    ) -> None:
        self.dimos = dimos
        self.publish = publish
        self.motion_enabled = motion_enabled
        self.interaction_speed_cap_mps = min(0.3, max(0.0, interaction_speed_cap_mps))
        self.zones: dict[str, dict[str, Any]] = {}
        self._danger_fingerprints: dict[str, str] = {}
        self._seen_commands: set[str] = set()
        self._active_command_id: str | None = None
        self._cancelled_commands: set[str] = set()
        self._command_task: asyncio.Task[None] | None = None
        self._seq = 0
        self._lock = asyncio.Lock()

    async def handle(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        if msg_type == "config_update":
            await self._sync_zones((msg.get("payload") or {}).get("zones"))
            return
        if msg_type != "command":
            return

        payload = msg.get("payload") or {}
        command_id = str(payload.get("command_id") or "")
        if not command_id or command_id in self._seen_commands:
            return
        self._seen_commands.add(command_id)
        if len(self._seen_commands) > 2000:
            self._seen_commands = set(list(self._seen_commands)[-500:])

        action = str(payload.get("action") or "")
        args = payload.get("args") or {}
        if action == "stop" and args.get("operation") == "map_scan":
            # The dedicated mapping bridge owns this stop command.
            return
        if action in {"stop", "yield"}:
            await self._stop(command_id, yielded=action == "yield")
            return
        if action != "lead_to":
            await self._status(command_id, "failed", f"unsupported real-robot action: {action}")
            return

        async with self._lock:
            if self._active_command_id is not None:
                await self._status(command_id, "failed", f"robot busy with {self._active_command_id}")
                return
            self._active_command_id = command_id
            self._command_task = asyncio.create_task(self._lead_to(command_id, args))

    async def wait_idle(self) -> None:
        task = self._command_task
        if task is not None:
            await task

    async def _sync_zones(self, raw_zones: object) -> None:
        if raw_zones is None:
            return
        if not isinstance(raw_zones, list):
            logger.warning("ignoring config_update with non-list zones")
            return

        next_zones: dict[str, dict[str, Any]] = {}
        for raw in raw_zones:
            if not isinstance(raw, dict):
                continue
            zone_id = str(raw.get("id") or "").strip()
            zone_class = str(raw.get("class") or "").strip()
            polygon = _valid_polygon(raw.get("polygon"))
            if not zone_id or zone_class not in {"safe", "watch", "exit"} or polygon is None:
                logger.warning("ignoring invalid zone id=%r class=%r", zone_id, zone_class)
                continue
            next_zones[zone_id] = {**raw, "id": zone_id, "class": zone_class, "polygon": polygon}

        # Only exit/"Don't go" polygons are controller danger zones. Watch
        # zones remain policy inputs for E4 and do not forbid robot motion.
        next_dangers = {
            zone_id: _zone_fingerprint(zone)
            for zone_id, zone in next_zones.items()
            if zone["class"] == "exit"
        }

        removed = set(self._danger_fingerprints) - set(next_dangers)
        changed = {
            zone_id
            for zone_id, fingerprint in next_dangers.items()
            if self._danger_fingerprints.get(zone_id) != fingerprint
        }
        for zone_id in sorted(removed | (changed & set(self._danger_fingerprints))):
            await self.dimos.call("delete_danger_zone", {"name": zone_id}, timeout_s=30)
        for zone_id in sorted(changed):
            await self.dimos.call(
                "create_danger_zone",
                {"name": zone_id, "vertices": next_zones[zone_id]["polygon"]},
                timeout_s=30,
            )

        self.zones = next_zones
        self._danger_fingerprints = next_dangers
        logger.info("zone sync complete: %s zones, %s exit polygons", len(next_zones), len(next_dangers))

    async def _lead_to(self, command_id: str, args: dict[str, Any]) -> None:
        try:
            zone_id = str(args.get("zone_id") or "").strip()
            zone = self.zones.get(zone_id)
            if zone is None:
                await self._status(command_id, "failed", f"unknown destination zone: {zone_id}")
                return
            if zone.get("class") != "safe":
                await self._status(command_id, "failed", f"destination is not a safe zone: {zone_id}")
                return
            try:
                requested_speed = float(args.get("speed_max", self.interaction_speed_cap_mps))
            except (TypeError, ValueError):
                await self._status(command_id, "failed", "invalid speed_max")
                return
            if requested_speed <= 0 or requested_speed > self.interaction_speed_cap_mps:
                await self._status(
                    command_id,
                    "failed",
                    f"speed_max must be > 0 and <= {self.interaction_speed_cap_mps:.2f} m/s",
                )
                return
            if not self.motion_enabled:
                await self._status(
                    command_id,
                    "failed",
                    "motion disabled; verify controller speed, doorway, and yield safeguards first",
                )
                return

            await self._status(command_id, "accepted", f"lead_to {zone_id}")
            await self._status(command_id, "executing", f"navigating to saved location {zone_id}")
            await self.dimos.call("go_to_named_location", {"name": zone_id}, timeout_s=120)
            if command_id not in self._cancelled_commands:
                await self._status(command_id, "done", None)
        except Exception as exc:
            logger.exception("lead_to failed command=%s", command_id)
            if command_id not in self._cancelled_commands:
                await self._status(command_id, "failed", str(exc)[-300:])
        finally:
            async with self._lock:
                if self._active_command_id == command_id:
                    self._active_command_id = None

    async def _stop(self, stop_command_id: str, *, yielded: bool) -> None:
        active = self._active_command_id
        if active is not None:
            self._cancelled_commands.add(active)
        try:
            await self.dimos.call("stop_location_navigation", {}, timeout_s=30)
        except Exception as exc:
            await self._status(stop_command_id, "failed", f"could not stop navigation: {exc}")
            return
        if active is not None:
            await self._status(
                active,
                "yielded" if yielded else "failed",
                "yield command" if yielded else "navigation stopped by a higher-priority command",
            )
        await self._status(stop_command_id, "done", "navigation stopped")

    async def _status(self, command_id: str, state: str, detail: str | None) -> None:
        self._seq += 1
        await self.publish(
            {
                "type": "robot_status",
                "ts": time.time(),
                "source": "robot",
                "seq": self._seq,
                "payload": {
                    "command_id": command_id,
                    "state": state,
                    "detail": detail,
                    "distance_to_person_m": None,
                },
            }
        )


async def _post_json(url: str, msg: dict[str, Any]) -> None:
    body = json.dumps(msg).encode()

    def send() -> None:
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()

    await asyncio.to_thread(send)


async def run(args: argparse.Namespace) -> None:
    dimos = DimosCli(args.dimos_bin)

    async def publish(msg: dict[str, Any]) -> None:
        await _post_json(f"{args.bus_base.rstrip('/')}/publish", msg)

    bridge = RuntimeBridge(
        dimos=dimos,
        publish=publish,
        motion_enabled=args.motion_enabled,
        interaction_speed_cap_mps=args.interaction_speed_cap_mps,
    )
    while True:
        try:
            async with websockets.connect(args.bus_url) as ws:
                logger.info("connected to Lantern bus at %s", args.bus_url)
                async for raw in ws:
                    asyncio.create_task(bridge.handle(json.loads(raw)))
        except Exception as exc:
            logger.warning("bus connection failed: %s; retrying", exc)
            await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lantern bus → deterministic DimOS runtime")
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--bus-base", default="http://127.0.0.1:9000")
    parser.add_argument("--dimos-bin", default="dimos")
    parser.add_argument("--interaction-speed-cap-mps", type=float, default=0.3)
    parser.add_argument(
        "--motion-enabled",
        action="store_true",
        help="Enable physical movement only after controller safeguards are verified",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

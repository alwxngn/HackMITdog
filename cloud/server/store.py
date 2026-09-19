"""JSONL event store + in-memory projection for the portal."""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any

from schema import DEFAULT_CONFIG

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EVENTS_PATH = DATA_DIR / "events.jsonl"
TIMELINE_MAX = 500
TRAIL_MAX = 200


class EventStore:
    def __init__(self, path: Path = EVENTS_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.timeline: deque[dict[str, Any]] = deque(maxlen=TIMELINE_MAX)
        self.person_trail: deque[dict[str, float]] = deque(maxlen=TRAIL_MAX)
        self.projection: dict[str, Any] = self._empty_projection()

    def _empty_projection(self) -> dict[str, Any]:
        return {
            "agent_state": {
                "state": "IDLE",
                "previous": None,
                "agitation": "calm",
                "calm_mode": False,
                "reason": "boot",
                "since_ts": time.time(),
            },
            "pose": None,
            "person_track": None,
            "person_trail": [],
            "zones": list(DEFAULT_CONFIG["zones"]),
            "config": dict(DEFAULT_CONFIG),
            "open_alert": None,
            "live_tracking": False,
            "speech_state": "idle",
            "last_transcript": None,
            "robot_status": None,
            "checkin_queue": [],
            "map_ready": None,
            "map_scan_pending": None,
        }

    def append(self, msg: dict[str, Any]) -> None:
        line = json.dumps(msg, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        self._apply(msg)
        if self._is_timeline_worthy(msg):
            self.timeline.appendleft(msg)

    def _is_timeline_worthy(self, msg: dict[str, Any]) -> bool:
        t = msg.get("type")
        if t in {
            "agent_state",
            "alert",
            "zone_event",
            "caregiver_ack",
            "transcript",
            "say",
            "checkin",
            "config_update",
            "map_scan_request",
            "map_ready",
        }:
            return True
        if t == "robot_status" and (msg.get("payload") or {}).get("state") == "yielded":
            return True
        return False

    def _apply(self, msg: dict[str, Any]) -> None:
        t = msg.get("type")
        p = msg.get("payload") or {}
        if t == "agent_state":
            self.projection["agent_state"] = p
        elif t == "pose":
            self.projection["pose"] = p
        elif t == "person_track":
            self.projection["person_track"] = p
            if "x" in p and "y" in p:
                self.person_trail.append({"x": p["x"], "y": p["y"], "ts": msg.get("ts", 0)})
                self.projection["person_trail"] = list(self.person_trail)
        elif t == "alert":
            self.projection["open_alert"] = {**p, "ts": msg.get("ts")}
            if p.get("live_tracking"):
                self.projection["live_tracking"] = True
        elif t == "caregiver_ack":
            if (
                self.projection["open_alert"]
                and self.projection["open_alert"].get("alert_id") == p.get("alert_id")
            ):
                self.projection["open_alert"] = None
            self.projection["live_tracking"] = False
        elif t == "config_update":
            cfg = self.projection["config"]
            for key, val in p.items():
                cfg[key] = val
            if "zones" in p:
                self.projection["zones"] = p["zones"]
        elif t == "speech_state":
            self.projection["speech_state"] = p.get("state", "idle")
        elif t == "transcript" and p.get("is_final"):
            self.projection["last_transcript"] = p
        elif t == "robot_status":
            self.projection["robot_status"] = p
        elif t == "checkin":
            self.projection["checkin_queue"].append(p)
        elif t == "map_scan_request":
            self.projection["map_scan_pending"] = p
        elif t == "map_ready":
            self.projection["map_ready"] = p
            self.projection["map_scan_pending"] = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "ts": time.time(),
            "source": "cloud",
            "seq": 0,
            "payload": {
                **self.projection,
                "timeline": list(self.timeline),
            },
        }

    def reset(self) -> None:
        # Truncate JSONL for a clean demo loop; keep a backup stamp.
        if self.path.exists():
            bak = self.path.with_suffix(f".{int(time.time())}.bak.jsonl")
            self.path.rename(bak)
        self.path.touch()
        self.timeline.clear()
        self.person_trail.clear()
        self.projection = self._empty_projection()

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out


store = EventStore()

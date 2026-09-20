"""Pydantic mirrors of docs/04-interfaces.md. Local until E4 ships /bus."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Source = Literal["robot", "voice", "orchestrator", "cloud", "mock"]


class Envelope(BaseModel):
    type: str
    ts: float
    source: Source
    seq: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Robot ---

PoseMode = Literal["idle", "standing", "walking", "sitting", "lying"]
Posture = Literal["standing", "sitting", "lying", "unknown"]
TrackerKind = Literal["overhead_cam", "lidar_cluster", "onboard_fusion", "gps", "mock"]
ZoneClass = Literal["safe", "watch", "exit"]
ZoneEventKind = Literal["entered", "exited", "approaching"]
RobotStatusState = Literal["accepted", "executing", "done", "failed", "yielded"]

# --- Orchestrator ---

AgentStateName = Literal[
    "IDLE",
    "ATTEND",
    "LEAD",
    "ESCALATE",
    "EMERGENCY",
    "WALK",
    "FOLLOW",
    "CONFIRM_HOME",
    "GUIDE_HOME",
]
Agitation = Literal["calm", "unsettled", "agitated"]
AlertContext = Literal["night_breach", "day_walk_separation"]

# --- Cloud outbound ---

AckAction = Literal["im_coming", "handled", "false_alarm", "call_help"]


class CaregiverAckPayload(BaseModel):
    alert_id: str
    by: str = "jenny"
    action: AckAction = "im_coming"


class CheckinPayload(BaseModel):
    checkin_id: str
    from_name: str
    text: str


class Position(BaseModel):
    x: float
    y: float
    zone: str | None = None


DEFAULT_MAP_READY: dict[str, Any] = {
    "request_id": "ms_default",
    "map_id": "demo_home_v1",
    "origin": {"x": 0.0, "y": 0.0},
    "width_m": 2.0,
    "height_m": 2.0,
    "outline": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]],
    "rooms": [
        {
            "id": "bedroom",
            "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.2], [0.0, 1.2]],
        },
        {
            "id": "hallway",
            "polygon": [[1.0, 0.3], [1.8, 0.3], [1.8, 1.0], [1.0, 1.0]],
        },
        {
            "id": "front_door",
            "polygon": [[1.6, 0.0], [2.0, 0.0], [2.0, 0.5], [1.6, 0.5]],
        },
    ],
}


DEFAULT_CONFIG: dict[str, Any] = {
    "night_watch_enabled": True,
    "zones": [
        {
            "id": "bedroom",
            "class": "safe",
            "label": "Bedroom",
            "kind": "door",
            "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        },
        {
            "id": "hallway",
            "class": "watch",
            "label": "Hallway",
            "kind": "door",
            "polygon": [[1.0, 0.3], [1.8, 0.3], [1.8, 0.9], [1.0, 0.9]],
        },
        {
            "id": "front_door",
            "class": "exit",
            "label": "Danger",
            "kind": "door",
            "polygon": [[1.6, 0.0], [2.0, 0.0], [2.0, 0.5], [1.6, 0.5]],
        },
    ],
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
        "name": "Arthur",
        "preferred_name": "Art",
        "calming_topics": ["fishing at Moosehead", "his dog Bella"],
        "avoid_topics": ["his wife's death"],
        "music_url": "/media/arthur_playlist.mp3",
        "schedule": {
            "wake_time": "07:30",
            "meals": ["08:00", "12:30", "18:00"],
            "walk_window": ["15:00", "16:30"],
            "notes": "likes the porch after lunch",
        },
        # Origin = SW corner of taped area (docs/16-e3-portal.md)
        "home": {"x": 0.0, "y": 0.0, "lat": None, "lon": None},
        "route_id": None,
    },
}

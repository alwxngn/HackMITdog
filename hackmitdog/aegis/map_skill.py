"""Callable Go2 room mapping and browser artifact export.

DimOS already supplies the hard parts: ``WavefrontFrontierExplorer`` drives
the robot to unknown-space frontiers and ``VoxelGridMapper`` publishes a
world-frame ``PointCloud2`` on ``global_map``.  This skill composes those
existing modules and only owns the bounded session and file/export contract.

The exported ASCII PLY is intentionally dependency-free on the web side:
Three.js, Babylon.js, and most desktop viewers can load it directly.  The
JSON sidecar contains the frozen Lantern ``map_ready`` payload plus artifact
metadata.  No new bus message type is introduced.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from dimos.agents.annotation import skill
from dimos.core.module import Module
from dimos.core.stream import In
from dimos.msgs.sensor_msgs.PointCloud2 import PointCloud2
from dimos.navigation.frontier_exploration.wavefront_frontier_goal_selector import (
    WavefrontFrontierExplorer,
)
from dimos.agents.skill_result import SkillResult

from hackmitdog.aegis.skill_errors import AegisError


_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_name(value: str) -> str:
    cleaned = _SAFE_NAME.sub("_", value.strip()).strip("._")
    return cleaned or "room"


def _ply(points: Any, colors: Any | None, max_points: int) -> tuple[str, int]:
    """Serialize a finite, optionally downsampled Nx3 point array as ASCII PLY."""
    import numpy as np

    xyz = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    finite = np.isfinite(xyz).all(axis=1)
    xyz = xyz[finite]
    rgb = None
    if colors is not None:
        candidate = np.asarray(colors, dtype=np.float32).reshape(-1, 3)
        candidate = candidate[finite]
        rgb = np.clip(candidate * 255.0, 0, 255).astype(np.uint8)
    if len(xyz) > max_points:
        stride = int(math.ceil(len(xyz) / max_points))
        xyz = xyz[::stride]
        if rgb is not None:
            rgb = rgb[::stride]

    lines = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(xyz)}",
        "property float x",
        "property float y",
        "property float z",
    ]
    if rgb is not None:
        lines += ["property uchar red", "property uchar green", "property uchar blue"]
    lines += ["end_header"]
    if rgb is None:
        lines.extend(f"{x:.5f} {y:.5f} {z:.5f}" for x, y, z in xyz)
    else:
        lines.extend(
            f"{x:.5f} {y:.5f} {z:.5f} {r} {g} {b}"
            for (x, y, z), (r, g, b) in zip(xyz, rgb, strict=True)
        )
    return "\n".join(lines) + "\n", len(xyz)


def _map_payload(request_id: str, map_id: str, room_id: str, points: Any) -> dict[str, Any]:
    import numpy as np

    xyz = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    xyz = xyz[np.isfinite(xyz).all(axis=1)]
    if len(xyz) == 0:
        raise ValueError("the global map contains no finite points")
    low = xyz.min(axis=0)
    high = xyz.max(axis=0)
    # The portal/map contract is metres in a SW-origin frame. z is retained in
    # the PLY, while the 2-D envelope uses x/y only.
    outline = [
        [round(float(low[0]), 3), round(float(low[1]), 3)],
        [round(float(high[0]), 3), round(float(low[1]), 3)],
        [round(float(high[0]), 3), round(float(high[1]), 3)],
        [round(float(low[0]), 3), round(float(high[1]), 3)],
    ]
    return {
        "request_id": request_id,
        "map_id": map_id,
        "origin": {"x": float(low[0]), "y": float(low[1])},
        "width_m": round(float(high[0] - low[0]), 3),
        "height_m": round(float(high[1] - low[1]), 3),
        "outline": outline,
        "rooms": [{"id": room_id, "polygon": outline}],
    }


class MapRoomSkills(Module):
    """Map a bounded room with Go2 frontier exploration and export a 3-D file."""

    global_map: In[PointCloud2]
    _explorer: WavefrontFrontierExplorer

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._latest_map: PointCloud2 | None = None

    async def handle_global_map(self, msg: PointCloud2) -> None:
        self._latest_map = msg

    @skill
    def map_room(
        self,
        room_id: str,
        duration_s: float = 300.0,
        output_dir: str | None = None,
        request_id: str | None = None,
        map_id: str | None = None,
        max_points: int = 200_000,
        cloud_ingest_url: str | None = None,
        artifact_url: str | None = None,
    ) -> SkillResult[AegisError]:
        """Explore a room, export a browser-loadable 3-D PLY, and publish map_ready.

        The robot moves autonomously using DimOS frontier exploration until the
        room is covered or ``duration_s`` elapses. The call is bounded and stops
        exploration in all exit paths. ``cloud_ingest_url`` may be the existing
        Lantern ``POST /api/ingest`` endpoint; ``artifact_url`` is an optional
        URL served by the web app and is included as additive payload metadata.
        The PLY itself must be made reachable by that web app separately.
        """
        room_id = room_id.strip()
        if not room_id:
            return SkillResult.fail("INVALID_INPUT", "room_id must not be empty.")
        if duration_s <= 0 or max_points <= 0:
            return SkillResult.fail("INVALID_INPUT", "duration_s and max_points must be positive.")

        request_id = request_id or f"map_{uuid.uuid4().hex[:12]}"
        map_id = map_id or f"{_safe_name(room_id)}_{int(time.time())}"
        out = Path(output_dir or os.getenv("LANTERN_MAP_ARTIFACT_DIR", "artifacts/maps"))
        started = time.monotonic()
        started_exploration = False

        try:
            self._latest_map = None
            result = self._explorer.begin_exploration()
            started_exploration = "Started" in result
            if not started_exploration:
                return SkillResult.fail("ALREADY_RUNNING", result)

            deadline = started + duration_s
            while time.monotonic() < deadline and self._explorer.is_exploration_active():
                time.sleep(0.25)
        except Exception as exc:
            return SkillResult.fail("EXECUTION_FAILED", f"Mapping failed: {exc}")
        finally:
            if started_exploration:
                try:
                    self._explorer.end_exploration()
                except Exception:
                    # The explorer's own stop path is best-effort; never leave
                    # the robot exploring just because export failed.
                    pass

        cloud = self._latest_map
        if cloud is None:
            return SkillResult.fail("EXECUTION_FAILED", "No global_map PointCloud2 was received.")
        try:
            points, colors = cloud.as_numpy()
            payload = _map_payload(request_id, map_id, room_id, points)
            ply_text, point_count = _ply(points, colors, max_points)
            out.mkdir(parents=True, exist_ok=True)
            stem = _safe_name(map_id)
            ply_path = out / f"{stem}.ply"
            json_path = out / f"{stem}.json"
            ply_path.write_text(ply_text, encoding="utf-8")
            metadata = {
                "type": "lantern_3d_map",
                "format": "ply",
                "artifact_path": str(ply_path.resolve()),
                "artifact_url": artifact_url,
                "point_count": point_count,
                "frame_id": getattr(cloud, "frame_id", "world"),
                "map_ready": payload,
            }
            json_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            if artifact_url:
                payload["artifact_url"] = artifact_url
            if cloud_ingest_url:
                envelope = {
                    "type": "map_ready",
                    "ts": time.time(),
                    "source": "robot",
                    "seq": 0,
                    "payload": payload,
                }
                request = urllib.request.Request(
                    cloud_ingest_url,
                    data=json.dumps(envelope).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    if response.status >= 300:
                        raise RuntimeError(f"cloud ingest returned HTTP {response.status}")
            return SkillResult.ok(
                "Room mapped and 3-D artifact exported.",
                map_ready=payload,
                ply_path=str(ply_path.resolve()),
                metadata_path=str(json_path.resolve()),
                point_count=point_count,
                elapsed_s=round(time.monotonic() - started, 1),
            )
        except Exception as exc:
            return SkillResult.fail("EXECUTION_FAILED", f"Could not export map: {exc}")

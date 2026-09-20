"""Skills 9, 10, 11 — danger-zone CRUD, monitoring, and safe-intercept.

DimOS has no polygon/geofence primitive anywhere in the package (confirmed in
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §6, §8: no ``shapely`` dependency, no
``Zone``/``Geofence``/``Polygon`` class). Everything geometric in this module
is therefore genuinely new, standard-library-only code, not a reuse of a
DimOS API that happens to be missing here:

- Zones are named 2D polygons (world/map frame) persisted to a local JSON
  file next to this module (``danger_zones.json``) — this repo owns this
  data; DimOS doesn't, so it isn't stored through any DimOS mechanism.
- Point-in-polygon (ray casting) and point-to-polygon distance (min over
  point-to-segment distance across all edges) are both implemented here from
  scratch; see the two module-level functions below for the exact algorithm
  and edge-case conventions.

Navigation reuses the same mechanism as ``locations.py``/``navigation_skills.py``
(``NavigationInterfaceSpec.set_goal`` + poll-until-arrival), duplicated here
rather than cross-imported, matching this batch's established convention of
small independent ``Module``s (see ``navigation_skills.py``'s own docstring
for the same reasoning).

**Safety note (Skill 11, `navigate_to_safe_intercept_position`)**: this skill
positions the robot near a zone while keeping clearance from it. It never
computes or issues a goal inside the zone, and it never targets a person's
position, path, or heading — only the fixed zone geometry. It cannot and does
not implement blocking or contact of any kind; see the skill's own docstring.

No DimOS code is modified.
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dimos.agents.annotation import skill
from dimos.agents.capabilities import CAP_MOVEMENT
from dimos.agents.skill_result import SkillResult
from dimos.core.module import Module
from dimos.core.stream import In
from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
from dimos.msgs.geometry_msgs.Quaternion import Quaternion
from dimos.msgs.geometry_msgs.Vector3 import make_vector3
from dimos.msgs.tf2_msgs.TFMessage import TFMessage
from dimos.navigation.base import NavigationState
from dimos.navigation.navigation_spec import NavigationInterfaceSpec
from dimos.utils.logging_config import setup_logger

from hackmitdog.aegis.skill_errors import AegisError

logger = setup_logger()

# Persistence lives next to this file so it's deterministic regardless of the
# process's current working directory (a running blueprint's cwd is not
# something a skill author controls).
_ZONES_FILE = Path(__file__).parent / "danger_zones.json"

_GOAL_POLL_INTERVAL_S = 0.1
_GOAL_SETTLE_S = 1.5
_DEFAULT_INTERCEPT_TIMEOUT_S = 60.0

# monitor_danger_zones tuning: how often the background loop polls, and how
# long to wait before re-notifying for the *same* zone so a robot sitting
# near a boundary doesn't spam a notification on every poll tick.
_DEFAULT_POLL_INTERVAL_S = 1.0
_DEFAULT_APPROACH_THRESHOLD_M = 1.0
_RENOTIFY_COOLDOWN_S = 10.0
# Only re-notify inside the cooldown window if distance has closed by at
# least this much (meters) -- e.g. the robot is visibly still approaching.
_RENOTIFY_MIN_DELTA_M = 0.1


# ----------------------------------------------------------------------
# Geometry (standard library only -- see module docstring)
# ----------------------------------------------------------------------


def point_in_polygon(x: float, y: float, vertices: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test.

    Casts a horizontal ray from ``(x, y)`` toward +infinity in x and counts
    how many polygon edges it crosses; an odd count means the point is
    inside. This is the standard even-odd algorithm.

    Convention for points exactly on an edge or vertex: due to the strict
    inequality in the crossing test below, on-boundary points are treated
    inconsistently by raw ray casting (a well-known property of this
    algorithm) -- they may report inside or outside depending on which edge
    they sit on. This module does not special-case boundary points as a
    third state; callers that need an exact "on the line" answer should
    treat a `distance_to_danger_zone` result of ``0.0`` as authoritative
    instead of relying on this function's boundary behavior.
    """
    inside = False
    n = len(vertices)
    x1, y1 = vertices[-1]
    for i in range(n):
        x2, y2 = vertices[i]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def _point_to_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """Shortest distance from point (px, py) to segment [(ax, ay), (bx, by)].

    Projects the point onto the (clamped) segment parameter t in [0, 1] and
    returns the Euclidean distance to that closest point.
    """
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-12:
        # Degenerate segment (a == b): distance to the single point.
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return math.hypot(px - closest_x, py - closest_y)


def distance_to_polygon(x: float, y: float, vertices: list[tuple[float, float]]) -> float:
    """Distance in meters from (x, y) to the polygon's boundary.

    Convention: 0.0 if the point is inside (or exactly on the boundary) --
    this module does not report a signed "how deep inside" distance, since
    none of the three skills need it and a plain non-negative distance is
    the least surprising contract for an LLM caller. For a point outside,
    the result is the minimum point-to-segment distance over every edge.
    """
    if point_in_polygon(x, y, vertices):
        return 0.0
    n = len(vertices)
    best = math.inf
    for i in range(n):
        ax, ay = vertices[i]
        bx, by = vertices[(i + 1) % n]
        d = _point_to_segment_distance(x, y, ax, ay, bx, by)
        best = min(best, d)
    return best


def _nearest_boundary_point(
    x: float, y: float, vertices: list[tuple[float, float]]
) -> tuple[float, float, float]:
    """Nearest point on the polygon boundary to (x, y), plus the distance.

    Returns (nearest_x, nearest_y, distance). Used by the safe-intercept
    geometry below; distance is always >= 0 regardless of inside/outside
    (unlike `distance_to_polygon`, which collapses inside to 0) because the
    intercept computation needs the true nearest-edge point even when the
    robot happens to be starting from inside a zone.
    """
    n = len(vertices)
    best_d = math.inf
    best_point = vertices[0]
    for i in range(n):
        ax, ay = vertices[i]
        bx, by = vertices[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-12:
            t = 0.0
        else:
            t = ((x - ax) * dx + (y - ay) * dy) / seg_len_sq
            t = max(0.0, min(1.0, t))
        cx, cy = ax + t * dx, ay + t * dy
        d = math.hypot(x - cx, y - cy)
        if d < best_d:
            best_d = d
            best_point = (cx, cy)
    return best_point[0], best_point[1], best_d


# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------


@dataclass
class DangerZone:
    name: str
    vertices: list[list[float]] = field(default_factory=list)

    def vertex_tuples(self) -> list[tuple[float, float]]:
        return [(float(v[0]), float(v[1])) for v in self.vertices]


def _load_zones(path: Path) -> dict[str, DangerZone]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load danger zones file", path=str(path))
        return {}
    zones: dict[str, DangerZone] = {}
    for entry in raw.get("zones", []):
        try:
            zone = DangerZone(name=entry["name"], vertices=entry["vertices"])
            zones[zone.name.lower()] = zone
        except (KeyError, TypeError):
            logger.warning("Skipping malformed zone entry", entry=entry)
    return zones


def _save_zones(path: Path, zones: dict[str, DangerZone]) -> None:
    payload = {"zones": [asdict(z) for z in zones.values()]}
    path.write_text(json.dumps(payload, indent=2))


# ----------------------------------------------------------------------
# Module
# ----------------------------------------------------------------------


class DangerZoneSkills(Module):
    """Danger-zone CRUD, queries, background monitoring, and safe-intercept.

    Zones are simple named 2D polygons in the world/map frame, persisted
    locally to ``danger_zones.json`` next to this file (see module
    docstring). No DimOS zone/geofence API exists to reuse; the CRUD and
    geometry here are this module's own.
    """

    _navigation: NavigationInterfaceSpec

    tf: In[TFMessage]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._zones: dict[str, DangerZone] = _load_zones(_ZONES_FILE)
        self._monitor_stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        # zone_name -> (last_notified_monotonic_time, last_notified_distance)
        self._last_notified: dict[str, tuple[float, float]] = {}

    # ------------------------------------------------------------------
    # Skill 9: CRUD
    # ------------------------------------------------------------------

    @skill
    def create_danger_zone(
        self, name: str, vertices: list[list[float]]
    ) -> SkillResult[AegisError]:
        """Define a named danger zone as a 2D polygon in world/map coordinates.

        Use this to mark an area the robot should treat as off-limits or
        report proximity to -- e.g. a pool edge, a stairwell, a construction
        area. `vertices` should be ordered around the polygon (clockwise or
        counter-clockwise, either works); they do not need to be closed
        (do not repeat the first point at the end).

        Args:
            name: Short zone name, e.g. "pool edge". Case-insensitive for
                lookups. Creating a zone with an existing name overwrites it.
            vertices: At least 3 `[x, y]` pairs in world/map coordinates
                (meters), in order around the polygon boundary.

        Example:
            create_danger_zone("pool edge", [[1.0, 1.0], [4.0, 1.0], [4.0, 3.0], [1.0, 3.0]])
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")
        if not isinstance(vertices, list) or len(vertices) < 3:
            return SkillResult.fail("INVALID_INPUT", "vertices must have at least 3 points.")
        for v in vertices:
            if (
                not isinstance(v, list | tuple)
                or len(v) != 2
                or not all(isinstance(c, int | float) for c in v)
            ):
                return SkillResult.fail(
                    "INVALID_INPUT", f"Each vertex must be a 2-element numeric pair, got {v!r}."
                )

        try:
            zone = DangerZone(name=name, vertices=[[float(v[0]), float(v[1])] for v in vertices])
            self._zones[name.lower()] = zone
            _save_zones(_ZONES_FILE, self._zones)
        except Exception as exc:
            logger.exception("create_danger_zone failed", name=name)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not save zone '{name}': {exc}")

        return SkillResult.ok(
            f"Created danger zone '{name}' with {len(vertices)} vertices.",
            name=name,
            vertex_count=len(vertices),
        )

    @skill
    def list_danger_zones(self) -> SkillResult[AegisError]:
        """List every configured danger zone, with its vertices.

        Use this to see what zones already exist before creating a new one
        or calling `is_in_danger_zone`/`distance_to_danger_zone`.
        """
        zones = [{"name": z.name, "vertices": z.vertices} for z in self._zones.values()]
        return SkillResult.ok(
            f"{len(zones)} danger zone(s)." if zones else "No danger zones configured yet.",
            zones=zones,
        )

    @skill
    def delete_danger_zone(self, name: str) -> SkillResult[AegisError]:
        """Delete a named danger zone.

        Args:
            name: The zone name to delete, as previously created.
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")

        key = name.lower()
        if key not in self._zones:
            return SkillResult.fail("ZONE_NOT_FOUND", f"No danger zone called '{name}'.")

        try:
            del self._zones[key]
            _save_zones(_ZONES_FILE, self._zones)
        except Exception as exc:
            logger.exception("delete_danger_zone failed", name=name)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not delete zone '{name}': {exc}")

        return SkillResult.ok(f"Deleted danger zone '{name}'.", name=name)

    # ------------------------------------------------------------------
    # Skill 9 (continued): queries
    # ------------------------------------------------------------------

    @skill
    def is_in_danger_zone(
        self, x: float | None = None, y: float | None = None
    ) -> SkillResult[AegisError]:
        """Check whether a point falls inside any configured danger zone.

        If `x`/`y` are omitted, checks the robot's own current position
        instead of an arbitrary point.

        Args:
            x: World-frame x coordinate in meters. Omit to use the robot's
                current position.
            y: World-frame y coordinate in meters. Omit to use the robot's
                current position.

        Example:
            is_in_danger_zone()                 # check the robot's own position
            is_in_danger_zone(x=2.0, y=1.5)      # check an arbitrary point
        """
        point = self._resolve_point(x, y)
        if isinstance(point, SkillResult):
            return point
        px, py = point

        try:
            matches = [
                z.name for z in self._zones.values() if point_in_polygon(px, py, z.vertex_tuples())
            ]
        except Exception as exc:
            logger.exception("is_in_danger_zone failed", x=px, y=py)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not evaluate zones: {exc}")

        message = (
            f"Point ({px:.2f}, {py:.2f}) is inside: {', '.join(matches)}."
            if matches
            else f"Point ({px:.2f}, {py:.2f}) is not inside any danger zone."
        )
        return SkillResult.ok(message, x=px, y=py, zones=matches)

    @skill
    def distance_to_danger_zone(
        self, name: str, x: float | None = None, y: float | None = None
    ) -> SkillResult[AegisError]:
        """Distance in meters from a point to a named danger zone's boundary.

        If `x`/`y` are omitted, measures from the robot's own current
        position. Returns 0.0 if the point is already inside the zone.

        Args:
            name: A zone name previously created with `create_danger_zone`.
            x: World-frame x coordinate in meters. Omit to use the robot's
                current position.
            y: World-frame y coordinate in meters. Omit to use the robot's
                current position.

        Example:
            distance_to_danger_zone("pool edge")
            distance_to_danger_zone("pool edge", x=0.0, y=0.0)
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")
        zone = self._zones.get(name.lower())
        if zone is None:
            return SkillResult.fail("ZONE_NOT_FOUND", f"No danger zone called '{name}'.")

        point = self._resolve_point(x, y)
        if isinstance(point, SkillResult):
            return point
        px, py = point

        try:
            distance = distance_to_polygon(px, py, zone.vertex_tuples())
        except Exception as exc:
            logger.exception("distance_to_danger_zone failed", name=name)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not compute distance: {exc}")

        return SkillResult.ok(
            f"Distance from ({px:.2f}, {py:.2f}) to '{name}': {distance:.2f} m.",
            name=name,
            x=px,
            y=py,
            distance_m=round(distance, 3),
        )

    def _resolve_point(
        self, x: float | None, y: float | None
    ) -> tuple[float, float] | SkillResult[AegisError]:
        """Resolve (x, y), defaulting to the robot's own current position."""
        if x is not None and y is not None:
            return float(x), float(y)
        if (x is None) != (y is None):
            return SkillResult.fail("INVALID_INPUT", "x and y must both be given, or both omitted.")

        tf = self.tfbuffer.get("world", "base_link")
        if tf is None:
            return SkillResult.fail(
                "EXECUTION_FAILED", "Could not get the robot's current position."
            )
        position = tf.to_pose().position
        return float(position.x), float(position.y)

    # ------------------------------------------------------------------
    # Skill 10: monitor_danger_zones (background)
    # ------------------------------------------------------------------

    @skill(lifecycle="background")
    def start_monitoring_danger_zones(
        self,
        approach_threshold_m: float = _DEFAULT_APPROACH_THRESHOLD_M,
        poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    ) -> SkillResult[AegisError]:
        """Watch configured danger zones and report when something gets close.

        Limitation, stated plainly: this monitors the ROBOT's own position
        against configured zones. DimOS has no standing "current tracked
        person position" stream in this version to monitor a person's
        position directly -- only transient, per-call detections exist (see
        `DIMOS_SKILL_IMPLEMENTATION_PLAN.md` §3, §6). If/when a person-
        position source exists (e.g. a continuous person-tracking skill),
        this monitor would extend to accept that as an alternative subject.

        Does not move the robot and does not hold the movement capability,
        so navigation skills can run concurrently with monitoring -- this
        skill only observes and reports.

        Polls every `poll_interval_s` seconds. When the robot's distance to
        any zone drops below `approach_threshold_m` (including being inside
        a zone, distance 0), pushes a structured JSON progress update with
        fields `zone`, `position` (the robot's own x/y), `timestamp`, and
        `distance`. Repeat notifications for the same zone are rate-limited
        (at most once per 10s, unless distance has closed by at least 0.1m
        since the last notification) so sitting near a boundary doesn't spam
        an update every poll tick.

        Call `stop_monitoring_danger_zones` to stop.

        Args:
            approach_threshold_m: Notify when distance to a zone drops below
                this many meters.
            poll_interval_s: How often to check, in seconds.

        Example:
            start_monitoring_danger_zones()
            start_monitoring_danger_zones(approach_threshold_m=2.0, poll_interval_s=0.5)
        """
        self.start_tool("monitor_danger_zones")

        if approach_threshold_m <= 0:
            self.stop_tool("monitor_danger_zones")
            return SkillResult.fail("INVALID_INPUT", "approach_threshold_m must be positive.")
        if poll_interval_s <= 0:
            self.stop_tool("monitor_danger_zones")
            return SkillResult.fail("INVALID_INPUT", "poll_interval_s must be positive.")

        background_launched = False
        try:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return SkillResult.fail(
                    "ALREADY_RUNNING",
                    "Danger-zone monitoring is already running. "
                    "Call stop_monitoring_danger_zones first.",
                )

            self._monitor_stop_event.clear()
            self._last_notified.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(approach_threshold_m, poll_interval_s),
                daemon=True,
            )
            self._monitor_thread.start()
            background_launched = True
            return SkillResult.ok(
                f"Monitoring {len(self._zones)} danger zone(s) "
                f"(threshold={approach_threshold_m:.2f}m, poll={poll_interval_s:.2f}s).",
                zone_count=len(self._zones),
                approach_threshold_m=approach_threshold_m,
                poll_interval_s=poll_interval_s,
            )
        finally:
            if not background_launched:
                self.stop_tool("monitor_danger_zones")

    @skill
    def stop_monitoring_danger_zones(self) -> SkillResult[AegisError]:
        """Stop an in-progress `start_monitoring_danger_zones` call.

        Safe to call even if nothing is currently monitoring.
        """
        self._monitor_stop_event.set()
        return SkillResult.ok("Danger-zone monitoring stop requested.")

    def _monitor_loop(self, approach_threshold_m: float, poll_interval_s: float) -> None:
        try:
            while not self._monitor_stop_event.is_set():
                tf = self.tfbuffer.get("world", "base_link")
                if tf is not None and self._zones:
                    position = tf.to_pose().position
                    px, py = float(position.x), float(position.y)
                    now = time.monotonic()
                    for zone in self._zones.values():
                        distance = distance_to_polygon(px, py, zone.vertex_tuples())
                        if distance < approach_threshold_m:
                            self._maybe_notify(zone.name, px, py, distance, now)
                self._monitor_stop_event.wait(poll_interval_s)
        finally:
            self.stop_tool("monitor_danger_zones")

    def _maybe_notify(
        self, zone_name: str, px: float, py: float, distance: float, now: float
    ) -> None:
        """Rate-limited notification for one zone.

        Notifies immediately the first time a zone is approached; after
        that, only re-notifies once `_RENOTIFY_COOLDOWN_S` has elapsed, or
        sooner if distance has closed by at least `_RENOTIFY_MIN_DELTA_M`
        since the last notification (so a fast approach still gets timely
        updates even inside the cooldown window).
        """
        last = self._last_notified.get(zone_name)
        if last is not None:
            last_time, last_distance = last
            elapsed = now - last_time
            closed_by = last_distance - distance
            if elapsed < _RENOTIFY_COOLDOWN_S and closed_by < _RENOTIFY_MIN_DELTA_M:
                return

        self._last_notified[zone_name] = (now, distance)
        message = json.dumps(
            {
                "zone": zone_name,
                "position": {"x": px, "y": py},
                "timestamp": time.time(),
                "distance": round(distance, 3),
            }
        )
        self.tool_update("monitor_danger_zones", message)

    # ------------------------------------------------------------------
    # Skill 11: navigate_to_safe_intercept_position
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT])
    def navigate_to_safe_intercept_position(
        self,
        zone_name: str,
        clearance_m: float = 1.5,
        timeout_s: float = _DEFAULT_INTERCEPT_TIMEOUT_S,
    ) -> SkillResult[AegisError]:
        """Position the robot near a danger zone, outside it, with clearance.

        Positions the robot near the zone with clearance; never enters the
        zone, never blocks or contacts a person. This does not physically
        prevent anyone from entering the zone -- it only positions the robot
        nearby, per this project's explicit prohibition on physical
        intercept/blocking behavior. It never computes a goal from, or
        targets, any person's position or path -- only the zone's own fixed
        geometry and the robot's current position.

        Geometry: finds the point on the zone's boundary nearest to the
        robot's current position, then offsets `clearance_m` further out
        along the line from the zone's centroid through that boundary
        point (i.e. straight out and away from the zone, not toward the
        robot's approach heading) so the result is unambiguously outside
        the polygon. The computed goal's distance to the zone is verified to
        be >= `clearance_m` before any goal is issued; if that check fails
        this reports EXECUTION_FAILED rather than moving the robot.

        Args:
            zone_name: A zone previously created with `create_danger_zone`.
            clearance_m: Minimum distance in meters to keep from the zone
                boundary. Must be positive.
            timeout_s: Give up and report failure after this many seconds.

        Example:
            navigate_to_safe_intercept_position("pool edge")
            navigate_to_safe_intercept_position("pool edge", clearance_m=2.0)
        """
        zone_name = zone_name.strip()
        if not zone_name:
            return SkillResult.fail("INVALID_INPUT", "zone_name must not be empty.")
        if clearance_m <= 0:
            return SkillResult.fail("INVALID_INPUT", "clearance_m must be positive.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        zone = self._zones.get(zone_name.lower())
        if zone is None:
            return SkillResult.fail("ZONE_NOT_FOUND", f"No danger zone called '{zone_name}'.")

        try:
            tf = self.tfbuffer.get("world", "base_link")
            if tf is None:
                return SkillResult.fail(
                    "EXECUTION_FAILED", "Could not get the robot's current position."
                )
            robot_pos = tf.to_pose().position
            rx, ry = float(robot_pos.x), float(robot_pos.y)

            vertices = zone.vertex_tuples()
            nx, ny, _boundary_dist = _nearest_boundary_point(rx, ry, vertices)

            # Direction from the zone's centroid through the nearest boundary
            # point, i.e. straight outward. Using the centroid->boundary ray
            # (rather than robot->boundary) keeps the offset direction stable
            # and always outward even if the robot starts inside the zone.
            cx = sum(v[0] for v in vertices) / len(vertices)
            cy = sum(v[1] for v in vertices) / len(vertices)
            dir_x, dir_y = nx - cx, ny - cy
            dir_len = math.hypot(dir_x, dir_y)
            if dir_len < 1e-9:
                # Degenerate: boundary point coincides with centroid (should
                # not happen for a valid polygon). Fall back to +x.
                dir_x, dir_y = 1.0, 0.0
                dir_len = 1.0
            dir_x, dir_y = dir_x / dir_len, dir_y / dir_len

            goal_x = nx + dir_x * clearance_m
            goal_y = ny + dir_y * clearance_m

            # Sanity-check our own math before issuing any goal: the
            # candidate must be outside the polygon and at least
            # clearance_m from its boundary.
            if point_in_polygon(goal_x, goal_y, vertices):
                return SkillResult.fail(
                    "EXECUTION_FAILED",
                    "Computed intercept position fell inside the zone; refusing to navigate.",
                )
            actual_clearance = distance_to_polygon(goal_x, goal_y, vertices)
            if actual_clearance < clearance_m - 1e-6:
                return SkillResult.fail(
                    "EXECUTION_FAILED",
                    f"Computed intercept position only has {actual_clearance:.2f}m clearance "
                    f"(wanted {clearance_m:.2f}m); refusing to navigate.",
                )

            heading = math.atan2(cy - goal_y, cx - goal_x)  # face toward the zone
            goal = PoseStamped(
                position=make_vector3(goal_x, goal_y, 0.0),
                orientation=Quaternion.from_euler(make_vector3(0.0, 0.0, heading)),
                frame_id="world",
            )

            if not self._navigation.set_goal(goal):
                return SkillResult.fail(
                    "EXECUTION_FAILED", f"Planner rejected the intercept goal for '{zone_name}'."
                )
        except Exception as exc:
            logger.exception("navigate_to_safe_intercept_position failed", zone_name=zone_name)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not start navigation: {exc}")

        outcome, elapsed_s = self._wait_for_arrival(timeout_s)
        if outcome == "reached":
            return SkillResult.ok(
                f"Positioned near '{zone_name}' with {clearance_m:.2f}m clearance.",
                zone_name=zone_name,
                clearance_m=clearance_m,
                x=goal_x,
                y=goal_y,
                elapsed_s=round(elapsed_s, 1),
            )
        if outcome == "timeout":
            return SkillResult.fail(
                "EXECUTION_TIMEOUT",
                f"Did not reach the intercept position near '{zone_name}' within {timeout_s:.0f}s.",
            )
        return SkillResult.fail(
            "EXECUTION_FAILED",
            f"Navigation to the intercept position near '{zone_name}' was cancelled or failed.",
        )

    def _wait_for_arrival(self, timeout_s: float) -> tuple[str, float]:
        """Poll the navigation interface until arrival, cancellation/failure, or timeout.

        Duplicated from ``locations.py``'s ``_wait_for_arrival`` /
        ``navigation_skills.py``'s ``_wait_for_goal`` (same reasoning: small
        independent ``Module``, no cross-import of navigation logic).
        """
        start = time.monotonic()
        deadline = start + timeout_s
        idle_since: float | None = None

        while time.monotonic() < deadline:
            if self._navigation.is_goal_reached():
                return "reached", time.monotonic() - start
            if self._navigation.get_state() == NavigationState.FOLLOWING_PATH:
                idle_since = None
            elif idle_since is None:
                idle_since = time.monotonic()
            elif time.monotonic() - idle_since > _GOAL_SETTLE_S:
                return "failed", time.monotonic() - start
            time.sleep(_GOAL_POLL_INTERVAL_S)

        return "timeout", time.monotonic() - start

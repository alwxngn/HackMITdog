"""Skills 1, 2, 4 — turn-in-place, obstacle approach, and waypoint patrol.

Reuses DimOS's navigation stack the same way
``UnitreeSkillContainer.move_to``/``NavigationSkillContainer`` and
``hackmitdog.aegis.locations`` already do (see
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §2, §6):

- ``NavigationInterfaceSpec.set_goal`` / ``get_state`` / ``is_goal_reached`` /
  ``cancel_goal`` (``dimos.navigation.navigation_spec``) for all movement.
- ``self.tfbuffer.get("world", "base_link")`` for the robot's current pose,
  the same helper ``UnitreeSkillContainer.move_to`` reads.
- ``ExtendedSpatialMemorySpec`` (``hackmitdog.aegis.spec_ext``) for named
  -location lookup in ``patrol_waypoints``, reusing the same
  ``SpatialMemory.find_robot_location`` RPC ``locations.py`` uses for
  ``go_to_named_location`` — not a separate lookup implementation.

This module is deliberately self-contained: it does not import
``UnitreeSkillContainer`` or ``hackmitdog.aegis.locations`` and instead
duplicates their small pose-construction / poll-until-arrival helpers, so it
can be loaded into a blueprint independently of which other skill modules are
also present (matching DimOS's own convention of small per-``Module``
helpers rather than cross-module inheritance — see
``dimos/agents/skills/person_follow.py`` and ``locations.py``'s
``_wait_for_arrival``).

No DimOS code is modified.
"""

from __future__ import annotations

import math
import threading
import time

from dimos.agents.annotation import skill
from dimos.agents.capabilities import CAP_MOVEMENT
from dimos.agents.skill_result import SkillResult
from dimos.core.module import Module
from dimos.core.stream import In
from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
from dimos.msgs.geometry_msgs.Quaternion import Quaternion
from dimos.msgs.geometry_msgs.Vector3 import Vector3, make_vector3
from dimos.msgs.nav_msgs.OccupancyGrid import CostValues, OccupancyGrid
from dimos.msgs.tf2_msgs.TFMessage import TFMessage
from dimos.navigation.base import NavigationState
from dimos.navigation.navigation_spec import NavigationInterfaceSpec
from dimos.utils.logging_config import setup_logger

from hackmitdog.aegis.skill_errors import AegisError
from hackmitdog.aegis.spec_ext import ExtendedSpatialMemorySpec

logger = setup_logger()

_GOAL_POLL_INTERVAL_S = 0.1
_GOAL_SETTLE_S = 1.5

_DEFAULT_TURN_TIMEOUT_S = 30.0

# approach_obstacle tuning: how far each incremental forward nudge goes, and
# how close (plus tolerance) counts as "there" so we don't chatter forever
# around the target distance.
_APPROACH_STEP_M = 0.25
_APPROACH_TOLERANCE_M = 0.05
_APPROACH_STEP_TIMEOUT_S = 5.0
_APPROACH_MAX_RANGE_M = 10.0  # nothing ahead within this counts as "no obstacle"

_DEFAULT_PATROL_TIMEOUT_S = 600.0
_PATROL_ARRIVAL_TIMEOUT_S = 60.0


def _wait_for_goal(
    navigation: NavigationInterfaceSpec, timeout_s: float
) -> tuple[str, float]:
    """Poll `navigation` until arrival, cancellation/failure, or timeout.

    Duplicated from ``locations.py``'s ``_wait_for_arrival`` (itself mirroring
    ``UnitreeSkillContainer._wait_for_goal``): the planner drops out of
    FOLLOWING_PATH for a moment on every replan, so a pause only counts as
    "done" once it has held for ``_GOAL_SETTLE_S``.
    """
    start = time.monotonic()
    deadline = start + timeout_s
    idle_since: float | None = None

    while time.monotonic() < deadline:
        if navigation.is_goal_reached():
            return "reached", time.monotonic() - start
        if navigation.get_state() == NavigationState.FOLLOWING_PATH:
            idle_since = None
        elif idle_since is None:
            idle_since = time.monotonic()
        elif time.monotonic() - idle_since > _GOAL_SETTLE_S:
            return "failed", time.monotonic() - start
        time.sleep(_GOAL_POLL_INTERVAL_S)

    return "timeout", time.monotonic() - start


class NavigationSkills(Module):
    """Turn-in-place, obstacle approach, and multi-waypoint patrol."""

    _navigation: NavigationInterfaceSpec
    _spatial_memory: ExtendedSpatialMemorySpec

    tf: In[TFMessage]
    global_costmap: In[OccupancyGrid]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._should_stop_patrol = threading.Event()
        self._patrol_thread: threading.Thread | None = None
        self._costmap_lock = threading.Lock()
        self._latest_costmap_grid: OccupancyGrid | None = None

    async def handle_global_costmap(self, msg: OccupancyGrid) -> None:
        """Auto-bound by `Module._auto_bind_handlers` for the `global_costmap`
        input port (same convention `PatrollingModule.handle_global_costmap`
        uses) -- caches the latest costmap for `_distance_to_obstacle_ahead`."""
        with self._costmap_lock:
            self._latest_costmap_grid = msg

    # ------------------------------------------------------------------
    # Skill 2: turn_relative
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT])
    def turn_relative(
        self, angle_degrees: float, timeout_s: float = _DEFAULT_TURN_TIMEOUT_S
    ) -> SkillResult[AegisError]:
        """Turn the robot in place, relative to its current heading.

        Sign convention (standard right-hand-rule, z-up yaw, confirmed against
        `Quaternion.from_euler` and `UnitreeSkillContainer._goal_pose`'s
        relative-turn math, which this skill mirrors): **positive
        `angle_degrees` turns left (counter-clockwise, viewed from above);
        negative turns right (clockwise)**. E.g. `turn_relative(90)` turns 90
        degrees left; `turn_relative(-90)` turns 90 degrees right.

        Blocks until the turn completes, fails, or `timeout_s` elapses.

        Args:
            angle_degrees: Degrees to turn from the current heading. Positive
                is left/counter-clockwise, negative is right/clockwise.
            timeout_s: Give up and report failure after this many seconds.
                A turn-in-place normally finishes well under 30s.

        Example:
            turn_relative(90)      # turn left 90 degrees
            turn_relative(-45)     # turn right 45 degrees
        """
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")
        try:
            angle_degrees = float(angle_degrees)
        except (TypeError, ValueError):
            return SkillResult.fail("INVALID_INPUT", "angle_degrees must be a number.")

        try:
            tf = self.tfbuffer.get("world", "base_link")
            if tf is None:
                return SkillResult.fail(
                    "EXECUTION_FAILED", "Could not get the robot's current position."
                )

            current = tf.to_pose()
            euler = current.orientation.to_euler()
            yaw = euler.yaw + math.radians(angle_degrees)
            orientation = Quaternion.from_euler(Vector3(euler.roll, euler.pitch, yaw))
            goal = PoseStamped(
                position=current.position, orientation=orientation, frame_id="world"
            )

            if not self._navigation.set_goal(goal):
                return SkillResult.fail("EXECUTION_FAILED", "Planner rejected the turn goal.")
        except Exception as exc:
            logger.exception("turn_relative failed", angle_degrees=angle_degrees)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not start the turn: {exc}")

        outcome, elapsed_s = _wait_for_goal(self._navigation, timeout_s)
        if outcome == "reached":
            return SkillResult.ok(
                f"Turned {angle_degrees:.0f} degrees.",
                angle_degrees=angle_degrees,
                elapsed_s=round(elapsed_s, 1),
            )
        if outcome == "timeout":
            return SkillResult.fail(
                "EXECUTION_TIMEOUT", f"Turn did not complete within {timeout_s:.0f}s."
            )
        return SkillResult.fail("EXECUTION_FAILED", "Turn was cancelled or failed.")

    # ------------------------------------------------------------------
    # Skill 1: approach_obstacle
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT])
    def approach_obstacle(
        self,
        distance_m: float = 0.30,
        direction: str = "front",
        max_travel_m: float = 3.0,
        timeout_s: float = 30.0,
    ) -> SkillResult[AegisError]:
        """Move forward until roughly `distance_m` from the nearest obstacle ahead.

        Measures obstacle distance from the live occupancy costmap (raycasting
        forward from the robot's pose through grid cells — see the
        `_distance_to_obstacle_ahead` implementation), then advances in small,
        re-measured steps rather than one blind move, so it tracks a moving or
        imprecise reading safely. This is a plain synchronous Python loop
        making direct DimOS navigation calls — no LLM/agent call is made or
        needed inside the loop, only deterministic distance checks.

        Args:
            distance_m: Target standoff distance from the obstacle, in meters.
            direction: Which way to look for the obstacle. Only "front" is
                supported today; any other value fails with INVALID_INPUT.
            max_travel_m: Safety cap on total distance travelled by this call.
                Fails with MAX_DISTANCE_EXCEEDED rather than travel further.
            timeout_s: Overall deadline for the whole approach.

        Example:
            approach_obstacle(distance_m=0.3)
            approach_obstacle(distance_m=0.5, max_travel_m=2.0)
        """
        if direction != "front":
            return SkillResult.fail(
                "INVALID_INPUT",
                f"direction='{direction}' is not supported yet; only 'front' works today.",
            )
        if distance_m < 0:
            return SkillResult.fail("INVALID_INPUT", "distance_m must not be negative.")
        if max_travel_m <= 0:
            return SkillResult.fail("INVALID_INPUT", "max_travel_m must be positive.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        deadline = time.monotonic() + timeout_s
        travelled_m = 0.0

        try:
            tf = self.tfbuffer.get("world", "base_link")
            if tf is None:
                return SkillResult.fail(
                    "EXECUTION_FAILED", "Could not get the robot's current position."
                )
            start_position = tf.to_pose().position

            obstacle_distance = self._distance_to_obstacle_ahead()
            if obstacle_distance is None:
                return SkillResult.fail(
                    "EXECUTION_FAILED", "No costmap data available to measure obstacle distance."
                )

            if obstacle_distance <= distance_m + _APPROACH_TOLERANCE_M:
                return SkillResult.ok(
                    "Already at target distance from the obstacle.",
                    final_distance_m=round(obstacle_distance, 3),
                    travelled_m=0.0,
                    reason="already_at_target_distance",
                )

            while True:
                if time.monotonic() >= deadline:
                    return SkillResult.fail(
                        "EXECUTION_TIMEOUT",
                        f"Did not reach target distance within {timeout_s:.0f}s.",
                    )

                obstacle_distance = self._distance_to_obstacle_ahead()
                if obstacle_distance is None:
                    return SkillResult.fail(
                        "EXECUTION_FAILED", "Lost costmap data while approaching the obstacle."
                    )

                if obstacle_distance <= distance_m + _APPROACH_TOLERANCE_M:
                    return SkillResult.ok(
                        "Reached target distance from the obstacle.",
                        final_distance_m=round(obstacle_distance, 3),
                        travelled_m=round(travelled_m, 3),
                        reason="target_distance_reached",
                    )

                # Step size: the smaller of a bounded nudge and however far is
                # actually left to close, so we never overshoot past the
                # target distance in one step.
                remaining = obstacle_distance - distance_m
                step = min(_APPROACH_STEP_M, remaining)
                step = max(step, 0.05)

                if travelled_m + step > max_travel_m:
                    return SkillResult.fail(
                        "MAX_DISTANCE_EXCEEDED",
                        f"Reaching the target distance would exceed max_travel_m={max_travel_m:.2f}m.",
                    )

                tf = self.tfbuffer.get("world", "base_link")
                if tf is None:
                    return SkillResult.fail(
                        "EXECUTION_FAILED", "Could not get the robot's current position."
                    )
                current = tf.to_pose()
                goal_position = current.position + current.orientation.rotate_vector(
                    Vector3(step, 0, 0)
                )
                goal = PoseStamped(
                    position=goal_position,
                    orientation=current.orientation,
                    frame_id="world",
                )

                if not self._navigation.set_goal(goal):
                    return SkillResult.fail(
                        "EXECUTION_FAILED", "Planner rejected an incremental approach goal."
                    )

                step_timeout = min(_APPROACH_STEP_TIMEOUT_S, max(0.1, deadline - time.monotonic()))
                outcome, _elapsed = _wait_for_goal(self._navigation, step_timeout)
                if outcome == "failed":
                    return SkillResult.fail(
                        "EXECUTION_FAILED", "Navigation was cancelled or failed mid-approach."
                    )
                # "timeout" on a single small step is tolerated (the step is
                # tiny; we re-measure and keep going) as long as the overall
                # deadline hasn't passed -- checked at the top of the loop.

                tf = self.tfbuffer.get("world", "base_link")
                if tf is not None:
                    travelled_m = start_position.distance(tf.to_pose().position)
                else:
                    travelled_m += step
        except Exception as exc:
            logger.exception("approach_obstacle failed", distance_m=distance_m)
            return SkillResult.fail("EXECUTION_FAILED", f"Approach failed: {exc}")
        finally:
            # This skill issues several small goals in a loop rather than one
            # blocking call, so it -- not the caller -- is responsible for
            # never leaving a stray goal active on any exit path.
            self._navigation.cancel_goal()

    def _distance_to_obstacle_ahead(self) -> float | None:
        """Distance in meters to the nearest occupied cell in front of the robot.

        Chosen approach: raycast through the live `OccupancyGrid` costmap
        (`global_costmap: In[OccupancyGrid]`, published by DimOS's
        `CostMapper`) rather than filtering the raw LiDAR `PointCloud2`
        directly. The costmap already fuses/denoises the LiDAR into a single
        occupied/free/unknown grid the planner itself trusts, so this stays
        consistent with what `ReplanningAStarPlanner` considers an obstacle,
        and raycasting fixed-size grid cells is simpler and cheaper than
        angular-cone filtering a raw point cloud every tick. A raw-LiDAR
        fallback (`PointCloud2.filter_by_height` + min-range-in-cone) would
        be the alternative if a costmap is ever unavailable in some blueprint.

        Returns None if no costmap has been received yet. Returns
        `_APPROACH_MAX_RANGE_M` if the ray reaches that range without hitting
        an occupied or unknown cell (i.e. no obstacle detected ahead).
        """
        grid = self._latest_costmap()
        if grid is None or grid.grid.size == 0:
            return None

        tf = self.tfbuffer.get("world", "base_link")
        if tf is None:
            return None
        pose = tf.to_pose()
        heading = pose.orientation.to_euler().yaw

        resolution = grid.resolution
        step = resolution if resolution > 0 else 0.05
        distance = 0.0
        while distance < _APPROACH_MAX_RANGE_M:
            distance += step
            probe = pose.position + Vector3(
                distance * math.cos(heading), distance * math.sin(heading), 0.0
            )
            value = grid.cell_value(probe)
            if value == CostValues.OCCUPIED or value > 0:
                return distance
        return _APPROACH_MAX_RANGE_M

    def _latest_costmap(self) -> OccupancyGrid | None:
        with self._costmap_lock:
            return self._latest_costmap_grid

    # ------------------------------------------------------------------
    # Skill 4: patrol_waypoints
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT], lifecycle="background")
    def patrol_waypoints(
        self,
        locations: list[str],
        loop: bool = False,
        timeout_s: float = _DEFAULT_PATROL_TIMEOUT_S,
    ) -> SkillResult[AegisError]:
        """Visit a list of previously-saved named locations in order.

        Custom composition, not DimOS's `PatrollingModule` (that one picks
        goals to maximize area coverage; it has no fixed-waypoint-list mode).
        This instead calls the same navigation mechanism as
        `go_to_named_location` once per name, in sequence, in a background
        thread. Runs until every waypoint is visited (or `loop=True`, until
        `stop_patrol_waypoints` is called or `timeout_s` elapses). Unknown
        location names are logged and skipped, not treated as a hard failure.

        Args:
            locations: Ordered list of names previously saved with
                `save_named_location`.
            loop: If True, cycle through the list repeatedly instead of
                stopping after one pass.
            timeout_s: Overall deadline for the whole patrol.

        Example:
            patrol_waypoints(["kitchen", "living room", "front door"])
            patrol_waypoints(["post 1", "post 2"], loop=True, timeout_s=1800)

        Use `stop_patrol_waypoints` to cancel an in-progress patrol.
        """
        self.start_tool("patrol_waypoints")

        if not locations:
            self.stop_tool("patrol_waypoints")
            return SkillResult.fail("INVALID_INPUT", "locations must not be empty.")
        if timeout_s <= 0:
            self.stop_tool("patrol_waypoints")
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        background_launched = False
        try:
            if self._patrol_thread is not None and self._patrol_thread.is_alive():
                return SkillResult.fail(
                    "ALREADY_RUNNING",
                    "A patrol is already running. Call stop_patrol_waypoints first.",
                )

            self._should_stop_patrol.clear()
            self._patrol_thread = threading.Thread(
                target=self._patrol_loop,
                args=(list(locations), loop, timeout_s),
                daemon=True,
            )
            self._patrol_thread.start()
            background_launched = True
            return SkillResult.ok(
                f"Patrol started over {len(locations)} waypoint(s)."
                + (" Looping until stopped." if loop else ""),
                waypoint_count=len(locations),
                loop=loop,
            )
        finally:
            if not background_launched:
                self.stop_tool("patrol_waypoints")

    @skill
    def stop_patrol_waypoints(self) -> SkillResult[AegisError]:
        """Stop an in-progress `patrol_waypoints` call.

        Safe to call even if no patrol is running.
        """
        self._should_stop_patrol.set()
        return SkillResult.ok("Patrol stop requested.")

    def _patrol_loop(self, locations: list[str], loop: bool, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        visited = 0
        skipped = 0
        stop_reason = "completed"

        try:
            while True:
                for name in locations:
                    if self._should_stop_patrol.is_set():
                        stop_reason = "stopped"
                        return
                    if time.monotonic() >= deadline:
                        stop_reason = "timeout"
                        return

                    location = self._find_location(name)
                    if location is None:
                        logger.warning("patrol_waypoints: unknown location, skipping", name=name)
                        skipped += 1
                        self.tool_update(
                            "patrol_waypoints", f"Skipping unknown location '{name}'."
                        )
                        continue

                    try:
                        goal = PoseStamped(
                            position=make_vector3(*location.position),
                            orientation=Quaternion.from_euler(make_vector3(*location.rotation)),
                            frame_id="map",
                        )
                        if not self._navigation.set_goal(goal):
                            logger.warning(
                                "patrol_waypoints: planner rejected goal, skipping", name=name
                            )
                            skipped += 1
                            self.tool_update(
                                "patrol_waypoints", f"Planner rejected goal for '{name}', skipping."
                            )
                            continue

                        remaining = max(0.1, deadline - time.monotonic())
                        step_timeout = min(_PATROL_ARRIVAL_TIMEOUT_S, remaining)
                        outcome, _elapsed = _wait_for_goal(self._navigation, step_timeout)
                        if outcome == "reached":
                            visited += 1
                            self.tool_update("patrol_waypoints", f"Arrived at '{name}'.")
                        else:
                            skipped += 1
                            self.tool_update(
                                "patrol_waypoints", f"Could not reach '{name}' ({outcome})."
                            )
                    except Exception:
                        logger.exception("patrol_waypoints: navigation step failed", name=name)
                        skipped += 1
                        self.tool_update(
                            "patrol_waypoints", f"Error navigating to '{name}', skipping."
                        )

                if not loop:
                    stop_reason = "completed"
                    return
        finally:
            self._navigation.cancel_goal()
            self.tool_update(
                "patrol_waypoints",
                f"Patrol ended ({stop_reason}). Visited {visited}, skipped {skipped}.",
            )
            self.stop_tool("patrol_waypoints")
            self._should_stop_patrol.clear()

    def _find_location(self, name: str) -> object | None:
        try:
            return self._spatial_memory.find_robot_location(name)
        except Exception:
            logger.exception("patrol_waypoints: find_robot_location failed", name=name)
            return None

"""Skill 3 — named-location navigation and CRUD.

Reuses DimOS's existing spatial-memory + navigation stack end to end (see
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §3, §6):

- ``SpatialMemory.add_named_location`` / ``find_robot_location`` /
  ``get_robot_locations`` (``dimos.perception.experimental.spatial_perception``,
  reached here through :mod:`hackmitdog.aegis.spec_ext`'s
  ``ExtendedSpatialMemorySpec``) for save/find/list.
- ``NavigationInterfaceSpec.set_goal`` / ``cancel_goal``
  (``dimos.navigation.navigation_spec``) for the actual movement, the same
  interface ``UnitreeSkillContainer.move_to`` and
  ``NavigationSkillContainer.navigate_with_text`` already drive.

No DimOS code is modified. ``delete_named_location`` is the one genuinely new
piece — DimOS has no delete/remove method anywhere on ``SpatialMemory`` or
``SpatialVectorDB`` (confirmed in the plan's investigation) — implemented here
as a local tombstone set layered on top, so a "deleted" name stops resolving
through this module without touching DimOS's underlying store.
"""

from __future__ import annotations

import time

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
from hackmitdog.aegis.spec_ext import ExtendedSpatialMemorySpec

logger = setup_logger()

_DEFAULT_ARRIVAL_TIMEOUT_S = 60.0
_GOAL_POLL_INTERVAL_S = 0.1
_GOAL_SETTLE_S = 1.5


class LocationSkills(Module):
    """Named-location CRUD and navigation, backed by DimOS spatial memory."""

    _spatial_memory: ExtendedSpatialMemorySpec
    _navigation: NavigationInterfaceSpec

    tf: In[TFMessage]

    _deleted_names: set[str]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._deleted_names = set()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @skill
    def save_named_location(
        self, name: str, description: str | None = None
    ) -> SkillResult[AegisError]:
        """Remember the robot's current position under a name.

        Call this while the robot is physically standing where you want the
        name to point to. Use it to build a map of places like "kitchen",
        "bedroom", or "front door" so `go_to_named_location` can return here
        later.

        Args:
            name: Short place name, e.g. "kitchen". Case-insensitive for lookups.
            description: Optional free-text note about the place.

        Example:
            save_named_location("kitchen")
            save_named_location("front door", description="main entrance, no rug")
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")

        self._deleted_names.discard(name.lower())

        try:
            ok = self._spatial_memory.add_named_location(name, description=description)
        except Exception as exc:
            logger.exception("save_named_location failed", name=name)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not save '{name}': {exc}")

        if not ok:
            return SkillResult.fail(
                "EXECUTION_FAILED",
                f"Failed to store '{name}' in spatial memory (no odometry yet?).",
            )
        return SkillResult.ok(f"Saved current position as '{name}'.", name=name)

    @skill
    def list_named_locations(self) -> SkillResult[AegisError]:
        """List every named location currently remembered.

        Use this to see what places the robot already knows before deciding
        whether to `save_named_location` a new one or `go_to_named_location`
        an existing one.
        """
        try:
            locations = self._spatial_memory.get_robot_locations()
        except Exception as exc:
            logger.exception("list_named_locations failed")
            return SkillResult.fail("EXECUTION_FAILED", f"Could not list locations: {exc}")

        names = sorted(
            {loc.name for loc in locations if loc.name.lower() not in self._deleted_names}
        )
        return SkillResult.ok(
            f"{len(names)} named location(s)." if names else "No named locations saved yet.",
            names=names,
        )

    @skill
    def delete_named_location(self, name: str) -> SkillResult[AegisError]:
        """Forget a named location.

        DimOS's spatial memory has no underlying delete, so this marks the
        name as removed for this skill set's own lookups (`go_to_named_location`,
        `list_named_locations`); the underlying record may still exist in
        DimOS's spatial memory store for other consumers.

        Args:
            name: The location name to forget, as previously saved.
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")

        found = self._find_active(name)
        if found is None:
            return SkillResult.fail("LOCATION_NOT_FOUND", f"No named location called '{name}'.")

        self._deleted_names.add(name.lower())
        return SkillResult.ok(f"Forgot named location '{name}'.", name=name)

    def _find_active(self, name: str) -> object | None:
        if name.lower() in self._deleted_names:
            return None
        try:
            return self._spatial_memory.find_robot_location(name)
        except Exception:
            logger.exception("find_robot_location failed", name=name)
            return None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT])
    def go_to_named_location(
        self, name: str, timeout_s: float = _DEFAULT_ARRIVAL_TIMEOUT_S
    ) -> SkillResult[AegisError]:
        """Navigate to a previously saved named location and wait to arrive.

        Looks the name up in spatial memory, then drives there using DimOS's
        planner (with its own obstacle avoidance and replanning) and blocks
        until arrival, failure, or `timeout_s`. Cancel an in-progress call
        with `stop_location_navigation`.

        Args:
            name: A location saved earlier with `save_named_location`.
            timeout_s: Give up and report failure after this many seconds.

        Example:
            go_to_named_location("kitchen")
        """
        name = name.strip()
        if not name:
            return SkillResult.fail("INVALID_INPUT", "name must not be empty.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        location = self._find_active(name)
        if location is None:
            return SkillResult.fail(
                "LOCATION_NOT_FOUND",
                f"No named location called '{name}'. Use list_named_locations to see what's saved.",
            )

        goal = PoseStamped(
            position=make_vector3(*location.position),
            orientation=Quaternion.from_euler(make_vector3(*location.rotation)),
            frame_id="map",
        )

        if not self._navigation.set_goal(goal):
            return SkillResult.fail("EXECUTION_FAILED", f"Planner rejected the goal for '{name}'.")

        outcome, elapsed_s = self._wait_for_arrival(timeout_s)
        if outcome == "reached":
            return SkillResult.ok(f"Arrived at '{name}'.", name=name, elapsed_s=round(elapsed_s, 1))
        if outcome == "timeout":
            return SkillResult.fail(
                "EXECUTION_TIMEOUT", f"Did not reach '{name}' within {timeout_s:.0f}s."
            )
        return SkillResult.fail(
            "EXECUTION_FAILED", f"Navigation to '{name}' was cancelled or failed."
        )

    @skill
    def stop_location_navigation(self) -> SkillResult[AegisError]:
        """Cancel any in-progress `go_to_named_location` call.

        Safe to call even if nothing is navigating.
        """
        self._navigation.cancel_goal()
        return SkillResult.ok("Navigation cancelled.")

    def _wait_for_arrival(self, timeout_s: float) -> tuple[str, float]:
        """Poll the navigation interface until arrival, cancellation/failure, or timeout.

        Mirrors ``UnitreeSkillContainer._wait_for_goal``'s settle-time logic
        (the planner briefly drops out of FOLLOWING_PATH on every replan, so a
        pause only counts as "done" once it holds for ``_GOAL_SETTLE_S``).
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

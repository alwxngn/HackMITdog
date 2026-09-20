"""Skills 12, 13 — remembered-object lookup and bounded object search.

Reuses the exact same DimOS spatial-memory mechanism
``hackmitdog.aegis.locations`` uses for places (see
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §3, §6 rows 12/13): object memory and
place memory are the same underlying ``RobotLocation`` store in
``SpatialMemory`` (``dimos.perception.experimental.spatial_perception``,
reached here through ``ExtendedSpatialMemorySpec`` in
``hackmitdog.aegis.spec_ext``) — an object is just a named location saved
under the object's name instead of a place's name.

- ``SpatialMemory.add_named_location`` / ``find_robot_location`` for exact
  storage/lookup by name.
- ``SpatialMemory.query_by_text`` for a semantic fallback lookup, mirroring
  ``NavigationSkillContainer._navigate_using_semantic_map``'s
  similarity-threshold gate (``dimos/agents/skills/navigation.py``).
- ``NavigationInterfaceSpec.set_goal`` / ``cancel_goal`` for the navigation
  step in ``search_for_object``, the same interface
  ``locations.py``'s ``go_to_named_location`` drives.

**Real DimOS limitation (confirmed from source, not assumed):**
``SpatialMemory.add_named_location(name, position=None, rotation=None,
description=None)`` has no ``room``/``metadata`` parameter. Internally it
builds a ``RobotLocation(name=..., position=..., rotation=...,
description=..., timestamp=...)`` and never sets ``RobotLocation.metadata``
from the call — so there is no real structured-metadata field this module can
write through the ``@rpc`` surface it's given, even though the
``RobotLocation`` dataclass itself has a ``metadata`` field. The only place a
caller-supplied ``room`` can honestly go is into the free-text
``description``, which is what this module does. It is never inferred or
guessed when the caller omits it, per the plan's explicit rule.

This module is deliberately self-contained: it does not import
``hackmitdog.aegis.locations`` and instead duplicates the small
poll-until-arrival helper, matching ``navigation_skills.py``'s stated
convention of small per-``Module`` helpers rather than cross-module
inheritance.

No DimOS code is modified.
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
from dimos.msgs.sensor_msgs.Image import Image
from dimos.msgs.tf2_msgs.TFMessage import TFMessage
from dimos.navigation.base import NavigationState
from dimos.navigation.navigation_spec import NavigationInterfaceSpec
from dimos.types.robot_location import RobotLocation
from dimos.utils.logging_config import setup_logger

from hackmitdog.aegis.skill_errors import AegisError
from hackmitdog.aegis.spec_ext import ExtendedSpatialMemorySpec

logger = setup_logger()

_GOAL_POLL_INTERVAL_S = 0.1
_GOAL_SETTLE_S = 1.5
_DEFAULT_NAV_TIMEOUT_S = 60.0
_DEFAULT_SEARCH_TIMEOUT_S = 60.0
_FRAME_CAPTURE_TIMEOUT_S = 5.0

# Same semantic-match gate `NavigationSkillContainer._navigate_using_semantic_map`
# uses (dimos/agents/skills/navigation.py, `_similarity_threshold = 0.23`) for
# query_by_text's `distance` field (similarity = 1 - distance). Reused as-is
# here rather than inventing a different threshold, so "found via semantic
# search" means the same thing across every skill in this codebase that does
# a text-query spatial-memory fallback.
_SEMANTIC_SIMILARITY_THRESHOLD = 0.23


def _wait_for_goal(
    navigation: NavigationInterfaceSpec, timeout_s: float
) -> tuple[str, float]:
    """Poll `navigation` until arrival, cancellation/failure, or timeout.

    Duplicated from ``locations.py``'s ``_wait_for_arrival`` /
    ``navigation_skills.py``'s ``_wait_for_goal`` (itself mirroring
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


class ObjectMemorySkills(Module):
    """Remember where objects were last seen, and go check a remembered spot."""

    _spatial_memory: ExtendedSpatialMemorySpec
    _navigation: NavigationInterfaceSpec

    tf: In[TFMessage]
    color_image: In[Image]

    # ------------------------------------------------------------------
    # Skill 12: remember_object_location / find_remembered_object
    # ------------------------------------------------------------------

    @skill
    def remember_object_location(
        self, object_name: str, room: str | None = None
    ) -> SkillResult[AegisError]:
        """Remember an object's location as the robot's current position.

        Call this while the robot is at (or right next to) the object — the
        robot's current position is stored as the object's remembered
        location. DimOS has no separate "object held vs. object seen in the
        world" concept at this layer, so this honestly models "the robot
        saw/was told about this object here," not a hand-tracked grasp pose.

        Uses the same spatial-memory mechanism `save_named_location` uses for
        places (`locations.py`) — object memory and place memory are the same
        underlying store, just keyed by an object name instead of a place
        name.

        Args:
            object_name: Name of the object, e.g. "keys". Case-insensitive
                for lookups.
            room: Optional room label, e.g. "kitchen". Only stored if you
                explicitly supply it — never inferred or guessed. DimOS's
                `add_named_location` has no dedicated room/metadata field, so
                this is folded into the location's free-text description.

        Example:
            remember_object_location("keys")
            remember_object_location("keys", room="kitchen")
        """
        object_name = object_name.strip()
        if not object_name:
            return SkillResult.fail("INVALID_INPUT", "object_name must not be empty.")

        description = f"Object: {object_name}"
        if room is not None:
            room = room.strip()
            if room:
                description += f" (room: {room})"

        try:
            ok = self._spatial_memory.add_named_location(
                object_name, description=description
            )
        except Exception as exc:
            logger.exception("remember_object_location failed", object_name=object_name)
            return SkillResult.fail(
                "EXECUTION_FAILED", f"Could not remember '{object_name}': {exc}"
            )

        if not ok:
            return SkillResult.fail(
                "EXECUTION_FAILED",
                f"Failed to store '{object_name}' in spatial memory (no odometry yet?).",
            )

        metadata: dict[str, object] = {"object_name": object_name}
        if room:
            metadata["room"] = room
        return SkillResult.ok(
            f"Remembered current position as '{object_name}'.", **metadata
        )

    @skill
    def find_remembered_object(self, object_name: str) -> SkillResult[AegisError]:
        """Look up a remembered object's last-known location.

        Two-stage lookup, mirroring `NavigationSkillContainer.navigate_with_text`'s
        fallback chain: first an exact (case-insensitive) name match, then a
        semantic text search over everything in spatial memory (tagged
        locations and recorded frames alike) if no exact match exists. A
        semantic match only counts if its similarity score clears the same
        0.23 threshold `navigate_with_text`'s own semantic fallback uses, so a
        weak/unrelated match isn't reported as a real find.

        Args:
            object_name: Name of the object to look up, as previously saved
                with `remember_object_location`.

        Example:
            find_remembered_object("keys")
        """
        object_name = object_name.strip()
        if not object_name:
            return SkillResult.fail("INVALID_INPUT", "object_name must not be empty.")

        try:
            location = self._spatial_memory.find_robot_location(object_name)
        except Exception:
            logger.exception("find_remembered_object: exact lookup failed", object_name=object_name)
            location = None

        if location is not None:
            return self._found_result(location, match_type="exact")

        try:
            results = self._spatial_memory.query_by_text(object_name, limit=3)
        except Exception as exc:
            logger.exception(
                "find_remembered_object: semantic lookup failed", object_name=object_name
            )
            return SkillResult.fail(
                "LOCATION_NOT_FOUND",
                f"No remembered location for '{object_name}' (semantic search failed: {exc}).",
            )

        for result in results:
            distance = result.get("distance")
            similarity = 1.0 - (distance if distance is not None else 1.0)
            if similarity < _SEMANTIC_SIMILARITY_THRESHOLD:
                continue
            location = self._robot_location_from_query_result(result)
            if location is not None:
                return self._found_result(
                    location, match_type="semantic", similarity=round(similarity, 3)
                )

        return SkillResult.fail(
            "LOCATION_NOT_FOUND",
            f"No remembered location for '{object_name}'. "
            "Use remember_object_location to save one first.",
        )

    def _found_result(
        self, location: RobotLocation, *, match_type: str, similarity: float | None = None
    ) -> SkillResult[AegisError]:
        metadata: dict[str, object] = {
            "name": location.name,
            "position": list(location.position),
            "timestamp": location.timestamp,
            "match_type": match_type,
        }
        if similarity is not None:
            metadata["similarity"] = similarity
        if location.metadata:
            metadata["stored_metadata"] = location.metadata
        return SkillResult.ok(f"Found remembered location for '{location.name}'.", **metadata)

    def _robot_location_from_query_result(self, result: dict) -> RobotLocation | None:  # type: ignore[type-arg]
        """Best-effort conversion of a `query_by_text` result dict into a `RobotLocation`.

        `query_by_text` (see `spatial_perception.py`) returns raw vector-DB
        query results, whose `metadata` list holds primitive `pos_x`/`pos_y`/
        `pos_z`/`rot_x`/`rot_y`/`rot_z` fields (the same shape
        `NavigationSkillContainer._get_goal_pose_from_result` reads) rather
        than a `RobotLocation` object directly.
        """
        metadata_list = result.get("metadata")
        if not metadata_list:
            return None
        first = metadata_list[0] if isinstance(metadata_list, list) else metadata_list
        if not isinstance(first, dict) or "pos_x" not in first:
            return None
        try:
            return RobotLocation(
                name=first.get("location_name", "unknown"),
                position=(
                    float(first.get("pos_x", 0.0)),
                    float(first.get("pos_y", 0.0)),
                    float(first.get("pos_z", 0.0)),
                ),
                rotation=(
                    float(first.get("rot_x", 0.0)),
                    float(first.get("rot_y", 0.0)),
                    float(first.get("rot_z", 0.0)),
                ),
                timestamp=float(first.get("timestamp", time.time())),
            )
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Skill 13: search_for_object
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT])
    def search_for_object(
        self,
        object_name: str,
        verify_visually: bool = True,
        timeout_s: float = _DEFAULT_SEARCH_TIMEOUT_S,
    ) -> SkillResult[AegisError]:
        """Go check a remembered location for an object. Does not scan/explore.

        This only checks a location already saved with
        `remember_object_location` (or matched semantically by
        `find_remembered_object`) — DimOS has no open-vocabulary "search the
        whole house" capability, so if nothing is remembered for
        `object_name` this fails immediately rather than wandering around
        looking.

        Steps, all counted against the single `timeout_s` deadline: (1) look
        up the object via `find_remembered_object`; (2) if found, navigate
        there and wait to arrive, using the same navigate-and-wait mechanism
        `go_to_named_location` uses; (3) if `verify_visually=True`, grab the
        current camera frame once arrived.

        Be precise about what step 3 does and does not mean: this captures a
        frame as a best-effort presence check, it does **not** run any object
        detector against it. No open-vocabulary detector is wired into this
        skill (a real detector integration — e.g. `Owlv2Detector` — is
        documented as future work in the implementation plan, not done here).
        A successful capture is reported as `frame_captured: True` with a
        message that plainly says the object's presence was **not** visually
        confirmed — never claim "I see the keys" from this alone.

        Args:
            object_name: Name of the object to look for, as previously saved
                with `remember_object_location`.
            verify_visually: If True, capture a camera frame at the
                destination as a best-effort check (see caveat above). If
                False, skip the capture and report arrival only.
            timeout_s: Hard deadline covering the memory lookup, navigation,
                and optional frame capture combined.

        Example:
            search_for_object("keys")
            search_for_object("keys", verify_visually=False, timeout_s=30)
        """
        object_name = object_name.strip()
        if not object_name:
            return SkillResult.fail("INVALID_INPUT", "object_name must not be empty.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        deadline = time.monotonic() + timeout_s

        lookup = self.find_remembered_object(object_name)
        if not lookup.success:
            return SkillResult.fail(
                "LOCATION_NOT_FOUND",
                f"No remembered location for '{object_name}'. Nothing to search. "
                "Use remember_object_location to save one first.",
            )

        position = lookup.metadata.get("position")
        if not position:
            return SkillResult.fail(
                "EXECUTION_FAILED",
                f"Found a memory record for '{object_name}' but it had no position.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return SkillResult.fail(
                "EXECUTION_TIMEOUT", f"Timed out before navigating to '{object_name}'."
            )

        goal = PoseStamped(
            position=make_vector3(*position),
            orientation=Quaternion.from_euler(make_vector3(0.0, 0.0, 0.0)),
            frame_id="map",
        )

        if not self._navigation.set_goal(goal):
            return SkillResult.fail(
                "EXECUTION_FAILED", f"Planner rejected the goal for '{object_name}'."
            )

        outcome, elapsed_s = _wait_for_goal(self._navigation, remaining)
        if outcome == "timeout":
            return SkillResult.fail(
                "EXECUTION_TIMEOUT",
                f"Did not reach the remembered location for '{object_name}' within {timeout_s:.0f}s.",
            )
        if outcome != "reached":
            return SkillResult.fail(
                "EXECUTION_FAILED",
                f"Navigation to '{object_name}''s remembered location was cancelled or failed.",
            )

        result_metadata: dict[str, object] = {
            "object_name": object_name,
            "match_type": lookup.metadata.get("match_type"),
            "elapsed_s": round(elapsed_s, 1),
        }

        if not verify_visually:
            return SkillResult.ok(
                f"Arrived at the remembered location for '{object_name}'. "
                "Visual verification was not requested.",
                **result_metadata,
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result_metadata["frame_captured"] = False
            return SkillResult.ok(
                f"Arrived at the remembered location for '{object_name}', but ran out of "
                "time before capturing a verification frame. Object presence was NOT checked.",
                **result_metadata,
            )

        try:
            self.color_image.get_next(timeout=min(_FRAME_CAPTURE_TIMEOUT_S, remaining))
            result_metadata["frame_captured"] = True
            return SkillResult.ok(
                f"Arrived at the remembered location for '{object_name}' and captured a "
                "camera frame there. This confirms the robot looked, NOT that the object "
                "was visually detected — no object detector was run against the frame.",
                **result_metadata,
            )
        except Exception:
            logger.exception("search_for_object: frame capture failed", object_name=object_name)
            result_metadata["frame_captured"] = False
            return SkillResult.ok(
                f"Arrived at the remembered location for '{object_name}', but no camera "
                "frame could be captured (camera may not be running). Object presence was "
                "NOT checked.",
                **result_metadata,
            )

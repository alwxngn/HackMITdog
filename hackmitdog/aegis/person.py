"""Skills 6, 7, 8 — person detection, person following, and escort.

Reuses DimOS's person-perception and person-follow stack (see
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §3, §6 rows 6/7/8):

- ``YoloPersonDetector`` (``dimos.perception.detection.detectors.person.yolo``)
  for ``detect_person`` — a dedicated YOLO11-pose + BoT-SORT person detector
  with a real, calibrated ``confidence`` field, run directly against a single
  captured frame rather than wired as a standing streaming module (see the
  code comment on ``detect_person`` for why an instant, single-frame call is
  the right shape here).
- ``PersonFollowSkillContainer`` (``dimos.agents.skills.person_follow``) for
  ``follow_person``/``stop_person_follow`` — DimOS already owns the entire
  background follow lifecycle (visual detection, EdgeTAM tracking, visual
  servoing, capability holding, lost-track handling); this module composes
  it rather than reimplementing any of it.
- ``ExtendedSpatialMemorySpec`` + ``NavigationInterfaceSpec`` (the same two
  specs ``hackmitdog.aegis.locations`` uses) for the navigation leg of
  ``escort_person``.

No DimOS code is modified.

**Two gaps this file deliberately does NOT paper over** (see plan §3, §6
rows 7/8, §8):

1. ``PersonFollowSkillContainer.follow_person`` has no enforced minimum
   standoff distance. It drives the robot to keep the person centered/sized
   in the camera frame (2D visual servoing) or, with 3D navigation enabled,
   toward a fixed offset from a 3D detection -- neither path takes this
   module's ``follow_distance_m`` as a live setpoint. ``follow_person`` below
   accepts the parameter for interface compatibility but documents, in its
   own docstring, that it is not enforced.
2. DimOS has no "is the person still following/nearby" primitive independent
   of a transient per-call detection. ``escort_person`` therefore only
   confirms a person is present *before* departing, then navigates and
   reports arrival -- it does not and cannot verify the person stayed with
   the robot during the walk.
"""

from __future__ import annotations

import threading
import time

from dimos.agents.annotation import skill
from dimos.agents.capabilities import CAP_MOVEMENT
from dimos.agents.skill_result import SkillResult
from dimos.agents.skills.person_follow import PersonFollowSkillContainer
from dimos.core.module import Module
from dimos.core.stream import In
from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
from dimos.msgs.geometry_msgs.Quaternion import Quaternion
from dimos.msgs.geometry_msgs.Vector3 import make_vector3
from dimos.msgs.sensor_msgs.Image import Image
from dimos.navigation.base import NavigationState
from dimos.navigation.navigation_spec import NavigationInterfaceSpec
from dimos.perception.detection.detectors.person.yolo import YoloPersonDetector
from dimos.utils.logging_config import setup_logger

from hackmitdog.aegis.skill_errors import AegisError
from hackmitdog.aegis.spec_ext import ExtendedSpatialMemorySpec

logger = setup_logger()

_FRAME_TIMEOUT_S = 5.0
_DEFAULT_ESCORT_TIMEOUT_S = 300.0
_ESCORT_GOAL_POLL_INTERVAL_S = 0.1
_ESCORT_GOAL_SETTLE_S = 1.5


class PersonSkills(Module):
    """Person detection, person-following, and escort-to-location skills."""

    # Direct Module-type injection: DimOS's blueprint composer treats a
    # Module-typed annotation the same way it treats a Spec-typed one
    # (confirmed in `dimos/core/coordination/blueprints.py::BlueprintAtom.create`,
    # which calls `is_module_type(annotation)` alongside `is_spec(annotation)`
    # and registers both as a `ModuleRef`) -- at blueprint-build time this
    # attribute is replaced with an RPC proxy to the running
    # `PersonFollowSkillContainer` instance, so calls below are ordinary
    # cross-module RPCs, not local method calls.
    _person_follow: PersonFollowSkillContainer
    _spatial_memory: ExtendedSpatialMemorySpec
    _navigation: NavigationInterfaceSpec

    color_image: In[Image]

    _escort_stop_event: threading.Event
    _escort_thread: threading.Thread | None

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        # Constructed once here and reused across calls -- YOLO model load is
        # expensive (weights + tracker init), so this must not happen inside
        # detect_person's per-call body. Mirrors how PersonFollowSkillContainer
        # builds its QwenVlModel once in __init__ rather than per skill call.
        self._person_detector = YoloPersonDetector()
        self._escort_stop_event = threading.Event()
        self._escort_thread = None

    # ------------------------------------------------------------------
    # Skill 6: detect_person
    # ------------------------------------------------------------------

    @skill
    def detect_person(self) -> SkillResult[AegisError]:
        """Detect whether a person is visible in the current camera view.

        Grabs the current camera frame and runs a dedicated person detector
        (YOLO11-pose) on that single frame. This is an instant, single-shot
        check, not a continuous tracker -- call it again to re-check.

        Reports only what the detector actually provides: a real detection
        confidence, the person's bounding box in pixel coordinates, and a
        normalized `relative_position` (bbox center mapped from image space
        to x,y in [-1, 1], where (0, 0) is the image center, -1/+1 on x is
        the left/right edge, and -1/+1 on y is the top/bottom edge -- so
        positive x means the person is right of center, positive y means
        below center).

        Does NOT report a `world_position` (3D/world-frame location) -- that
        requires combining this 2D detection with depth and a TF lift
        (`Detection3DBBox`), which this skill does not do. Does NOT report
        any identity/name for the person -- the detector recognizes "a
        person", not who they are.

        Example:
            detect_person()
        """
        try:
            image = self.color_image.get_next(timeout=_FRAME_TIMEOUT_S)
        except Exception as exc:
            logger.exception("detect_person: no camera frame")
            return SkillResult.fail(
                "EXECUTION_TIMEOUT",
                f"No camera frame received within {_FRAME_TIMEOUT_S}s: {exc}",
            )

        try:
            detections = self._person_detector.process_image(image)
        except Exception as exc:
            logger.exception("detect_person: detector failed")
            return SkillResult.fail("EXECUTION_FAILED", f"Person detector failed: {exc}")

        valid = [d for d in detections if d.is_valid()]
        if not valid:
            return SkillResult.fail(
                "PERSON_NOT_FOUND", "No person detected in the current camera view."
            )

        best = max(valid, key=lambda d: d.confidence)
        cx, cy = best.center_bbox
        width, height = image.width, image.height
        rel_x = (cx / width) * 2.0 - 1.0 if width else 0.0
        rel_y = (cy / height) * 2.0 - 1.0 if height else 0.0

        return SkillResult.ok(
            "Person detected in current view.",
            confidence=round(best.confidence, 3),
            bbox=list(best.bbox),
            relative_position={"x": round(rel_x, 3), "y": round(rel_y, 3)},
        )

    # ------------------------------------------------------------------
    # Skill 7: follow_person / stop_person_follow
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT], lifecycle="background")
    def follow_person(
        self,
        query: str = "a person",
        follow_distance_m: float = 1.5,
        timeout_s: float = 120.0,
    ) -> SkillResult[AegisError]:
        """Start following a person matching a description.

        Thin wrapper over DimOS's `PersonFollowSkillContainer.follow_person`.
        That skill is itself `lifecycle="background"`: it detects the person
        once from the current camera frame, launches a background thread that
        tracks and drives toward them at 20 Hz, and returns immediately once
        tracking starts -- it does not block until following ends. This
        wrapper is deliberately just as thin: it calls straight through and
        relays the immediate return message, rather than adding a second
        blocking wait/timeout loop of its own that would fight with the
        underlying skill's own start_tool/stop_tool-managed lifecycle (that
        would mean two independent things both deciding when "done" is).
        Call `stop_person_follow` to end an in-progress follow.

        KNOWN LIMITATION -- `follow_distance_m` is accepted but NOT enforced.
        The underlying `follow_person` drives the robot using 2D visual
        servoing (keeping the person centered and a consistent size in the
        camera frame), not a metric distance controller. There is no minimum
        standoff distance guaranteed at any point during following. Do not
        rely on this skill to keep the robot a specific distance from the
        person; it only tries to keep them in view. `timeout_s` is accepted
        for interface compatibility but is also not enforced here, since the
        underlying skill has no notion of an overall follow-duration timeout
        either (it runs until lost-track, an explicit stop, or a takeover).

        Args:
            query: Free-text description of the person to follow, e.g. "man
                with blue shirt". Passed straight to the underlying VL-model
                detection step.
            follow_distance_m: Requested standoff distance in meters. NOT
                currently enforced -- see limitation above.
            timeout_s: Accepted for interface compatibility. NOT enforced --
                see limitation above.

        Example:
            follow_person("person in the red jacket")
        """
        query = query.strip()
        if not query:
            return SkillResult.fail("INVALID_INPUT", "query must not be empty.")
        if follow_distance_m <= 0:
            return SkillResult.fail("INVALID_INPUT", "follow_distance_m must be positive.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        try:
            message = self._person_follow.follow_person(query=query)
        except Exception as exc:
            logger.exception("follow_person: underlying skill call failed", query=query)
            return SkillResult.fail("EXECUTION_FAILED", f"Could not start following: {exc}")

        message_lower = str(message).lower()
        if "could not find" in message_lower or "no image available" in message_lower:
            return SkillResult.fail("PERSON_NOT_FOUND", str(message))
        if "failed" in message_lower:
            return SkillResult.fail("EXECUTION_FAILED", str(message))

        return SkillResult.ok(
            str(message),
            query=query,
            follow_distance_m_requested=follow_distance_m,
            follow_distance_enforced=False,
        )

    @skill
    def stop_person_follow(self) -> SkillResult[AegisError]:
        """Stop an in-progress `follow_person` call.

        Safe to call even if nothing is currently being followed.

        Example:
            stop_person_follow()
        """
        try:
            message = self._person_follow.stop_following()
        except Exception as exc:
            logger.exception("stop_person_follow failed")
            return SkillResult.fail("EXECUTION_FAILED", f"Could not stop following: {exc}")
        return SkillResult.ok(str(message))

    # ------------------------------------------------------------------
    # Skill 8: escort_person / stop_escort
    # ------------------------------------------------------------------

    @skill(uses=[CAP_MOVEMENT], lifecycle="background")
    def escort_person(
        self,
        destination: str,
        standoff_m: float = 1.5,
        timeout_s: float = _DEFAULT_ESCORT_TIMEOUT_S,
    ) -> SkillResult[AegisError]:
        """Confirm a person is present, then navigate to a named destination.

        This is a three-step composition: (1) confirm a person is currently
        visible via `detect_person`, (2) navigate to `destination` using the
        same named-location lookup and navigation interface as
        `go_to_named_location`, (3) report arrival or failure. Runs as a
        background skill (start_tool/tool_update/stop_tool), pushing progress
        as: "confirming person is present", "navigating to <destination>",
        then a final "arrived"/failure update.

        KNOWN LIMITATION -- DimOS has no mechanism to verify the person is
        still following or nearby once the robot starts moving. This skill
        only confirms a person is present *before* departing; it cannot and
        does not check that they stayed with the robot during the walk, and
        does not combine with `follow_person`'s visual tracking while
        navigating. Treat a successful return as "a person was seen, then the
        robot reached the destination" -- not as a guarantee of continuous
        escort. `standoff_m` is accepted for interface compatibility with the
        rest of this skill family but has no effect here (this skill does not
        drive relative to the person at all, unlike `follow_person`).

        Args:
            destination: A location name previously saved with
                `save_named_location`.
            standoff_m: Accepted for interface compatibility. Not enforced --
                see limitation above.
            timeout_s: Give up on the navigation leg after this many seconds.

        Example:
            escort_person("front door")
        """
        destination = destination.strip()
        if not destination:
            return SkillResult.fail("INVALID_INPUT", "destination must not be empty.")
        if standoff_m <= 0:
            return SkillResult.fail("INVALID_INPUT", "standoff_m must be positive.")
        if timeout_s <= 0:
            return SkillResult.fail("INVALID_INPUT", "timeout_s must be positive.")

        self._escort_stop_event.clear()
        self.start_tool("escort_person")

        thread = threading.Thread(
            target=self._escort_loop,
            args=(destination, timeout_s),
            daemon=True,
        )
        self._escort_thread = thread
        thread.start()

        return SkillResult.ok(
            f"Escort to '{destination}' started. Streaming progress updates; "
            "call stop_escort to cancel.",
            destination=destination,
        )

    @skill
    def stop_escort(self) -> SkillResult[AegisError]:
        """Cancel an in-progress `escort_person` call.

        Signals the background escort loop to stop and cancels any
        in-progress navigation goal. Safe to call even if no escort is
        active.

        Example:
            stop_escort()
        """
        self._escort_stop_event.set()
        try:
            self._navigation.cancel_goal()
        except Exception:
            logger.exception("stop_escort: cancel_goal failed")

        thread = self._escort_thread
        if thread is not None:
            thread.join(timeout=5.0)
            self._escort_thread = None

        return SkillResult.ok("Escort cancelled.")

    def _escort_loop(self, destination: str, timeout_s: float) -> None:
        """Background body of escort_person: confirm person, navigate, report.

        Runs in its own thread (mirrors PersonFollowSkillContainer's
        `_follow_loop` idiom: start_tool was already opened by the caller,
        this method is responsible for closing it via stop_tool in every
        exit path).
        """
        try:
            self.tool_update("escort_person", "confirming person is present")
            if self._escort_stop_event.is_set():
                self.tool_update("escort_person", "escort cancelled before starting")
                return

            presence = self.detect_person()
            if not presence.success:
                self.tool_update(
                    "escort_person",
                    f"failed: no person detected before departure ({presence.message})",
                )
                return

            if self._escort_stop_event.is_set():
                self.tool_update("escort_person", "escort cancelled before navigating")
                return

            self.tool_update("escort_person", f"navigating to {destination}")

            location = None
            try:
                location = self._spatial_memory.find_robot_location(destination)
            except Exception as exc:
                logger.exception("escort_person: location lookup failed", name=destination)
                self.tool_update("escort_person", f"failed: location lookup error: {exc}")
                return

            if location is None:
                self.tool_update(
                    "escort_person",
                    f"failed: no named location called '{destination}'.",
                )
                return

            goal = PoseStamped(
                position=make_vector3(*location.position),
                orientation=Quaternion.from_euler(make_vector3(*location.rotation)),
                frame_id="map",
            )

            if not self._navigation.set_goal(goal):
                self.tool_update(
                    "escort_person", f"failed: planner rejected the goal for '{destination}'."
                )
                return

            outcome, elapsed_s = self._wait_for_escort_arrival(timeout_s)
            if outcome == "reached":
                self.tool_update(
                    "escort_person", f"arrived at '{destination}' ({elapsed_s:.1f}s)."
                )
            elif outcome == "timeout":
                self.tool_update(
                    "escort_person",
                    f"failed: did not reach '{destination}' within {timeout_s:.0f}s.",
                )
            elif outcome == "cancelled":
                self.tool_update("escort_person", "escort cancelled during navigation.")
            else:
                self.tool_update(
                    "escort_person", f"failed: navigation to '{destination}' failed."
                )
        finally:
            self.stop_tool("escort_person")

    def _wait_for_escort_arrival(self, timeout_s: float) -> tuple[str, float]:
        """Poll navigation until arrival, cancellation, failure, or timeout.

        Mirrors `LocationSkills._wait_for_arrival` in
        `hackmitdog.aegis.locations` (duplicated here rather than imported --
        these are independent DimOS Modules; small helpers are duplicated per
        module rather than shared via inheritance/cross-import, matching how
        each skill module in this package owns its own copy).
        """
        start = time.monotonic()
        deadline = start + timeout_s
        idle_since: float | None = None

        while time.monotonic() < deadline:
            if self._escort_stop_event.is_set():
                return "cancelled", time.monotonic() - start
            if self._navigation.is_goal_reached():
                return "reached", time.monotonic() - start
            if self._navigation.get_state() == NavigationState.FOLLOWING_PATH:
                idle_since = None
            elif idle_since is None:
                idle_since = time.monotonic()
            elif time.monotonic() - idle_since > _ESCORT_GOAL_SETTLE_S:
                return "failed", time.monotonic() - start
            time.sleep(_ESCORT_GOAL_POLL_INTERVAL_S)

        return "timeout", time.monotonic() - start

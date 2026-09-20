"""Distance-configurable person following.

DimOS's own `PersonFollowSkillContainer` (`dimos.agents.skills.person_follow`)
already performs real distance-aware visual following -- it is not a naive
"keep the person centered" loop. Its two motion controllers,
`VisualServoing2D` (`dimos.navigation.visual_servoing.visual_servoing_2d`,
pinhole-camera bbox-width distance estimation, no depth sensor required) and
`DetectionNavigation` (`dimos.navigation.visual_servoing.detection_navigation`,
real 3D distance from the pointcloud when `use_3d_navigation=True`), both
already compute a genuine metric distance to the tracked person and drive
toward a `_target_distance`/`_target_distance_3d` setpoint (default 1.5 m,
with a `_min_distance`/`_min_distance_3d` backup-off floor of 0.8 m). The gap
this repo had was purely that `PersonFollowSkillContainer` hardcodes those two
constants and exposes no way to configure them per call
(`DIMOS_SKILL_IMPLEMENTATION_PLAN.md` §3/§6 row 7's "known limitation" note).

This module closes that gap withOUT modifying DimOS: `ConfigurableFollowConfig`
extends `PersonFollowSkillContainer.Config` with a `target_distance_m` /
`min_distance_m` field pair, and `ConfigurableFollowSkillContainer` overrides
`__init__` to construct the same `VisualServoing2D`/`DetectionNavigation`
objects DimOS's own container builds, just with those two attributes set from
config instead of left at the hardcoded defaults. Everything else (VL
detection, EdgeTAM tracking, the 20 Hz control loop, capability handling,
lost-track logic) is inherited unchanged from DimOS's implementation -- this
is a thin override of two motion-control constants, not a reimplementation of
person following.
"""

from __future__ import annotations

import functools
from threading import RLock
from typing import Any

from dimos.agents.skills.person_follow import Config as _PersonFollowConfig
from dimos.agents.skills.person_follow import PersonFollowSkillContainer
from dimos.core.core import rpc
from dimos.msgs.geometry_msgs.Twist import Twist
from dimos.msgs.geometry_msgs.Vector3 import make_vector3
from dimos.navigation.visual_servoing.detection_navigation import DetectionNavigation
from dimos.navigation.visual_servoing.visual_servoing_2d import VisualServoing2D
from dimos.utils.logging_config import setup_logger


def _rpc_only(func: Any) -> Any:
    """Re-wrap an inherited `@skill`-decorated method as plain-`@rpc`-only.

    `Module.get_skills()` (`dimos/core/module.py`) discovers MCP-exposed
    tools via `hasattr(getattr(self, name), "__skill__")` on the *bound*
    method actually resolved at runtime, the same late-binding pattern that
    makes `Module.rpcs` require `start`/`set_follow_distance` above to
    re-apply `@rpc` on override. Left alone, this class would inherit
    `PersonFollowSkillContainer.follow_person`/`.stop_following` still
    carrying DimOS's own `__skill__` marker, so BOTH this container and
    `hackmitdog.aegis.person.PersonSkills` would register a same-named
    `follow_person` MCP tool. `McpServer.on_system_modules`
    (`dimos/agents/mcp/mcp_server.py`) flattens every deployed module's
    skills into one `skills_by_name = {s.func_name: s for s in ...}` dict
    with no collision handling -- whichever module is enumerated last wins,
    silently shadowing the other. That is exactly how a live run ended up
    calling DimOS's raw `follow_person` (which falls through to the
    Alibaba-backed VL query path when `initial_bbox` is omitted) instead of
    `PersonSkills.follow_person` (which never touches Alibaba) despite the
    Aegis wrapper existing and working correctly.

    This helper strips `__skill__` (so `get_skills()` skips it -- only
    `PersonSkills`'s wrapper stays MCP-visible) while re-applying `@rpc` (so
    `PersonSkills._person_follow.follow_person(...)`/`.stop_following()`,
    which call this over the RPC layer keyed by `__rpc__` rather than
    through `@skill`, keep working unchanged).
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    # functools.wraps copies func.__dict__ onto wrapper, which would bring
    # DimOS's __skill__/__skill_uses__/__skill_lifecycle__ markers right back
    # -- the whole point of this helper is to NOT have those. Strip them
    # after wraps() runs, then apply plain @rpc.
    for attr in ("__skill__", "__skill_uses__", "__skill_lifecycle__"):
        if hasattr(wrapper, attr):
            delattr(wrapper, attr)

    return rpc(wrapper)

logger = setup_logger()

_DEFAULT_TARGET_DISTANCE_M = 1.5
_DEFAULT_MIN_DISTANCE_M = 0.8


class SmoothedVisualServoing2D(VisualServoing2D):
    """`VisualServoing2D` with a filtered distance estimate and a hold deadband.

    DimOS's own controller is a clean proportional law, but on real hardware
    it produced visibly slow, jittery following. Both symptoms trace to how
    it senses distance, and both are fixed here without touching its control
    math -- `compute_twist` still runs the parent's exact algorithm, just on
    a steadier distance signal and with a "close enough, hold still" band.

    JITTER. The parent estimates distance purely from bounding-box width
    (`_estimate_distance`: `distance = _assumed_object_width * fx /
    bbox_width`, with `_assumed_object_width = 0.45 m`). That is inversely
    proportional to a pixel measurement, so ordinary frame-to-frame tracker
    wobble becomes a large distance swing. Measured against real bboxes from
    this robot's logs (fx=797.5, bbox_width~200px, i.e. ~1.7-1.9 m away), a
    10-pixel wobble moves the estimate by 8-9 cm. Fed unfiltered into a
    proportional controller at 20 Hz, that is a jitter generator -- and it
    gets worse up close, where the box is wider. `_distance_smoothing`
    applies an exponential moving average so a single noisy frame nudges the
    command instead of yanking it.

    SLOWNESS. The parent's forward speed is `distance_error * _linear_gain`
    with no lower bound, so speed decays to zero as it approaches the
    setpoint -- it is slowest exactly where it is asked to settle. With a
    1 m target that dead zone is most of the operating range. Below
    `_hold_deadband_m` of error this class commands zero linear motion
    (deliberately stop, rather than creep), and outside it enforces
    `_min_move_speed` so real corrections happen at a visible pace instead
    of a crawl.

    Angular control is left entirely alone -- turning to keep the person
    centered uses bbox *center*, not width, so it never had the noise
    problem and was not reported as jittery.
    """

    # Weight of each new distance reading in the exponential moving average
    # (0 < a <= 1). Lower = smoother but laggier. 0.3 removes most of the
    # single-frame noise while still tracking a walking person promptly.
    _distance_smoothing: float = 0.3

    # Distance error (m) within which the robot holds position instead of
    # creeping. Sized above the ~8-9 cm single-frame noise measured above,
    # so sensor wobble alone can never command motion.
    _hold_deadband_m: float = 0.15

    # Minimum commanded linear speed (m/s) once outside the deadband, so a
    # real correction moves at a visible pace rather than a crawl.
    _min_move_speed: float = 0.12

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._smoothed_distance: float | None = None

    def reset_distance_filter(self) -> None:
        """Forget the smoothed distance, so the next reading is taken as-is.

        Called when a new follow starts: the previous target's distance must
        not bleed into the new one.
        """
        self._smoothed_distance = None

    def _estimate_distance(self, bbox: tuple[float, float, float, float]) -> float | None:
        raw = super()._estimate_distance(bbox)
        if raw is None:
            # Keep the last smoothed value rather than resetting, so a single
            # dropped/invalid box doesn't restart the filter from scratch.
            return None

        if self._smoothed_distance is None:
            self._smoothed_distance = raw
        else:
            a = self._distance_smoothing
            self._smoothed_distance = a * raw + (1.0 - a) * self._smoothed_distance

        return self._smoothed_distance

    def compute_twist(
        self, bbox: tuple[float, float, float, float], image_width: int
    ) -> Twist:
        twist = super().compute_twist(bbox, image_width)

        # The parent already applied its full control law (including the
        # backup-off branch when closer than _min_distance) using the
        # smoothed distance from _estimate_distance above. Only shape the
        # forward/backward term here; leave angular_z untouched.
        distance = self._smoothed_distance
        if distance is None:
            return twist

        linear_x = twist.linear.x

        # Never suppress a backup command -- being too close is a safety
        # case, and the parent drives it at a fixed speed, not proportionally.
        if distance < self._min_distance:
            return twist

        error = distance - self._target_distance
        if abs(error) <= self._hold_deadband_m:
            # Close enough: hold position instead of hunting around the
            # setpoint, which is what made it stutter in place.
            linear_x = 0.0
        elif 0.0 < abs(linear_x) < self._min_move_speed:
            # Outside the deadband but the proportional term is tiny --
            # move at a visible minimum pace, preserving direction.
            linear_x = self._min_move_speed if linear_x > 0 else -self._min_move_speed

        if linear_x == twist.linear.x:
            return twist

        return Twist(
            linear=make_vector3(linear_x, twist.linear.y, twist.linear.z),
            angular=twist.angular,
        )


class ConfigurableFollowConfig(_PersonFollowConfig):
    """`PersonFollowSkillContainer.Config` plus a configurable standoff distance."""

    target_distance_m: float = _DEFAULT_TARGET_DISTANCE_M
    min_distance_m: float = _DEFAULT_MIN_DISTANCE_M


class ConfigurableFollowSkillContainer(PersonFollowSkillContainer):
    """`PersonFollowSkillContainer` with a real, configurable standoff distance.

    Identical to DimOS's own container in every other respect (same VL
    detection, same EdgeTAM tracker, same 20 Hz loop, same capability
    handling) -- only two things differ:

    1. The distance-control constants on the underlying `VisualServoing2D`/
       `DetectionNavigation` objects are overridden here, from
       `config.target_distance_m`/`config.min_distance_m` instead of DimOS's
       hardcoded 1.5 m / 0.8 m.
    2. `follow_person`/`stop_following` are inherited as plain RPC methods
       ONLY, not MCP-exposed `@skill`s (see `_rpc_only`) -- this module is
       deployed purely as `hackmitdog.aegis.person.PersonSkills`'s internal
       `_person_follow` dependency, and must never be independently
       agent-callable, or its inherited `follow_person` (which falls back to
       an Alibaba-backed VL query when called without `initial_bbox`) would
       collide with and potentially shadow `PersonSkills.follow_person`
       (which never does) in `McpServer`'s flat `skills_by_name` dict.
    """

    config: ConfigurableFollowConfig

    # De-skill DimOS's inherited `follow_person`/`stop_following` -- see
    # `_rpc_only`'s docstring above. These stay callable exactly as before
    # from `PersonSkills` (which uses them as plain RPC calls), they just
    # stop being independently registered as MCP tools, so the agent only
    # ever sees one `follow_person` (the Aegis wrapper in `person.py`, which
    # never requires ALIBABA_API_KEY).
    stop_following = _rpc_only(PersonFollowSkillContainer.stop_following)

    @rpc
    def follow_person(  # type: ignore[override]
        self,
        query: str,
        initial_bbox: list[float] | None = None,
        initial_image: str | None = None,
    ) -> str:
        """Start following, marking follow state and resetting the distance filter.

        Plain `@rpc`, never `@skill` -- see `_rpc_only`'s docstring for why
        this must not be independently MCP-exposed. (Declared directly
        rather than via `_rpc_only` because it needs real behavior of its
        own before delegating.)
        """
        # A previous target's smoothed distance must not carry into a new
        # follow, or the first few commands chase a stale estimate.
        self._visual_servo.reset_distance_filter()

        with self._follow_state_lock:
            self._following = True
            self._last_stop_reason = None

        try:
            return str(
                super().follow_person(
                    query=query,
                    initial_bbox=initial_bbox,
                    initial_image=initial_image,
                )
            )
        except Exception:
            # Never leave _following stuck True if starting threw.
            with self._follow_state_lock:
                self._following = False
            raise

    def _send_stop_reason(self, query: str, reason: str) -> None:
        """Record that the follow ended, so another module can observe it.

        `_send_stop_reason` is the single funnel every way a follow can end
        goes through -- an explicit `stop_following`, losing track of the
        person (`_max_lost_frames` exceeded), or a 3D-navigation failure.
        DimOS's version closes only THIS module's tool stream, releasing
        only this module's capability token.

        `hackmitdog.aegis.person.PersonSkills.follow_person` holds the
        `movement` capability under its OWN token (see its docstring), so it
        must learn when a follow ends for any reason -- otherwise a follow
        that ends by itself (the person walks away) strands `movement` held
        forever, exactly as an explicit stop used to.

        This is recorded as plain state rather than delivered via a
        callback: `PersonSkills` runs in a *different worker process* (its
        access to this module is an RPC proxy), so a Python callable cannot
        be handed across. `is_following()` below is what it polls.
        """
        with self._follow_state_lock:
            self._following = False
            self._last_stop_reason = reason
        super()._send_stop_reason(query, reason)

    @rpc
    def is_following(self) -> bool:
        """True while a follow is active; False once it has ended, for any reason.

        Polled by `PersonSkills` so it can close its own tool stream (and
        release `movement`) when a follow ends on its own rather than by an
        explicit `stop_person_follow`.
        """
        with self._follow_state_lock:
            return self._following

    @rpc
    def last_stop_reason(self) -> str | None:
        """Why the most recent follow ended, or None if none has ended yet."""
        with self._follow_state_lock:
            return self._last_stop_reason

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Observable follow state, polled cross-process via is_following()
        # -- see _send_stop_reason's docstring for why this isn't a callback.
        self._follow_state_lock = RLock()
        self._following = False
        self._last_stop_reason: str | None = None

        target = self.config.target_distance_m
        floor = self.config.min_distance_m
        if floor >= target:
            logger.warning(
                "min_distance_m >= target_distance_m; clamping min_distance_m "
                "to half of target_distance_m",
                target_distance_m=target,
                min_distance_m=floor,
            )
            floor = target / 2.0

        # Replace the parent's plain VisualServoing2D with the smoothed
        # variant (see SmoothedVisualServoing2D: filtered distance estimate,
        # hold deadband, minimum move speed -- fixes the slow, jittery
        # following seen on hardware). Rebuilt with the same constructor
        # args the parent used, so the camera_info/simulation-mode logic it
        # already resolved is preserved exactly.
        self._visual_servo = SmoothedVisualServoing2D(
            self._camera_info, bool(self.config.g.simulation)
        )
        self._visual_servo._target_distance = target
        self._visual_servo._min_distance = floor

        self._follow_target_distance_m = target
        self._follow_min_distance_m = floor

    def _rebuild_3d_navigation_distances(self) -> None:
        """Apply the configured distances to `_detection_navigation`.

        `_detection_navigation` (`DetectionNavigation`) is constructed in the
        parent's `start()`, not `__init__` (it needs `self.tfbuffer`, which
        isn't ready until the module starts) -- so this can't run in
        `__init__` and must be called after `super().start()`.
        """
        nav: DetectionNavigation | None = getattr(self, "_detection_navigation", None)
        if nav is not None:
            nav._target_distance_3d = self._follow_target_distance_m
            nav._min_distance_3d = self._follow_min_distance_m

    @rpc
    def start(self) -> None:  # type: ignore[override]
        # Must re-apply @rpc here: `Module.rpcs` discovers RPC-callable
        # methods via `hasattr(getattr(self, name), "__rpc__")` on the bound
        # method actually resolved at runtime -- since this override shadows
        # the parent's `@rpc`-decorated `start`, the parent's decoration
        # doesn't carry over and `start` would silently stop being callable
        # as an RPC without this.
        super().start()
        self._rebuild_3d_navigation_distances()

    @rpc
    def set_follow_distance(
        self, target_distance_m: float, min_distance_m: float | None = None
    ) -> bool:
        """Change the standoff distance this container follows at, live.

        Plain `@rpc` (not `@skill`) -- called internally by
        `hackmitdog.aegis.person.PersonSkills.follow_person` right before
        starting a follow, so a caller can request a different distance per
        call rather than only the one fixed at blueprint-launch time via
        `--target-distance-m`/`--min-distance-m`. Safe to call whether or not
        a follow is currently active: it updates the live `VisualServoing2D`/
        `DetectionNavigation` objects in place, so a change mid-follow takes
        effect on the very next control-loop tick.

        Args:
            target_distance_m: New standoff distance to hold, in meters. Must
                be positive.
            min_distance_m: New backup-off floor, in meters. Defaults to
                keeping whatever floor is already set if omitted.

        Returns:
            True if applied, False if `target_distance_m` was invalid (the
            distances are left unchanged in that case).
        """
        if target_distance_m <= 0:
            logger.warning(
                "set_follow_distance: ignoring non-positive target_distance_m",
                target_distance_m=target_distance_m,
            )
            return False

        floor = self._follow_min_distance_m if min_distance_m is None else min_distance_m
        if floor >= target_distance_m:
            floor = target_distance_m / 2.0

        self._visual_servo._target_distance = target_distance_m
        self._visual_servo._min_distance = floor
        self._follow_target_distance_m = target_distance_m
        self._follow_min_distance_m = floor
        self._rebuild_3d_navigation_distances()
        return True

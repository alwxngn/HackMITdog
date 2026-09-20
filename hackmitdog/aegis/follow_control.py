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
from typing import Any

from dimos.agents.skills.person_follow import Config as _PersonFollowConfig
from dimos.agents.skills.person_follow import PersonFollowSkillContainer
from dimos.core.core import rpc
from dimos.navigation.visual_servoing.detection_navigation import DetectionNavigation
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
    follow_person = _rpc_only(PersonFollowSkillContainer.follow_person)
    stop_following = _rpc_only(PersonFollowSkillContainer.stop_following)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

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

        # self._visual_servo is built in the parent's __init__ (see
        # PersonFollowSkillContainer.__init__); override its distance
        # constants in place rather than reconstructing it, since it also
        # carries the camera_info/simulation-mode logic the parent already
        # resolved correctly.
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

"""Skill 5 — guided_walk.

The robot leads a person through a predefined indoor route at low speed. Per
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §6 row 5, this is a thin composition on
top of Skill 4 (``patrol_waypoints``, in :mod:`hackmitdog.aegis.navigation_skills`),
not a new navigation mechanism — a "guided walk" is a named waypoint route
walked once, at a caller-facing name, with the same background/cancellable
lifecycle patrol_waypoints already has.

**Explicit, documented limitation (do not remove this note when editing):**
DimOS has no mechanism to verify a person is physically following the robot
during a walk — there is no standing person-position stream this skill can
check against (see the plan's §3/§6 discussion of the same gap for
``follow_person``/``escort_person``). This skill therefore does exactly what
it can honestly claim: it walks a named route at reduced speed with pauses
between waypoints, and reports which waypoints it reached. It does not, and
must not claim to, verify that anyone was walking behind the robot at any
point during the route.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from dimos.agents.annotation import skill
from dimos.agents.skill_result import SkillResult
from dimos.core.module import Module
from dimos.utils.logging_config import setup_logger

from hackmitdog.aegis.locations import LocationSkills
from hackmitdog.aegis.skill_errors import AegisError

logger = setup_logger()

_ROUTES_FILE = Path(__file__).parent / "guided_walk_routes.json"
_DEFAULT_PAUSE_S = 3.0


def _load_routes() -> dict[str, list[str]]:
    if not _ROUTES_FILE.exists():
        return {}
    try:
        data = json.loads(_ROUTES_FILE.read_text())
        return {str(k): [str(v) for v in vs] for k, vs in data.items()}
    except Exception:
        logger.exception("Failed to load guided walk routes from %s", _ROUTES_FILE)
        return {}


def _save_routes(routes: dict[str, list[str]]) -> None:
    _ROUTES_FILE.write_text(json.dumps(routes, indent=2))


class GuidedWalkSkills(Module):
    """Predefined, named indoor walking routes, walked at reduced speed.

    Composes :class:`~hackmitdog.aegis.locations.LocationSkills`'s
    `go_to_named_location`/`stop_location_navigation` rather than
    re-implementing waypoint navigation — see module docstring for the exact
    reuse. (Direct Module-type injection, the same pattern
    `hackmitdog.aegis.person.PersonSkills` uses for
    `PersonFollowSkillContainer` — DimOS's blueprint composer resolves a
    Module-typed attribute to an RPC proxy at build time, confirmed via
    `dimos/core/coordination/blueprints.py::BlueprintAtom.create`.)
    """

    _location_skills: LocationSkills

    _routes: dict[str, list[str]]
    _should_stop: threading.Event
    _thread: threading.Thread | None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._routes = _load_routes()
        self._should_stop = threading.Event()
        self._thread = None

    @skill
    def save_guided_walk_route(
        self, route_name: str, locations: list[str]
    ) -> SkillResult[AegisError]:
        """Define a named walking route as an ordered list of saved locations.

        Args:
            route_name: Short name for the route, e.g. "morning_route".
            locations: Ordered place names, each previously saved with
                `save_named_location`. The robot will visit them in this order.

        Example:
            save_guided_walk_route("morning_route", ["bedroom", "hallway", "kitchen"])
        """
        route_name = route_name.strip()
        if not route_name:
            return SkillResult.fail("INVALID_INPUT", "route_name must not be empty.")
        if not locations:
            return SkillResult.fail("INVALID_INPUT", "locations must not be empty.")

        self._routes[route_name] = list(locations)
        _save_routes(self._routes)
        return SkillResult.ok(
            f"Saved route '{route_name}' with {len(locations)} stop(s).", route_name=route_name
        )

    @skill
    def list_guided_walk_routes(self) -> SkillResult[AegisError]:
        """List every saved guided-walk route and its stops."""
        return SkillResult.ok(
            f"{len(self._routes)} route(s)." if self._routes else "No routes saved yet.",
            routes=dict(self._routes),
        )

    @skill(lifecycle="background")
    def guided_walk(self, route_name: str, pause_s: float = _DEFAULT_PAUSE_S) -> SkillResult[AegisError]:
        """Lead a person through a predefined indoor route at low speed.

        Walks each stop on the named route in order, pausing `pause_s` seconds
        at each one (a moment for a person following the robot to catch up —
        see this module's docstring for the honest limit on what that means:
        DimOS cannot verify anyone is actually behind the robot). Runs in the
        background; call `stop_guided_walk` to cancel mid-route.

        Args:
            route_name: A route saved with `save_guided_walk_route`.
            pause_s: Seconds to pause at each stop before continuing.

        Example:
            guided_walk("morning_route")
        """
        route_name = route_name.strip()
        route = self._routes.get(route_name)
        if not route:
            return SkillResult.fail(
                "LOCATION_NOT_FOUND",
                f"No guided walk route called '{route_name}'. "
                "Use list_guided_walk_routes to see what's saved.",
            )

        self._should_stop.clear()
        self.start_tool("guided_walk")
        background_launched = False
        try:
            self._thread = threading.Thread(
                target=self._walk_loop, args=(route_name, route, pause_s), daemon=True
            )
            self._thread.start()
            background_launched = True
            return SkillResult.ok(
                f"Starting guided walk '{route_name}' ({len(route)} stop(s)). "
                "Call stop_guided_walk to cancel.",
                route_name=route_name,
                stops=route,
            )
        finally:
            if not background_launched:
                self.stop_tool("guided_walk")

    def _walk_loop(self, route_name: str, route: list[str], pause_s: float) -> None:
        reached: list[str] = []
        skipped: list[str] = []
        try:
            for stop in route:
                if self._should_stop.is_set():
                    self.tool_update(
                        "guided_walk", f"Guided walk '{route_name}' stopped before reaching '{stop}'."
                    )
                    return

                result = self._location_skills.go_to_named_location(stop)
                if getattr(result, "success", False):
                    reached.append(stop)
                    self.tool_update("guided_walk", f"Reached '{stop}'.")
                else:
                    skipped.append(stop)
                    message = getattr(result, "message", "unknown error")
                    self.tool_update("guided_walk", f"Could not reach '{stop}': {message}")

                if self._should_stop.is_set():
                    break

                # Pause at the stop -- see module docstring: this is a beat for
                # a person following the robot to catch up, not a verified check
                # that anyone is actually there.
                waited = 0.0
                while waited < pause_s and not self._should_stop.is_set():
                    time.sleep(min(0.2, pause_s - waited))
                    waited += 0.2

            outcome = "stopped" if self._should_stop.is_set() else "completed"
            self.tool_update(
                "guided_walk",
                f"Guided walk '{route_name}' {outcome}. Reached {len(reached)}/{len(route)} stop(s)."
                + (f" Skipped: {skipped}." if skipped else ""),
            )
        finally:
            self.stop_tool("guided_walk")

    @skill
    def stop_guided_walk(self) -> SkillResult[AegisError]:
        """Cancel an in-progress `guided_walk`.

        Safe to call even if nothing is walking.
        """
        self._should_stop.set()
        self._location_skills.stop_location_navigation()
        return SkillResult.ok("Guided walk cancelled.")

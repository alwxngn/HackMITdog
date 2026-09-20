"""Pure decision core for the controller-level 1.2 m yield reflex.

This module does not command motors.  It is deliberately dependency-free so
the threshold, stale-sensor behavior, latch, and rear-clearance rules can be
tested before wiring them to DimOS's live LiDAR and velocity streams.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class YieldAction(str, Enum):
    CLEAR = "clear"
    STOP = "stop"
    RETREAT = "retreat"


@dataclass
class YieldPolicy:
    trigger_m: float = 1.2
    release_m: float = 1.4
    rear_clearance_m: float = 0.6
    max_sample_age_s: float = 0.25
    latched: bool = False

    def decide(
        self,
        *,
        front_min_m: float | None,
        rear_min_m: float | None,
        sample_age_s: float,
    ) -> YieldAction:
        """Return the motor override required by the latest raw range sample.

        Missing/stale data fails safe to STOP.  Once triggered, the reflex
        remains latched until the front clearance exceeds ``release_m``;
        this hysteresis prevents noisy measurements around 1.2 m from rapidly
        toggling motion on and off.
        """

        if (
            front_min_m is None
            or rear_min_m is None
            or sample_age_s < 0
            or sample_age_s > self.max_sample_age_s
        ):
            self.latched = True
            return YieldAction.STOP

        if front_min_m < self.trigger_m:
            self.latched = True
        elif self.latched and front_min_m >= self.release_m:
            self.latched = False

        if not self.latched:
            return YieldAction.CLEAR
        if rear_min_m >= self.rear_clearance_m:
            return YieldAction.RETREAT
        return YieldAction.STOP

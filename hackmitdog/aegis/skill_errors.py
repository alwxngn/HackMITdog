"""Aegis-domain failure codes for ``SkillResult``.

Cross-domain codes (``ROBOT_NOT_FOUND``, ``INVALID_INPUT``, ``EXECUTION_FAILED``,
``EXECUTION_TIMEOUT``, ...) live in ``dimos.agents.skill_result.CommonSkillError``
(see ``dimos/agents/skill_result.py``). This module owns codes specific to the
Aegis companion skills, following the same convention as e.g.
``dimos.manipulation.skill_errors``.
"""

from typing import Literal

from dimos.agents.skill_result import CommonSkillError

AegisError = Literal[
    CommonSkillError,
    "LOCATION_NOT_FOUND",  # named location/object has no memory record
    "PERSON_NOT_FOUND",  # no person detected in the current view
    "PERSON_LOST",  # a follow/escort lost track of the person mid-behavior
    "OBSTACLE_TOO_CLOSE",  # started already closer than the requested target distance
    "MAX_DISTANCE_EXCEEDED",  # a bounded move hit its distance cap before finishing
    "ZONE_NOT_FOUND",  # named danger zone has no record
    "ALREADY_RUNNING",  # a background skill was asked to start while already active
    "NOT_RUNNING",  # a stop/status skill was called with nothing active
]

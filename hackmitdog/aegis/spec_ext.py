"""Extended DimOS specs used by this package's skills.

``dimos.perception.experimental.spatial_memory_spec.SpatialMemorySpec`` only
exposes ``tag_location`` / ``query_tagged_location`` / ``query_by_text``. The
concrete module behind it, ``SpatialMemory``
(``dimos.perception.experimental.spatial_perception``), implements a wider
``@rpc`` surface — ``add_named_location``, ``find_robot_location``,
``get_robot_locations`` — that the narrow spec doesn't declare (see
``DIMOS_SKILL_IMPLEMENTATION_PLAN.md`` §3).

DimOS specs are plain structural ``Protocol``s (``dimos/spec/utils.py``:
``is_spec``/``spec_structural_compliance`` do a runtime-checkable structural
match, nothing more) — so declaring a wider ``Protocol`` here that a running
``SpatialMemory`` instance already structurally satisfies is a safe, additive
extension. It does not modify DimOS; it only describes more of what's already
there. If DimOS later widens ``SpatialMemorySpec`` itself, this local
extension becomes redundant and can be deleted.
"""

from __future__ import annotations

from typing import Protocol

from dimos.perception.experimental.spatial_memory_spec import SpatialMemorySpec
from dimos.spec.utils import Spec
from dimos.types.robot_location import RobotLocation


class ExtendedSpatialMemorySpec(SpatialMemorySpec, Spec, Protocol):
    """``SpatialMemorySpec`` plus the named-location CRUD methods DimOS's
    concrete ``SpatialMemory`` module already implements but doesn't declare
    on the narrow spec."""

    def add_named_location(
        self,
        name: str,
        position: list[float] | None = None,
        rotation: list[float] | None = None,
        description: str | None = None,
    ) -> bool: ...

    def find_robot_location(self, name: str) -> RobotLocation | None: ...

    def get_robot_locations(self) -> list[RobotLocation]: ...

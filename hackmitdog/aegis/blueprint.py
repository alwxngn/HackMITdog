"""Aegis skill blueprint — composes every skill module in this package onto a
running Go2, following the exact pattern DimOS's own
``dimos.robot.unitree.go2.blueprints.agentic._common_agentic`` uses to compose
`NavigationSkillContainer`, `ObserveSkill`, `PersonFollowSkillContainer`,
`UnitreeSkillContainer`, `WebInput`, and `SpeakSkill` onto `unitree_go2_spatial`.

Run with:

    dimos run hackmitdog.aegis-go2

(the ``dimos.blueprints`` entry point below; see this repo's ``pyproject.toml``).

Or compose it yourself into a different base, e.g. with the Ollama MCP client
DimOS already ships for small local models (see
``dimos.robot.unitree.go2.blueprints.agentic.unitree_go2_agentic_ollama`` for
the reference)::

    from dimos.agents.mcp.mcp_client import McpClient
    from dimos.agents.mcp.mcp_server import McpServer
    from dimos.core.coordination.blueprints import autoconnect
    from hackmitdog.aegis.blueprint import aegis_go2_skills

    aegis_go2_agentic_ollama = autoconnect(
        aegis_go2_skills,
        McpServer.blueprint(),
        McpClient.blueprint(model="ollama:qwen3:8b"),
    )
"""

from dimos.core.coordination.blueprints import autoconnect
from dimos.robot.unitree.go2.blueprints.smart.unitree_go2_spatial import (
    unitree_go2_spatial,
)

from hackmitdog.aegis.danger_zone import DangerZoneSkills
from hackmitdog.aegis.guided_walk import GuidedWalkSkills
from hackmitdog.aegis.home import HomeSkills
from hackmitdog.aegis.locations import LocationSkills
from hackmitdog.aegis.navigation_skills import NavigationSkills
from hackmitdog.aegis.object_memory import ObjectMemorySkills
from hackmitdog.aegis.person import PersonSkills

# All fourteen Aegis skills, composed onto the existing DimOS Go2 navigation +
# spatial-memory stack (unitree_go2_spatial already carries GO2Connection,
# VoxelGridMapper, CostMapper, ReplanningAStarPlanner, PatrollingModule,
# MovementManager, SpatialMemory, PerceiveLoopSkill -- see
# DIMOS_SKILL_IMPLEMENTATION_PLAN.md §5). This blueprint adds no new DimOS
# modules, only this package's own skill containers.
aegis_go2_skills = autoconnect(
    unitree_go2_spatial,
    LocationSkills.blueprint(),
    NavigationSkills.blueprint(),
    GuidedWalkSkills.blueprint(),
    PersonSkills.blueprint(),
    ObjectMemorySkills.blueprint(),
    HomeSkills.blueprint(),
    DangerZoneSkills.blueprint(),
).global_config(n_workers=12)

"""Aegis skill blueprint — composes every skill module in this package onto a
running Go2, following the exact pattern DimOS's own
``dimos.robot.unitree.go2.blueprints.agentic._common_agentic`` uses to compose
`NavigationSkillContainer`, `ObserveSkill`, `PersonFollowSkillContainer`,
`UnitreeSkillContainer`, `WebInput`, and `SpeakSkill` onto `unitree_go2_spatial`.

Two runnable blueprints (both registered as ``dimos.blueprints`` entry points,
see this repo's ``pyproject.toml``):

    dimos run hackmitdog.aegis-go2                 # skills only, call them
                                                    # directly via `dimos mcp call`
    dimos run hackmitdog.aegis-go2-ollama --listen-host 0.0.0.0
                                                    # + a local Ollama-backed
                                                    # agent that can plan across
                                                    # skills on its own, reachable
                                                    # over the LAN (see the
                                                    # `--listen-host` note below)

``aegis_go2_agentic_ollama`` mirrors
``dimos.robot.unitree.go2.blueprints.agentic.unitree_go2_agentic_ollama``
exactly: same ``McpServer``/``McpClient(model="ollama:qwen3:8b")`` pair DimOS's
own agentic Go2 blueprints use, just pointed at this package's skills instead
of (or alongside) DimOS's built-in ones. Requires a running Ollama daemon
(``ollama serve``) with the model pulled (``ollama pull qwen3:8b``) on
whichever machine runs ``dimos`` -- ``ollama_installed()`` is declared as a
requirement so ``dimos run`` refuses early with a clear message if it isn't.

**Reachable over wifi**: ``McpServer`` binds to ``GlobalConfig.listen_host``
(default ``127.0.0.1``, i.e. localhost-only) and ``GlobalConfig.mcp_port``
(default ``9990``). Pass ``--listen-host 0.0.0.0`` on `dimos run` to make it
reachable from another device on the same network, then point that device's
`dimos mcp` calls (or an `McpAdapter`) at ``http://<this-machine's-LAN-ip>:9990``.
"""

from dimos.agents.mcp.mcp_client import McpClient
from dimos.agents.mcp.mcp_server import McpServer
from dimos.agents.ollama_agent import ollama_installed
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

# Same skills, plus an MCP server/client pair backed by a local Ollama model --
# the same small-LLM configuration DimOS's own unitree_go2_agentic_ollama uses
# (dimos/robot/unitree/go2/blueprints/agentic/unitree_go2_agentic_ollama.py).
# This is the one to run if you want the robot to plan across skills on its
# own rather than being driven one `dimos mcp call` at a time.
aegis_go2_agentic_ollama = autoconnect(
    aegis_go2_skills,
    McpServer.blueprint(),
    McpClient.blueprint(model="ollama:qwen3:8b"),
).requirements(
    ollama_installed,
)

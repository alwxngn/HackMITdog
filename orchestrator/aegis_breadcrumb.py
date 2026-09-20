"""Combined real-Go2 Aegis and breadcrumb DimOS blueprint.

This intentionally composes the skill modules onto one Go2 spatial stack and
one MCP server/client pair.  Do not compose the two complete agentic
blueprints together: doing so would duplicate the Go2 connection and MCP
infrastructure in the same DimOS process.
"""

from dimos.agents.mcp.mcp_client import McpClient
from dimos.agents.mcp.mcp_server import McpServer
from dimos.core.coordination.blueprints import autoconnect
from dimos.perception.experimental.perceive_loop_skill import PerceiveLoopSkill
from dimos.robot.unitree.unitree_skill_container import UnitreeSkillContainer

from hackmitdog.aegis.blueprint import aegis_go2_skills
from orchestrator.breadcrumb import BreadcrumbRecorder


# Deterministic runtime: MCP tools are available to the external command
# bridge, but no LLM client is started. The perception loop is agent-only and
# requires AgentSpec, so it is disabled here.
aegis_breadcrumb = autoconnect(
    aegis_go2_skills.disabled_modules(PerceiveLoopSkill),
    UnitreeSkillContainer.blueprint(),
    BreadcrumbRecorder.blueprint(),
    McpServer.blueprint(),
)


# Aegis supplies the shared Go2 navigation/spatial stack and all Aegis skill
# modules. BreadcrumbRecorder adds its separate, non-conflicting MCP tools.
# McpServer/McpClient are added exactly once for the unified tool surface.
aegis_breadcrumb_agentic = autoconnect(
    aegis_go2_skills,
    BreadcrumbRecorder.blueprint(),
    McpServer.blueprint(),
    McpClient.blueprint(),
)

from __future__ import annotations

from dimos.agents.mcp.mcp_client import McpClient
from dimos.agents.skills.speak_skill import SpeakSkill
from dimos.core.coordination.blueprints import autoconnect
from dimos.core.coordination.module_coordinator import ModuleCoordinator
from dimos.robot.unitree.go2.blueprints.agentic.unitree_go2_agentic_ollama import (
    unitree_go2_agentic_ollama,
)

from hackmitdog.aegis.danger_zone import DangerZoneSkills
from hackmitdog.aegis.home import HomeSkills
from hackmitdog.aegis.locations import LocationSkills
from orchestrator.breadcrumb import BreadcrumbRecorder


# Simulation-safe composition for end-to-end safety testing:
# - proven agentic+MCP base (unitree_go2_agentic_ollama)
# - breadcrumb "take me home" flow
# - danger-zone monitoring/intercept tools
# - named home/location tools for return_to_home
safety_agentic_sim = autoconnect(
    unitree_go2_agentic_ollama.disabled_modules(SpeakSkill, McpClient),
    BreadcrumbRecorder.blueprint(),
    LocationSkills.blueprint(),
    HomeSkills.blueprint(),
    DangerZoneSkills.blueprint(),
).global_config(simulation="mujoco")


if __name__ == "__main__":
    ModuleCoordinator.build(safety_agentic_sim).loop()

"""Aegis skill blueprint — composes every skill module in this package onto a
running Go2, following the exact pattern DimOS's own
``dimos.robot.unitree.go2.blueprints.agentic._common_agentic`` uses to compose
`NavigationSkillContainer`, `ObserveSkill`, `PersonFollowSkillContainer`,
`UnitreeSkillContainer`, `WebInput`, and `SpeakSkill` onto `unitree_go2_spatial`.

Three runnable blueprints (all registered as ``dimos.blueprints`` entry points,
see this repo's ``pyproject.toml``):

    dimos run hackmitdog.aegis-go2                 # skills only, call them
                                                    # directly via `dimos mcp call`
    dimos run hackmitdog.aegis-go2-agentic
                                                    # + an agent backed by a
                                                    # hosted LLM (OpenAI/
                                                    # Anthropic/etc via
                                                    # LangChain's
                                                    # init_chat_model) -- reads
                                                    # its API key from the
                                                    # provider's normal env var
                                                    # (e.g. OPENAI_API_KEY),
                                                    # nothing DimOS-specific to
                                                    # export
    dimos run hackmitdog.aegis-go2-ollama --listen-host 0.0.0.0
                                                    # + a local Ollama-backed
                                                    # agent instead, reachable
                                                    # over the LAN (see the
                                                    # `--listen-host` note below)

``aegis_go2_agentic`` mirrors DimOS's own
``dimos.robot.unitree.go2.blueprints.agentic.unitree_go2_agentic`` exactly:
``McpServer``/``McpClient()`` with no ``model=`` override, so it takes
``McpClientConfig``'s own default (``"gpt-5.6-luna"``, a hosted model resolved
through LangChain's ``init_chat_model`` -- any LangChain-supported provider
string works, e.g. ``--model "anthropic:claude-sonnet-5"``, as long as that
provider's API key is exported in the environment already). Use this one if
you already have a hosted LLM API key rather than running Ollama locally.

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
from dimos.robot.unitree.go2.connection import GO2Connection

from hackmitdog.aegis import mps_worker_fix

# Must run before `dimos run` starts any worker process. On macOS this
# switches DimOS's module workers from forkserver to spawn, without which
# Metal/MPS shader compilation fails inside every worker and `follow_person`
# cannot start its EdgeTAM tracker at all. No-op on other platforms. See
# hackmitdog/aegis/mps_worker_fix.py for the full explanation and the
# measurements behind it.
mps_worker_fix.apply()

from hackmitdog.aegis.danger_zone import DangerZoneSkills
from hackmitdog.aegis.follow_control import ConfigurableFollowSkillContainer
from hackmitdog.aegis.guided_walk import GuidedWalkSkills
from hackmitdog.aegis.home import HomeSkills
from hackmitdog.aegis.locations import LocationSkills
from hackmitdog.aegis.map_skill import MapRoomSkills
from hackmitdog.aegis.navigation_skills import NavigationSkills
from hackmitdog.aegis.object_memory import ObjectMemorySkills
from hackmitdog.aegis.person import PersonSkills

# All fourteen Aegis skills, composed onto the existing DimOS Go2 navigation +
# spatial-memory stack (unitree_go2_spatial already carries GO2Connection,
# VoxelGridMapper, CostMapper, ReplanningAStarPlanner, PatrollingModule,
# MovementManager, SpatialMemory, PerceiveLoopSkill -- see
# DIMOS_SKILL_IMPLEMENTATION_PLAN.md §5). This blueprint deploys
# ConfigurableFollowSkillContainer (hackmitdog.aegis.follow_control), a thin
# PersonFollowSkillContainer subclass with a real, configurable standoff
# distance -- see that module's docstring. PersonSkills.follow_person/
# stop_person_follow only inject an RPC proxy typed as the DimOS base class
# (`_person_follow: PersonFollowSkillContainer`); DimOS's own module-ref
# resolution (`_resolve_single_ref.satisfies`, module_coordinator.py) matches
# by `issubclass`, so a subclass instance correctly satisfies that ref with no
# changes needed in person.py. Without *some* PersonFollowSkillContainer (or
# subclass) in this autoconnect(...) call, that proxy resolves to None at
# runtime -- confirmed the hard way once already ("'NoneType' object has no
# attribute 'follow_person'"/"'stop_following'"), so don't remove this line.
# camera_info=GO2Connection.camera_info_static matches the exact invocation
# DimOS's own _common_agentic.py uses for the stock container.
#
# ConfigurableFollowSkillContainer itself contributes ZERO MCP-exposed tools
# (see follow_control.py's _rpc_only) -- its follow_person/stop_following are
# de-skilled on purpose. Confirmed the hard way once already: with them left
# as inherited @skill methods, McpServer.on_system_modules flattened both
# PersonSkills.follow_person and ConfigurableFollowSkillContainer.follow_person
# into one skills_by_name dict keyed by function name with no collision
# handling, and the agent ended up calling DimOS's raw one -- which falls back
# to an Alibaba-backed VL query whenever it's called without initial_bbox,
# defeating the entire point of PersonSkills.follow_person's Alibaba-free
# local-YOLO wrapper. Do not remove _rpc_only's stripping without also solving
# that collision some other way.
aegis_go2_skills = autoconnect(
    unitree_go2_spatial,
    LocationSkills.blueprint(),
    NavigationSkills.blueprint(),
    GuidedWalkSkills.blueprint(),
    PersonSkills.blueprint(),
    ConfigurableFollowSkillContainer.blueprint(
        camera_info=GO2Connection.camera_info_static,
    ),
    ObjectMemorySkills.blueprint(),
    HomeSkills.blueprint(),
    DangerZoneSkills.blueprint(),
    MapRoomSkills.blueprint(),
).global_config(n_workers=12)

# Same skills, plus an MCP server/client pair backed by a hosted LLM (whatever
# McpClientConfig.model defaults to, or whatever --model override is passed on
# `dimos run` -- resolved via LangChain's init_chat_model, so it reads its API
# key from that provider's normal env var, e.g. OPENAI_API_KEY). Mirrors
# DimOS's own unitree_go2_agentic
# (dimos/robot/unitree/go2/blueprints/agentic/unitree_go2_agentic.py) exactly.
aegis_go2_agentic = autoconnect(
    aegis_go2_skills,
    McpServer.blueprint(),
    McpClient.blueprint(),
)

# Same skills, plus an MCP server/client pair backed by a local Ollama model --
# the same small-LLM configuration DimOS's own unitree_go2_agentic_ollama uses
# (dimos/robot/unitree/go2/blueprints/agentic/unitree_go2_agentic_ollama.py).
# This is the one to run if you want the robot to plan across skills on its
# own without a hosted API key.
aegis_go2_agentic_ollama = autoconnect(
    aegis_go2_skills,
    McpServer.blueprint(),
    McpClient.blueprint(model="ollama:qwen3:8b"),
).requirements(
    ollama_installed,
)

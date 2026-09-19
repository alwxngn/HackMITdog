# DimOS skill implementation plan — Aegis/Lantern Go2 companion skills

**Status:** Phase 1 (investigation) complete, including a revision pass after deeper investigation
of perception/detection and spatial-memory internals corrected two items in an earlier draft (see
§3 and the "resolved" notes in §9). This plan is based on reading the actual installed DimOS
source, not on assumption.

## 0. Where things actually live

**This repo (`HackMITdog`) is not DimOS.** It is the planning repo for a HackMIT project
(product name **Lantern**, code name in this task's brief was "Aegis") — see `README.md` and
`docs/`. It currently contains one stub module (`hackmitdog/behaviors.py`) registered as a DimOS
blueprint entry point:

```toml
[project.entry-points."dimos.blueprints"]
behaviors = "hackmitdog.behaviors:DogBehaviors"
```

**DimOS itself is a separately installed package**, not vendored into this repo:

```
/Users/laminegueye/dimensional-applications/.venv/lib/python3.12/site-packages/dimos   (v0.0.14)
```

Everything below cites real files at that path. Run `dimos` commands from that venv
(`source /Users/laminegueye/dimensional-applications/.venv/bin/activate`, or call the venv's
`dimos` binary directly), from a working directory where `hackmitdog` is installed
(`pip install -e .` from this repo, into that venv, so the entry point is discoverable).

**Note on scope vs. this repo's other docs:** `docs/02-blueprint.md`, `docs/04-interfaces.md`,
`docs/06-safety-ethics.md`, and `docs/11-perception.md` already specify a different, more
specific architecture for this exact robot (a bus-message-driven `robot_service` consumed by an
orchestrator state machine, a fixed safety envelope with exact numbers, an explicitly-cut
physical-intercept behavior, and a taped-demo-area camera/LiDAR tracker instead of open-vocabulary
person/object detection). Per direction received when this conflict was raised, **this plan
follows the pasted brief's generic MCP-skill-library design instead**, superseding those docs
where the two disagree. Every place that happens is called out explicitly below so nobody reading
`docs/` later is blindsided by the divergence.

---

## 1. Core DimOS architecture (read this before anything else)

DimOS is **not** an object you instantiate and call `.move_forward()` on. It's a
**Module + autoconnect blueprint** system:

- **`Module`** (`dimos/core/module.py`) — base class for any unit of the system. Declares typed
  I/O ports (`In[T]`, `Out[T]`) and RPC-callable methods (`@rpc`). Modules run as independent
  processes/workers wired together by streams.
- **`autoconnect(...)`** (`dimos/core/coordination/blueprints.py`) — composes several
  `Module.blueprint()`s into one `Blueprint`, auto-wiring matching port types together. A
  blueprint is itself composable (`autoconnect(existing_blueprint, NewModule.blueprint(), ...)`).
- **`@skill`** (`dimos/agents/annotation.py`) — decorates a `Module` method to mark it
  agent-callable. Wraps it with `@rpc`, per-call context, timing/logging. Supports:
  - `@skill` (bare) — `lifecycle="instant"`, no declared capabilities.
  - `@skill(uses=["movement"], lifecycle="background")` — declares it holds the `movement`
    capability while running, and that it starts background work and returns early rather than
    blocking to completion.
- **CLI**: `dimos run <blueprint-name>` launches a blueprint as a live process
  (`dimos/cli/commands/lifecycle.py`); `dimos list` lists blueprints
  (`dimos/cli/commands/info.py::list_blueprints`, reads `dimos.robot.all_blueprints.all_blueprints`
  plus this repo's `dimos.blueprints` entry point group via
  `dimos/robot/external_blueprints.py`); `dimos mcp *` talks to the running instance's MCP server
  (`dimos/cli/dimos.py`) — see §4.

### Skill authoring pattern (confirmed from real examples)

Two coexisting styles exist in the codebase:

1. **Legacy**: `AbstractRobotSkill` (pydantic `BaseModel` fields, `__call__()`), used only by
   `dimos/skills/unitree/unitree_speak.py` and `dimos/skills/visual_navigation_skills.py`. Not the
   pattern for new code — nothing recent uses it.
2. **Current** (what every Go2-agentic blueprint uses): `Module` subclass, typed ports for
   whatever data the skill needs, `Spec`/`Protocol`-typed attributes (prefixed `_`) injected for
   whatever DimOS subsystem it calls into, plain methods decorated `@skill`. Return either a plain
   descriptive `str`, or a `SkillResult` (`dimos/agents/skill_result.py`) for anything that needs a
   machine-checkable `success`/`error_code`.

`SkillResult` (current, still only used in one file — `ObserveSkill` — the rest of the codebase
mostly still returns strings; this plan's new skills should prefer `SkillResult` since it's the
typed/structured contract the brief wants and the framework already supports it end-to-end):

```python
@dataclass
class SkillResult(Generic[E]):
    success: bool
    message: str = ""
    error_code: E | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    @classmethod
    def ok(cls, message: str = "", **metadata) -> SkillResult[E]: ...
    @classmethod
    def fail(cls, error_code: E, message: str = "") -> SkillResult[E]: ...
```

`CommonSkillError = Literal["ROBOT_NOT_FOUND","INVALID_INPUT","INVALID_STATE","NOT_CONFIGURED",
"EXECUTION_FAILED","EXECUTION_TIMEOUT"]`. A domain declares its own error-code `Literal` alias and
parameterizes `SkillResult[MyDomainError]`.

### Capabilities and cancellation (`dimos/agents/capabilities.py`, `dimos/core/module.py`)

- `CAP_MOVEMENT = "movement"` is the one declared capability constant today. A skill that drives
  the robot declares `@skill(uses=[CAP_MOVEMENT])`.
- `CapabilityRegistry` is an in-memory, thread-safe, per-process mutex: the MCP server refuses (or
  briefly waits on) a tool call whose declared capability is already held by a *different* tool.
  Same-tool re-invocation is a takeover, not a conflict — this is what lets `follow_person` be
  called again to change target without an artificial "already running" error.
- **Background skills** (`lifecycle="background"`) must call `self.start_tool(name)` before doing
  anything (opens a tool-stream; safe to call unconditionally, including on a takeover),
  `self.tool_update(name, message)` to push progress, and `self.stop_tool(name)` in *every* exit
  path (normally in a `finally`, or in the background thread/task's own teardown) — that's what
  releases the capability hold. `person_follow.py`'s `follow_person`/`_follow_loop` is the
  reference implementation of this whole pattern, including "release from whichever path actually
  ends the loop" (lost-track, explicit stop, or the parent call's own early-return `finally`).
- **Cancellation of a live skill** happens by calling a **paired stop skill** (`stop_following`,
  `stop_navigation`, `stop_patrol`, `end_exploration`) — there is no separate generic
  "cancel any tool" RPC; each background skill exposes its own stop tool, and the MCP server's
  refusal message on a capability conflict explicitly tells the caller to do this ("Cannot start
  X: capability Y is held by Z... Call the appropriate stop tool first, then retry.").
- **Underlying navigation cancellation**: `NavigationInterfaceSpec.cancel_goal()` — see §2.

### MCP exposure (`dimos/agents/mcp/mcp_server.py`, confirmed from source)

- Every `@skill` method on every `Module` in a running blueprint is auto-discovered
  (`app.state.skills_by_name`, built from each module's `SkillInfo` — see
  `dimos/core/introspection/module/info.py`) and exposed as one MCP tool.
- **Tool schema** comes straight from the Python signature + docstring (`s.args_schema`, a
  Pydantic-generated JSON schema string): the docstring's summary becomes `description`,
  parameter names/types/defaults become the schema. **This means docstring quality and precise
  type hints directly become what the LLM sees** — exactly the "tool descriptions matter" concern
  in the brief.
- **Tool response formatting** (`_handle_tools_call`): if the return value has an `agent_encode()`
  method (i.e. it's a `SkillResult`), the server calls it and forwards its `content` list
  verbatim (`SkillResult.agent_encode()` emits one `{"type": "text", "text": json.dumps({success,
  message, error_code, duration_ms, metadata})}` block). Otherwise the return value is
  `str()`-coerced into a single text block. **Conclusion: skills should return `SkillResult` to
  get structured, parseable output; a plain string return becomes unstructured prose the LLM has
  to re-parse.**
- **Capability conflicts and background lifecycle are handled by the server itself** before your
  skill code even runs (see above) — skill authors don't need to re-implement mutual exclusion.
- **CLI invocation** (confirmed from `dimos/cli/dimos.py`, do not deviate from this syntax):
  ```
  dimos mcp list-tools
  dimos mcp status
  dimos mcp modules
  dimos mcp call <tool_name> --arg key=value [--arg key2=value2 ...] [--timeout N]
  dimos mcp call <tool_name> --json-args '{"key": "value"}'
  ```
  (`--arg`/`-a` values are JSON-decoded when possible, else treated as raw strings — booleans/
  numbers should be passed so they parse as JSON, e.g. `--arg distance_m=0.3` not `--arg
  "distance_m=0.3m"`.)

---

## 2. Navigation (confirmed: `dimos/navigation/*`, `dimos/robot/unitree/unitree_skill_container.py`)

- **`NavigationInterface`** (`dimos/navigation/base.py`) / **`NavigationInterfaceSpec`**
  (`dimos/navigation/navigation_spec.py`, the injectable `Protocol` version):
  ```python
  class NavigationState(Enum):
      IDLE = "idle"
      FOLLOWING_PATH = "following_path"
      RECOVERY = "recovery"

  def set_goal(self, goal: PoseStamped) -> bool: ...   # non-blocking
  def get_state(self) -> NavigationState: ...
  def is_goal_reached(self) -> bool: ...
  def cancel_goal(self) -> bool: ...
  ```
- **Concrete implementation for Go2**: `ReplanningAStarPlanner`
  (`dimos/navigation/replanning_a_star/module.py`) — A* over a costmap, continuous replanning,
  obstacle-ahead detection that halts and replans, stuck/path-deviation detection. This is what
  `_navigation` resolves to in every Go2 blueprint used below.
- **Turning in place / going to a pose — already built, use it directly, do not reimplement**:
  `UnitreeSkillContainer.move_to()` (`dimos/robot/unitree/unitree_skill_container.py`):
  ```python
  @skill
  def move_to(self, x: float = 0.0, y: float = 0.0, degrees: float | None = None,
              relative: bool = False) -> str:
      """... world frame by default (+x east, +y north); relative=True: x=forward,
      y=left, degrees=turn relative to current heading. Blocks until arrival,
      failure, or timeout."""
  ```
  Examples straight from its own docstring: `move_to(x=3.2, y=-0.5)`, `move_to(degrees=-90,
  relative=True)` (turn right 90° in place). It computes the goal from current pose via
  `self.tfbuffer.get("world", "base_link")`, calls `self._navigation.set_goal(goal)`, then blocks
  in `_wait_for_goal(timeout=100.0, settle=2.0)` polling `is_goal_reached()`/`get_state()`.
  **Positive `degrees` in `move_to` is a world-frame or relative-heading increase — need to verify
  sign convention against `Quaternion.from_euler`'s yaw convention (standard right-hand rule:
  positive yaw = counter-clockwise = left turn from above) empirically on hardware/sim before
  documenting `turn_relative`'s sign as authoritative** (see Skill 2 below).
- **Obstacle avoidance / collision stop**: layered, not something to reimplement —
  `LocalPlanner` (inside `ReplanningAStarPlanner`) checks `is_obstacle_ahead()` every tick and
  halts+replans; any module can broadcast `stop_movement: In[Bool]=True` to cancel the active
  goal (subscribed by `ReplanningAStarPlanner`, `BasicPathFollower`, `WavefrontFrontierExplorer`);
  `UnitreeWebRTCConnection` has a **0.2 s cmd_vel deadman timer** — if nothing republishes a
  velocity command within 0.2 s, the robot auto-stops at the connection layer, independent of
  everything else. Firmware-level `set_obstacle_avoidance()` is a fourth, independent layer
  (Unitree's own onboard system).
- **Costmap / occupancy**: `OccupancyGrid` (`dimos/msgs/nav_msgs/OccupancyGrid.py`) — numpy int8
  grid, `CostValues.{UNKNOWN=-1, FREE=0, OCCUPIED=100}`, `world_to_grid()`/`grid_to_world()`,
  `cell_value(pos)`. Produced by `CostMapper` (`dimos/mapping/costmapper.py`) from
  `VoxelGridMapper` + LiDAR pointcloud.
- **No standalone "distance to nearest obstacle in direction X" helper exists.** `approach_obstacle`
  will need to compute this itself from the costmap (raycast along a heading through
  `OccupancyGrid` cells) or from raw LiDAR `PointCloud2` (filter points within an angular cone in
  front of the robot, take min range) — see Skill 1 below for the concrete approach chosen.
- **Patrol**: `PatrollingModule` (`dimos/navigation/patrolling/module.py`) —
  `@skill(uses=[CAP_MOVEMENT], lifecycle="background") start_patrol()` /
  `@skill stop_patrol()`. **Important divergence from the brief**: this is a **coverage-area
  patrol router** (`PatrolRouter.next_goal()` picks goals to maximize area coverage /
  frontier-driven / random — see `dimos/navigation/patrolling/routers/`), not a fixed
  user-supplied waypoint list. There is no `set_waypoints([...])` API in DimOS. **Skill 4
  (`patrol_waypoints`) is therefore a custom composition**: loop calling the existing
  `go_to_named_location()` skill (Skill 3) over a caller-supplied list, not a reuse of
  `PatrollingModule`.
- **Frontier exploration**: `WavefrontFrontierExplorer` — `begin_exploration()`/
  `end_exploration()`, not used by this plan's skills directly but same
  start/stop-tool-pair pattern.
- **Person-following / visual servoing**: see §3.

---

## 3. Perception, person following, and spatial memory

### Person following — already built end-to-end, reuse directly

`PersonFollowSkillContainer` (`dimos/agents/skills/person_follow.py`) — the canonical example of
a background, streaming, cancellable movement skill:

```python
@skill(uses=[CAP_MOVEMENT], lifecycle="background")
def follow_person(self, query: str, initial_bbox: list[float] | None = None,
                   initial_image: str | None = None) -> str: ...

@skill
def stop_following(self) -> str: ...
```

Pipeline: `QwenVlModel` (VL model) detects a person from a **free-text description** on the
current camera frame → `EdgeTAMProcessor` (segmentation-based tracker) tracks across subsequent
frames → `VisualServoing2D.compute_twist()` (2D, bbox-position-based) or
`DetectionNavigation.compute_twist_for_detection_3d()` (3D, pointcloud-based, if
`config.use_3d_navigation=True`) turns the tracked position into a `Twist` published at 20 Hz.
Docstring states plainly: **"Does not do obstacle avoidance; assumes a clear path."** Loses track
after `_max_lost_frames=15` consecutive frames → auto-stops, releases capability, reports reason
via `tool_update`.

**Gap vs. the brief's Skill 7 requirement ("maintain minimum safe distance")**: `follow_person` as
shipped has no minimum-standoff enforcement — visual servoing drives the robot toward keeping the
person centered/sized in frame, not toward holding a specific metric distance. **This needs a
thin wrapper skill** (see Skill 7 below) that either (a) uses `use_3d_navigation=True` so 3D
detection-based twist computation has real distance to reason about, and layers a standoff check
on top, or (b) accepts and documents this as a known limitation. Do not claim distance-holding
that isn't actually enforced.

### Object/person detection — real open-vocabulary + dedicated person detectors exist (correcting an earlier gap in this plan)

The top-level `dimos/perception/detection/yolo.py` and `base.py` files are empty stubs, but the
**actual, implemented detectors live one level down**, in
`dimos/perception/detection/detectors/`, all conforming to a common interface:

```python
class Detector(ABC):                                  # detectors/base.py
    @abstractmethod
    def process_image(self, image: Image) -> ImageDetections2D: ...
```

- **`YoloPersonDetector`** (`detectors/person/yolo.py`) — YOLO11-pose + BoT-SORT tracking.
  **This is a dedicated, purpose-built person detector**, returning `Detection2DPerson` (bbox +
  17 COCO pose keypoints + per-keypoint scores, `type/detection2d/person.py`). This is a better
  fit for Skill 6 (`detect_person`) than the VL-query path below — it's a real detector with a
  real `confidence` field, not a single VL-model bbox call.
- **`Owlv2Detector`** / **`OmDetDetector`** (`detectors/owlv2.py`, `detectors/omdet.py`) —
  genuine **open-vocabulary, text-prompted** detectors (`query_detections(image, queries,
  threshold) -> ImageDetections2D`). Confirmed from source: each returned `Detection2DBBox` has a
  real, calibrated **`confidence: float`** (`"the calibrated per-box score"`, per
  `Owlv2Detector.query_detections`'s own docstring) and `name` set to the matched query string.
  **This resolves an item this plan originally flagged as unverified** — a genuine confidence
  score is available, but only through this detector-level API, not through the `BBox`-returning
  `get_object_bbox_from_image()` helper (below), which truncates to 4 coordinates and drops the
  score.
- **`Yolo2DDetector`** (`detectors/yolo.py`, fixed COCO-80 classes) and **`Yoloe2DDetector`**
  (`detectors/yoloe.py`, prompt-free or text/visual-prompted open-set) are also implemented and
  available, not used by this plan's skills directly.
- **3D lift**: `Detection3DBBox`/`Detection3DPC` (`type/detection3d/`) give world-frame
  `center`/`orientation`/`.pose -> PoseStamped` once a 2D detection is combined with depth + TF —
  this is the real path to a `world_position` field for Skill 6, not something to fake.
- **What's actually wired into the Go2 agentic blueprints today** is still the lighter-weight
  path used in `navigation.py`/`person_follow.py`: **`get_object_bbox_from_image(vl_model, image,
  query)`** (`dimos/navigation/visual/query.py`), backed by `QwenVlModel`
  (`dimos/models/vl/qwen.py`) — single VL call, single current frame, returns a bare `BBox` (4
  coordinates, `dimos/models/qwen/bbox.py`), **no confidence field**. This is what
  `follow_person`'s initial detection and `navigate_with_text`'s object-in-view step both use.
  **Recommendation for this plan's skills**: use `Owlv2Detector`/`YoloPersonDetector` directly
  (new, small integration — neither is wired into any Go2 blueprint examined) when an honest
  confidence score matters (Skill 6), and keep the existing `QwenVlModel`/`BBox` path only where
  matching existing skills' behavior (Skill 7/8, which build on `PersonFollowSkillContainer`
  as-is).
- `dimos/perception/detection/person_tracker.py` (`class PersonTracker(Module)`) is a separate,
  lower-level streaming building block (`center_to_3d`, `detections_stream()` Observable,
  `track()`) not wired into any Go2 agentic blueprint examined — available but would be new
  integration work, not reuse of a proven path.
- `ObserveSkill` (`dimos/agents/skills/observe_skill.py`) — `@skill observe() -> Image |
  SkillResult` — returns the current camera frame (or `SkillResult.fail("EXECUTION_TIMEOUT", ...)`
  on a 5 s timeout with no frame). This is the honest "look at the camera" primitive; useful as
  the visual-verification step in Skill 13 (`search_for_object`).

### Spatial memory — already built, exactly matches Skills 3/12/13's needs

The **injectable, skill-facing** interface is narrow —
`SpatialMemorySpec` (`dimos/perception/experimental/spatial_memory_spec.py`):

```python
class SpatialMemorySpec(Spec, Protocol):
    def tag_location(self, robot_location: RobotLocation) -> bool: ...
    def query_tagged_location(self, query: str) -> RobotLocation | None: ...
    def query_by_text(self, text: str, limit: int = 5) -> list[dict]: ...
```

But the **concrete module behind it, `SpatialMemory`** (`dimos/perception/experimental/
spatial_perception.py`), has a substantially larger `@rpc` surface than this narrow `Spec`
exposes — confirmed directly from source:

```python
@rpc
def add_named_location(self, name: str, position: list[float] | None = None,
                        rotation: list[float] | None = None,
                        description: str | None = None) -> bool: ...
    # Uses current tf ('world'->'base_link') if position/rotation are omitted.

@rpc
def find_robot_location(self, name: str) -> RobotLocation | None: ...
    # Case-insensitive linear search by name.

@rpc
def get_robot_locations(self) -> list[RobotLocation]: ...
    # All stored named locations -- this *is* list_named_locations, already built.

@rpc
def query_by_text(self, text: str, limit: int = 5) -> list[dict]: ...
    # CLIP text-to-image semantic search over recorded frames.

@rpc
def add_robot_location(self, location: RobotLocation) -> bool: ...

@rpc
def tag_location(self, robot_location: RobotLocation) -> bool: ...
@rpc
def query_tagged_location(self, query: str) -> RobotLocation | None: ...
```

**This revises an earlier draft of this plan**, which (working only from the narrow `Spec`) had
flagged `list_named_locations` as unsupported. It is not: `get_robot_locations()` already does
this, just not yet exposed as a `@skill` or through `SpatialMemorySpec` — Skill 3's
`list_named_locations` should inject `SpatialMemory` directly (or widen `SpatialMemorySpec`) and
call straight through, not reimplement listing.

**`delete_named_location` genuinely has no equivalent** — confirmed, no delete/remove method
exists anywhere on `SpatialMemory` or `SpatialVectorDB`. This one is still a real gap (see
feasibility matrix).

Backed by `SpatialVectorDB` (`dimos/perception/experimental/spatial_vector_db.py`, wraps
ChromaDB) — persistent vector DB storage, image embeddings for scene recall, and named-pose
tagging. `RobotLocation` (`dimos/types/robot_location.py`) is the record type:

```python
@dataclass
class RobotLocation:
    name: str
    position: tuple[float, float, float]
    rotation: tuple[float, float, float]
    frame_id: str | None = None
    timestamp: float = ...
    location_id: str = ...
    metadata: dict[str, Any] = ...
```

`NavigationSkillContainer` (`dimos/agents/skills/navigation.py`) already composes this into
exactly the behavior Skills 3, 12, and 13 ask for:

```python
@skill
def tag_location(self, location_name: str) -> str: ...        # save_named_location

@skill(uses=[CAP_MOVEMENT])
def navigate_with_text(self, query: str) -> str:
    """1. tagged-location lookup by name
       2. live VL object detection in current camera view + tracked navigation to it
       3. fallback: semantic-map text query over previously tagged locations/objects
       Tries all three in order; returns which one matched."""

@skill
def stop_navigation(self) -> str: ...
```

This single container already **is** `go_to_named_location` + `find_object` +
`navigate_to_object` + `search_for_object`'s "query memory, else look" fallback chain, fused into
one tool. This plan's job for Skills 3/12/13 is mostly to **split its three fused behaviors back
out into the brief's more granular tool names** (so a small LLM sees one clear verb per
intent, per the brief's own small-LLM-compatibility rule) while calling straight through to
`_spatial_memory`/`_navigation`/`SpatialMemory`, not reimplementing storage or lookup.

---

## 4. Unitree Go2 hardware integration

`GO2Connection` (`dimos/robot/unitree/go2/connection.py`, `Module` subclass) is the actual
hardware-facing module — not a `Go2()`-style object you construct directly, but composed via
blueprints (see §5). Key methods (all `@rpc`, i.e. callable cross-module):

```python
move(self, twist: Twist, duration: float = 0.0) -> bool
stop_movement(self) -> None                       # zero the base immediately
standup() -> bool / liedown() -> bool / balance_stand() -> bool
sport_command(api_id: int) -> bool                 # raw Unitree SPORT_MOD by id
set_obstacle_avoidance(enabled: bool = True) -> bool
set_light(level: int) -> bool
@skill get_battery_soc(self) -> int | None         # 0-100, already agent-callable
```

`UnitreeSkillContainer` (`dimos/robot/unitree/unitree_skill_container.py`) additionally exposes
`execute_sport_command(command_name: str)` — ~40 named built-in Unitree behaviors (StandUp, Sit,
Hello, FrontFlip, Dance1, Handstand, etc.), each mapped to a WebRTC `SPORT_MOD` api_id, with the
full list baked into its auto-generated docstring. Useful for gesture/posture skills, not
navigation.

**Pose access**: no single `RobotState` object. Pose is `PoseStamped` on each module's
`odom: Out[PoseStamped]` port, and/or via the shared `self.tfbuffer.get("world", "base_link")`
helper (any `Module` declaring a `tf: In[TFMessage]` port gets this) — this is what
`UnitreeSkillContainer.move_to()` itself uses to read current pose.

**Battery**: `GO2Connection.get_battery_soc()` — already a `@skill`, already agent-callable, no
new work needed; Skill 14 (`return_to_home`) and any low-battery caveat can call it directly.

**Connection selection** (webrtc / mujoco sim / dimsim sim / replay) happens inside
`GO2Connection.__init__` via `make_connection(...)`, driven by `GlobalConfig` — not something a
skill author touches; you get whichever backend the running blueprint was configured for.

---

## 5. Blueprint composition — how a new skill actually gets wired onto a running Go2

Confirmed reference chain, from `dimos/robot/all_blueprints.py` and the files it points to:

```
unitree_go2_basic  (GO2Connection + vis)
  → unitree_go2  (+ VoxelGridMapper, CostMapper, ReplanningAStarPlanner,
                    WavefrontFrontierExplorer, PatrollingModule, MovementManager)
    → unitree_go2_spatial  (+ SpatialMemory, PerceiveLoopSkill)
      → unitree_go2_agentic  (+ McpServer, McpClient, _common_agentic)
```

`_common_agentic` (`dimos/robot/unitree/go2/blueprints/agentic/_common_agentic.py`):

```python
_common_agentic = autoconnect(
    NavigationSkillContainer.blueprint(),
    ObserveSkill.blueprint(),
    PersonFollowSkillContainer.blueprint(camera_info=GO2Connection.camera_info_static),
    UnitreeSkillContainer.blueprint(),
    WebInput.blueprint(),
    SpeakSkill.blueprint(),
)
```

There's also `unitree_go2_agentic_ollama` — the same stack, but pointed at a local Ollama model
(`McpClient.blueprint(model="ollama:qwen3:8b")`), i.e. **DimOS already ships the exact
small-local-LLM configuration the brief asks to design for**; use it directly for testing rather
than inventing a new one.

**This is the pattern for adding the plan's new skill modules**: write each new skill as its own
`Module` subclass (or a small number of them grouped logically), give each a `.blueprint()`, add
them to a new `autoconnect(...)` alongside the existing `unitree_go2_spatial` stack (mirroring
`_common_agentic`), and register that as a new blueprint (either via this repo's existing
`dimos.blueprints` entry-point group in `pyproject.toml`, following the `hackmitdog.behaviors:
DogBehaviors` pattern already present, or as new files directly under `hackmitdog/`). Launch with
`dimos run <blueprint-name>`.

---

## 6. Feasibility matrix

| Skill | Status | DimOS dependency | Notes |
|---|---|---|---|
| 1. `approach_obstacle` | Composition + small custom loop | `ReplanningAStarPlanner`/`NavigationInterfaceSpec`, `OccupancyGrid`/raw LiDAR `PointCloud2`, `GO2Connection` | No ready "distance to nearest obstacle ahead" primitive; must compute from costmap/pointcloud each tick. Movement itself reuses `move_to(relative=True)`/`set_goal` in small increments, not custom motor control. |
| 2. `turn_relative` | Directly supported | `UnitreeSkillContainer.move_to(degrees=..., relative=True)` | Thin wrapper/rename; verify turn-sign convention empirically before documenting it as fact. |
| 3. `go_to_named_location` (+ save/list/delete) | Mostly supported | `NavigationSkillContainer.tag_location`/`navigate_with_text`, `SpatialMemory.add_named_location`/`get_robot_locations`/`find_robot_location` | save/go-to/**list** all reuse existing `SpatialMemory` RPCs directly (list via `get_robot_locations()`, confirmed present). Only **delete** needs new code — no remove method exists anywhere in `SpatialMemory`/`SpatialVectorDB`. |
| 4. `patrol_waypoints` | Custom composition | Skill 3's `go_to_named_location`, looped | DimOS's own `PatrollingModule` is coverage-based, not a fixed waypoint list — not reusable for this exact behavior. |
| 5. `guided_walk` | Custom composition, explicit limitation | Skill 4 (patrol_waypoints) at reduced speed | No "verify person is following" mechanism exists anywhere in DimOS — must be documented as UNSUPPORTED / not implemented, not faked. |
| 6. `detect_person` | Directly supported, with a real confidence field | `YoloPersonDetector` (dedicated person detector, pose keypoints) or `Owlv2Detector.query_detections(["person"])` (both return real per-detection `confidence`), `ObserveSkill`, `Detection3DBBox` for `world_position` | Neither detector is currently wired into any Go2 agentic blueprint — small, real integration work, not a stub. No persistent identity (by design, per the brief). |
| 7. `follow_person` | Directly supported, with one gap | `PersonFollowSkillContainer.follow_person`/`stop_following` | Ships with no enforced minimum-distance; needs a wrapper or documented limitation — see §3. |
| 8. `escort_person` | Custom composition | Skill 6 + Skill 7 + Skill 3 | No "person still following" verification available (same gap as guided_walk) — document, don't fake. |
| 9. `danger_zone` (CRUD) | Requires custom implementation | none — no polygon/geofence class exists in DimOS (confirmed: no `shapely`, no `Zone`/`Geofence`/`Polygon` class anywhere in the package) | Build as a small standalone module: polygon storage (JSON or reuse a KV/vector store), point-in-polygon test, distance-to-polygon. Persist locally (this repo owns it; DimOS doesn't). |
| 10. `monitor_danger_zones` | Requires custom implementation | Skill 9 + person-position source (see limitation below) | Implement as a DimOS background skill (`lifecycle="background"`, `start_tool`/`stop_tool`), not a blocking MCP call — matches the framework's own idiom. **DimOS has no standing "current tracked person position" stream** outside of the transient bbox from a `detect_person`/`follow_person` call — see limitation note. |
| 11. `intercept_danger_zone` → `navigate_to_safe_intercept_position` | Custom composition, geometry-only | Skill 3/9's navigation + polygon math | No contact/blocking, per the brief's own explicit prohibition — implemented as "navigate near, keep clearance," which is squarely inside what `set_goal`/`find_safe_goal`-style clearance logic already supports. |
| 12. Spatial object memory (`remember_object_location`/`find_remembered_object`) | Directly supported | `SpatialMemory.add_named_location`/`find_robot_location`/`get_robot_locations`, `RobotLocation` | Reuse as-is; object memory and location memory are the same underlying store (`RobotLocation` records), just called with an object name instead of a place name. `room` in the brief's example record is only honest if the caller supplies it (e.g. via the current named-location match) — never inferred. |
| 13. `search_for_object` | Supported via composition | Skill 12 + Skill 3 (navigate) + `ObserveSkill` (verify) | Matches `NavigationSkillContainer.navigate_with_text`'s existing fallback chain almost exactly; open-vocabulary claims limited to what the VL bbox call can actually do (single current frame, no scene-wide search). |
| 14. `return_to_home` | Supported, honest about docking | Skill 3 (`go_to_named_location("home")`) | No DimOS/Unitree autonomous-docking API found in this investigation — report `arrived_at_dock_pose`, never "charging," unless a docking API turns up during implementation (flag and re-check, don't assume absence is final without a targeted grep at build time). |

**Explicit UNSUPPORTED / REQUIRES ADDITIONAL COMPONENT items** (per the brief's own rule 8):

- **Person-following verification during `guided_walk`/`escort_person`** — DimOS has no
  "is the tracked person still within N meters, still behind me" primitive independent of the
  transient per-call VL detection. `follow_person`'s own loop only knows "still in frame /
  lost track," not a numeric distance. Building real verification would mean either (a) wiring
  `PersonTracker`/3D detection navigation for a continuous distance readout (real, scoped
  integration work, not currently wired into any Go2 blueprint), or (b) leaving this
  unimplemented and reporting it plainly in the skill's returned status. This plan chooses (b)
  for the first pass and flags (a) as follow-up work.
- **Autonomous charging/docking** — no evidence found in this DimOS install of a dock-detection
  or auto-charge API. `return_to_home` stops at a named pose and reports arrival, not charging.
- **Numeric detection confidence via the `QwenVlModel`/`get_object_bbox_from_image` path only** —
  that specific helper's `BBox` return type carries no confidence score. Real confidence **is**
  available via `Owlv2Detector`/`OmDetDetector`/`YoloPersonDetector.query_detections()`/
  `process_image()`, which this plan uses for Skill 6 instead.
- **Delete for named locations and remembered objects** — confirmed no enumerate-*and*-delete
  gap: `get_robot_locations()` already lists everything (§3). Only **delete** is a genuine gap —
  no remove method exists on `SpatialMemory`/`SpatialVectorDB`; needs a small addition (either a
  targeted look at whether the underlying ChromaDB collection supports delete-by-id directly, or
  a soft-delete/tombstone layer on top).

---

## 7. Files intended to add/change

All new code lives under this repo's own package, following its existing `dimos.blueprints`
entry-point convention — **no changes to DimOS itself** are planned or needed; everything above is
reachable through public `Spec`/`Module`/`@skill` surfaces.

```
hackmitdog/
  behaviors.py                  # existing stub — left alone, or its skill folded into aegis_skill_blueprint.py
  aegis/
    __init__.py
    locations.py                 # Skill 3: go_to_named_location, save/list/delete_named_location
    navigation_skills.py         # Skills 1, 2, 4: approach_obstacle, turn_relative, patrol_waypoints
    person.py                    # Skills 6, 7, 8: detect_person, follow_person wrapper, escort_person
    guided_walk.py                # Skill 5: guided_walk
    danger_zone.py                # Skills 9, 10, 11: zone CRUD, monitor, safe-intercept
    object_memory.py              # Skills 12, 13: remember/find object, search_for_object
    home.py                       # Skill 14: return_to_home
    blueprint.py                  # autoconnect(...) composing all of the above onto unitree_go2_spatial
pyproject.toml                   # add the new blueprint to [project.entry-points."dimos.blueprints"]
DIMOS_SKILL_IMPLEMENTATION_PLAN.md  # this file
AEGIS_SKILL_TESTING.md            # Phase-2 deliverable, written alongside each skill
```

---

## 8. Safety architecture (deterministic layer, not the LLM)

Per the brief's own instruction, safety enforcement sits below the skill layer, using DimOS's
existing mechanisms rather than new ones wherever possible:

- **Obstacle clearance / collision avoidance**: `ReplanningAStarPlanner`'s obstacle-ahead check
  and replanning, plus firmware `set_obstacle_avoidance` — already deterministic, already
  independent of any LLM call.
- **Hard stop / deadman**: the 0.2 s cmd_vel timeout in `UnitreeWebRTCConnection` — already exists,
  already independent of skill code.
- **Bounded execution**: every new skill in this plan takes an explicit `timeout_s` and, where
  relevant, a `max_travel_m`/`max_distance_m` bound, enforced in a plain Python loop around the
  DimOS calls (not left to the LLM to notice a runaway).
- **Cancellation**: every long-running skill follows the `lifecycle="background"` +
  `start_tool`/`stop_tool` + paired `stop_*` skill pattern already established by
  `PersonFollowSkillContainer`/`PatrollingModule`/`WavefrontFrontierExplorer`.
- **Never intentionally moving into a person**: `intercept_danger_zone` is implemented only as
  "navigate to a safe standoff position," never as blocking/contact — matching the brief's own
  explicit prohibition, and incidentally matching this repo's `docs/06-safety-ethics.md` on this
  one point even though this plan otherwise diverges from those docs.
- **What this plan does *not* newly enforce**: a numeric minimum-standoff distance during
  `follow_person`/`escort_person` (see UNSUPPORTED list above) — flagged rather than silently
  assumed safe.

---

## 9. Open items to verify empirically before/during Phase 2 implementation

1. ~~`move_to(degrees=..., relative=True)`'s turn-sign convention~~ — **resolved during Phase 2
   implementation**: confirmed from `UnitreeSkillContainer._goal_pose`'s relative-turn math
   (`yaw = euler.yaw + math.radians(degrees or 0.0)`) plus standard right-hand-rule z-up yaw:
   **positive `angle_degrees` turns left/counter-clockwise, negative turns right/clockwise**.
   Implemented in `hackmitdog/aegis/navigation_skills.py`'s `turn_relative`. Still worth one real
   hardware/sim turn to double-check empirically (see `AEGIS_SKILL_TESTING.md`'s
   NEXT_HARDWARE_TESTS), but the source-level derivation is unambiguous.
2. ~~Whether `SpatialVectorDB`'s concrete backend supports enumeration by name~~ — **resolved**:
   `SpatialMemory.get_robot_locations()`/`find_robot_location()` already do this (§3). Only
   **deletion** is still open — check whether the underlying ChromaDB collection supports
   delete-by-id directly before building a custom tombstone layer.
3. ~~Whether confidence is available for detections~~ — **resolved**: yes, via
   `Owlv2Detector`/`OmDetDetector`/`YoloPersonDetector`, just not via the `BBox`-returning
   `get_object_bbox_from_image()` helper used by the currently-wired Go2 skills (§3).
4. Whether any docking/charge-detection API exists elsewhere in the package outside the paths
   searched here (targeted grep for `dock`/`charg` at implementation time).
5. Costmap vs. raw-pointcloud approach for `approach_obstacle`'s live distance measurement —
   prototype both against sim before committing.
6. Whether `YoloPersonDetector`/`Owlv2Detector` are cheap enough to run per-call (model load time,
   inference latency) inside an `instant`-lifecycle `detect_person` skill, or whether they need to
   run as a standing `Detection2DModule` stream instead (more consistent with how
   `Detection2DModule`/`Detection3DModule` are designed to be used) — affects Skill 6's actual
   latency and whether it should be `instant` or backed by an always-running perception module.
   **Partial data point from implementation**: `YoloPersonDetector()` construction downloads and
   caches its ~72MB weight file on first use (one-time, ~17s), then is fast (~1.5s including
   interpreter startup) on subsequent calls with weights cached — constructed once in
   `PersonSkills.__init__`, not per skill call, so steady-state latency should be fine for
   `instant`; not yet measured against a live camera stream on real inference hardware.

## 10. Corrections and additions from Phase 2 implementation

Recorded here rather than silently rewritten into §1-§8 above, so the investigation-vs.-build
distinction stays visible.

- **Reading a `Module`'s input port's latest value has no `.latest()` method.** The real,
  DimOS-native pattern (confirmed in `dimos/core/module.py` and used by `PatrollingModule`) is
  declaring `async def handle_<port_name>(self, msg: T) -> None` on the `Module` — DimOS's
  `_auto_bind_handlers` auto-subscribes it on `start()`. `hackmitdog/aegis/navigation_skills.py`'s
  `approach_obstacle` uses this (`handle_global_costmap`) to cache the latest `OccupancyGrid` under
  a lock for its obstacle-raycasting helper. Anything in this plan that talked about "reading the
  latest port value" should be understood as this handler pattern, not a getter method.
- **Direct Module-type injection is real and confirmed working**, not just inferred from the
  blueprint docstring: `dimos/core/coordination/blueprints.py::BlueprintAtom.create` calls
  `is_module_type(annotation)` as a parallel branch right next to `is_spec(annotation)`, both
  producing a `ModuleRef` resolved to an RPC proxy at blueprint-build time. Used in
  `hackmitdog/aegis/person.py` (`_person_follow: PersonFollowSkillContainer`) and
  `hackmitdog/aegis/guided_walk.py` (`_location_skills: LocationSkills`) to compose sibling skill
  modules without reimplementing their behavior.
- **`SpatialMemory.add_named_location` has no room/metadata parameter** — its real signature is
  `add_named_location(name, position=None, rotation=None, description=None) -> bool`, and it never
  populates `RobotLocation.metadata` even though the dataclass has that field. This is a sharper
  gap than originally scoped: a caller-supplied `room` (Skill 12) has nowhere structured to go and
  is folded into the free-text `description` string instead (`hackmitdog/aegis/object_memory.py`).
- **`PersonFollowSkillContainer.follow_person` returns a plain `str`, not a `SkillResult`** — the
  Aegis wrapper (`hackmitdog/aegis/person.py`) has to string-match its message ("Could not find...",
  "failed") to map onto `AegisError` codes, since the underlying skill gives no structured error.
  Noted as a soft dependency on upstream DimOS wording that could silently break if that string
  changes in a future DimOS release.
- **Implemented file list, current as of Phase 2**: `hackmitdog/aegis/{__init__.py, skill_errors.py,
  spec_ext.py, locations.py, navigation_skills.py, person.py, guided_walk.py, object_memory.py,
  home.py, danger_zone.py, blueprint.py}`, registered as the `aegis-go2` blueprint in
  `pyproject.toml`. See `AEGIS_SKILL_TESTING.md` for exact run/test commands.

co# Aegis skill testing — exact commands

Companion to `DIMOS_SKILL_IMPLEMENTATION_PLAN.md`. Every command below uses the real, confirmed
`dimos mcp` CLI syntax (`dimos/cli/dimos.py`, `dimos/cli/commands/mcp.py`) — nothing here is
invented. Run everything from the venv that has both `dimos` and this repo installed:

```bash
source /Users/laminegueye/dimensional-applications/.venv/bin/activate
cd /Users/laminegueye/Desktop/repos/HackMITdog
# This venv has no `pip` module bootstrapped; use uv against it instead
# (confirmed working: `uv pip install -e .` installs hackmitdog==0.1.0 in ~1s).
VIRTUAL_ENV=/Users/laminegueye/dimensional-applications/.venv uv pip install -e .
```

## Launching

The blueprint's runnable name is namespaced by distribution name — confirmed via
`dimos list`/`list_external_blueprint_names()`, it's **`hackmitdog.aegis-go2`**, not bare
`aegis-go2`:

```bash
dimos list                                  # confirm hackmitdog.aegis-go2 (and hackmitdog.behaviors) are discovered
dimos run hackmitdog.aegis-go2 --daemon     # launch the composed blueprint in the background
dimos mcp status                            # confirm the MCP server is up and see loaded modules
dimos mcp list-tools                        # see every Aegis skill's name + generated schema
```

**Confirmed by an actual launch attempt**: `dimos run hackmitdog.aegis-go2` alone fails —
`GO2Connection.__init__` raises `AssertionError: IP address must be provided` from
`dimos/robot/unitree/go2/connection.py::make_connection`. All 31 Aegis skill modules
(`LocationSkills`, `NavigationSkills`, `PersonSkills`, `GuidedWalkSkills`, `ObjectMemorySkills`,
`HomeSkills`, `DangerZoneSkills`) deployed successfully before this point — the failure is purely
`GO2Connection` needing either a real robot IP or a simulation backend, which `unitree_go2_spatial`
(the base this blueprint builds on) does not default. Before running, either:

- pass a real Go2's IP (check `unitree_go2_basic`'s config surface / `GlobalConfig` for the exact
  field name — not yet confirmed by this doc, verify against `dimos/robot/unitree/go2/blueprints/
  basic/unitree_go2_basic.py` and `GO2ConnectionSpec`'s config at launch time), or
- point at simulation the same way DimOS's own `unitree_go2_*_sim`-suffixed blueprints do (see
  `dimos/robot/unitree/go2/blueprints/` for the exact mechanism — this repo doesn't invent a new
  one and hasn't yet confirmed the precise flag from a successful sim run).

This is an environment/launch-configuration item, not a defect in any Aegis skill — every skill
module builds and deploys correctly regardless of which Go2 connection backend is eventually
selected.

To stop: `dimos stop` (per `dimos/cli/commands/lifecycle.py`).

## Calling a tool

General form, confirmed exact syntax:

```bash
dimos mcp call <tool_name> --arg key=value [--arg key2=value2 ...] [--timeout N]
# or
dimos mcp call <tool_name> --json-args '{"key": "value"}'
```

---

## LEVEL 1 — no motion

Safe to run against real hardware standing still, or pure simulation with nothing moving.

```bash
# Tool discovery
dimos mcp list-tools
dimos mcp modules

# Named-location CRUD (hackmitdog.aegis.locations.LocationSkills)
dimos mcp call save_named_location --arg name=kitchen
dimos mcp call list_named_locations
dimos mcp call delete_named_location --arg name=kitchen

# Danger zone CRUD (hackmitdog.aegis.danger_zone.DangerZoneSkills)
dimos mcp call create_danger_zone \
  --json-args '{"name": "front_door", "vertices": [[3.1,0.0],[4.2,0.0],[4.2,1.1],[3.1,1.1]]}'
dimos mcp call list_danger_zones
dimos mcp call is_in_danger_zone
dimos mcp call distance_to_danger_zone --arg name=front_door
dimos mcp call delete_danger_zone --arg name=front_door

# Spatial object memory (hackmitdog.aegis.object_memory.ObjectMemorySkills)
dimos mcp call remember_object_location --arg object_name=keys
dimos mcp call find_remembered_object --arg object_name=keys

# Guided-walk route definitions (no motion, just saving the route)
dimos mcp call save_guided_walk_route \
  --json-args '{"route_name": "morning_route", "locations": ["bedroom", "hallway", "kitchen"]}'
dimos mcp call list_guided_walk_routes
```

**Unit tests (no DimOS/hardware needed):**

```bash
python hackmitdog/aegis/test_danger_zone_geometry.py
# or, if pytest-style:
pytest hackmitdog/aegis/test_danger_zone_geometry.py -v
```

---

## LEVEL 2 — controlled movement

Requires a robot (real or simulated) with navigation running. Clear the area first; the safety
stack (obstacle-ahead replanning, cmd_vel deadman timer) is DimOS's own, but treat this like any
first hardware test.

```bash
dimos mcp call turn_relative --arg angle_degrees=90
dimos mcp call turn_relative --arg angle_degrees=-90

dimos mcp call save_named_location --arg name=start
# ... physically move the robot or drive it via teleop to a second spot ...
dimos mcp call save_named_location --arg name=spot_b
dimos mcp call go_to_named_location --arg name=start

dimos mcp call approach_obstacle --json-args '{"distance_m": 0.3, "direction": "front", "max_travel_m": 3.0}'
```

---

## LEVEL 3 — perception

Requires a camera stream. A person (or a teammate) should be in frame for the person-detection
calls.

```bash
dimos mcp call detect_person
```

---

## LEVEL 4 — dynamic behaviors

Background/long-running skills. Each has a paired stop tool — always confirm you can cancel
before relying on the happy path.

```bash
dimos mcp call follow_person --arg query="the person in the blue shirt"
# ... let it run, watch it track ...
dimos mcp call stop_person_follow

dimos mcp call guided_walk --arg route_name=morning_route
# ... watch it walk the route ...
dimos mcp call stop_guided_walk

dimos mcp call escort_person --json-args '{"destination": "bedroom", "standoff_m": 1.5}'
# ... watch it navigate ...
dimos mcp call stop_escort

dimos mcp call patrol_waypoints --json-args '{"locations": ["living room", "hallway", "kitchen"], "loop": false}'
dimos mcp call stop_patrol_waypoints

dimos mcp call start_monitoring_danger_zones --json-args '{"approach_threshold_m": 1.0}'
# ... walk/drive the robot toward a configured zone, watch for the notification ...
dimos mcp call stop_monitoring_danger_zones

dimos mcp call navigate_to_safe_intercept_position --json-args '{"zone_name": "front_door", "clearance_m": 1.5}'
```

---

## LEVEL 5 — composite agent tasks

Exercised through the running MCP agent (`dimos run hackmitdog.aegis-go2` with an `McpClient` attached — see
`hackmitdog/aegis/blueprint.py`'s module docstring for wiring in DimOS's existing Ollama-backed
`McpClient`, the same one `unitree_go2_agentic_ollama` uses), or manually chained via the `dimos
mcp call` commands above to simulate what the agent would do.

**Find my keys:**

```bash
dimos mcp call remember_object_location --arg object_name=keys     # (earlier, when keys were seen)
dimos mcp call search_for_object --arg object_name=keys
```

**Go to bedroom (escort):**

```bash
dimos mcp call detect_person
dimos mcp call escort_person --arg destination=bedroom
```

**Follow me:**

```bash
dimos mcp call detect_person
dimos mcp call follow_person --arg query="the person nearby"
```

**Check the front door:**

```bash
dimos mcp call go_to_named_location --arg name="front door"
dimos mcp call detect_person   # or `observe`, if the base Go2 agentic skill set is also loaded
```

**Guided indoor walk:**

```bash
dimos mcp call guided_walk --arg route_name=morning_route
```

**Wandering safety (danger-zone response):**

```bash
dimos mcp call start_monitoring_danger_zones
# ... approach a configured zone ...
# on notification:
dimos mcp call navigate_to_safe_intercept_position --arg zone_name=front_door
```

---

## Progressive checklist

- [ ] Level 1 — `dimos mcp list-tools` shows all 14+ skills with sane schemas
- [ ] Level 1 — location + danger-zone + object-memory CRUD round-trips
- [ ] Level 1 — `test_danger_zone_geometry.py` passes
- [ ] Level 2 — `turn_relative` sign convention matches the documented one
- [ ] Level 2 — `go_to_named_location` arrives and reports success
- [ ] Level 2 — `approach_obstacle` stops at approximately the requested distance, never collides
- [ ] Level 3 — `detect_person` returns a real confidence value, no fabricated fields
- [ ] Level 4 — every background skill's paired stop tool actually cancels it
- [ ] Level 4 — capability conflicts behave as documented (starting a second movement skill while
      one is active gets refused with the "call the stop tool" message)
- [ ] Level 5 — at least one composite flow run end-to-end through a real MCP agent, not just
      manually chained calls

## NEXT_HARDWARE_TESTS

Things this plan could not verify from source alone and must be confirmed on the physical
Unitree Go2:

1. **`turn_relative` sign convention** — confirm positive `angle_degrees` actually turns the
   direction documented in the skill's docstring, not just what the source code implies.
2. **`approach_obstacle`'s real stopping accuracy** — how close to `distance_m` it actually lands,
   under real LiDAR noise, not simulation.
3. **`follow_person`'s real-world lost-track behavior** — how often it drops track walking at a
   normal human pace, and whether `_max_lost_frames=15` (DimOS's own constant) needs tuning for
   this use case.
4. **Capability-conflict UX** — whether the "capability held by X, call its stop tool" refusal
   message is something a small local LLM (e.g. `ollama:qwen3:8b`) reliably acts on correctly, or
   needs a system-prompt nudge.
5. **`monitor_danger_zones` notification latency** — real round-trip from crossing
   `approach_threshold_m` to the MCP `notifications/progress` frame reaching a connected client.
6. **Battery behavior during a long `patrol_waypoints`/`guided_walk` run** — whether
   `GO2Connection.get_battery_soc()` should be polled and surfaced as a caveat before starting a
   long route.
7. **`detect_person`/person-detector latency** — whether `YoloPersonDetector` running per-call is
   fast enough for a responsive `instant` skill, or needs to move to a standing
   `Detection2DModule` stream (flagged as open item #6 in the plan).
8. **The exact IP/sim configuration to actually launch `hackmitdog.aegis-go2`** — confirmed by a
   real launch attempt that `GO2Connection` needs either a real Go2 IP or a simulation backend
   that a bare `dimos run hackmitdog.aegis-go2` doesn't supply by default (see the note under
   "Launching" above). All 31 skill modules deploy successfully up to that point — this is purely
   about which connection backend flag/config to pass, not a skill defect.

# Lantern — HackMIT planning repo

Planning and scoping documents for a voice-native quadruped companion for in-home
dementia care. (Working name: **Lantern**. Previously "Project Aegis" — see
[`docs/01-judge-review.md`](docs/01-judge-review.md#p0-8-the-name) for why the name changed.)

This repo holds the **plan**, not the code — deliberately. HackMIT allows you to plan in
advance but requires all project code to be written during the hacking window, so nothing here
is implementation and nothing should become implementation until hacking opens. See
[`docs/10-second-pass.md`](docs/10-second-pass.md) P1-8.

It exists so that four engineers can agree on scope, interfaces, and the demo before anyone
writes a line, because the most common way a 4-person hardware hack dies is integration at the
seam, in the middle of the night.

## Read this first: the clock

**HackMIT is 24 hours, not 36**, and HackMIT 2026 runs September 19–20. The original build plan
assumed 36 hours and every gate in it was wrong; it has been rewritten against a real wall
clock in [`docs/03-build-plan.md`](docs/03-build-plan.md). Confirm this year's exact start and
end times on `dayof.hackmit.org` and shift the schedule before relying on it.

## Read in this order

| Doc | What it's for | Who needs it |
|---|---|---|
| [`docs/01-judge-review.md`](docs/01-judge-review.md) | Teardown of the original plan from a judge's seat | Everyone, first |
| [`docs/10-second-pass.md`](docs/10-second-pass.md) | Second teardown, of the revised plan. The clock, and the two unspecified dependencies | Everyone, immediately after |
| [`docs/02-blueprint.md`](docs/02-blueprint.md) | The revised product: what we are actually building | Everyone |
| [`docs/03-build-plan.md`](docs/03-build-plan.md) | 24-hour schedule, ownership, cut lines | Everyone |
| [`docs/04-interfaces.md`](docs/04-interfaces.md) | Frozen event schemas so we can work in parallel | Everyone, in the first 90 minutes |
| [`docs/15-dev-workflow.md`](docs/15-dev-workflow.md) | Repo layout, git rules, and running four different AI coding agents without them colliding | Everyone, before anyone opens an agent |
| [`docs/11-perception.md`](docs/11-perception.md) | How the person actually gets tracked. Six things depend on it | E2, E4 |
| [`docs/12-dialogue-runtime.md`](docs/12-dialogue-runtime.md) | What produces each utterance, the latency budget, the impersonation guard | E1, E4 |
| [`docs/14-companion-and-caretaker.md`](docs/14-companion-and-caretaker.md) | Check-in relay, companionship conversation, onboarding schedule, guided walks, the completed wandering policy | Everyone |
| [`docs/05-demo.md`](docs/05-demo.md) | Table demo, stage demo, fallback ladder | Everyone |
| [`docs/06-safety-ethics.md`](docs/06-safety-ethics.md) | Safety envelope, consent, privacy, claims discipline | Everyone |
| [`docs/07-evaluation.md`](docs/07-evaluation.md) | The numbers we put on the slide | E1, E2, E4 |
| [`docs/08-tracks.md`](docs/08-tracks.md) | Sponsor track strategy, honestly assessed | Whoever pitches |
| [`docs/13-landscape.md`](docs/13-landscape.md) | Named prior art, and the answer when a judge names one | Whoever pitches |
| [`docs/09-judge-qa.md`](docs/09-judge-qa.md) | Anticipated questions and our answers | Whoever pitches |

## The one-sentence pitch

When someone with dementia gets up at 2 AM and starts heading for the front door, a door
alarm tells the family too late and tells them nothing; Lantern is there at the moment of
confusion, uses the same redirection technique a trained memory-care aide would, and hands
the caregiver a head start plus a record of exactly what happened.

## Aegis skill library (Go2 companion skills, via DimOS/MCP)

`hackmitdog/aegis/` is a set of high-level, agent-callable robot skills for the Unitree Go2, built
on top of DimOS's existing navigation, perception, and spatial-memory stack rather than
reimplementing any of it. See [`DIMOS_SKILL_IMPLEMENTATION_PLAN.md`](DIMOS_SKILL_IMPLEMENTATION_PLAN.md)
for the investigation behind it and [`AEGIS_SKILL_TESTING.md`](AEGIS_SKILL_TESTING.md) for exact
test commands. This section diverges intentionally from some of the docs above (see the plan
doc's §0) — it follows a generic MCP-skill-library design rather than the bus-message-driven
`robot_service` those docs originally specified.

### Running it

```bash
source /Users/laminegueye/dimensional-applications/.venv/bin/activate
cd /Users/laminegueye/Desktop/repos/HackMITdog
VIRTUAL_ENV=/Users/laminegueye/dimensional-applications/.venv uv pip install -e .   # registers the blueprint entry point
dimos run hackmitdog.aegis-go2 --daemon
dimos mcp list-tools               # see every skill's name + schema
```

### Skills

| Skill | Module | Feasibility |
|---|---|---|
| `save_named_location` / `list_named_locations` / `delete_named_location` / `go_to_named_location` | `locations.py` | Directly supported (DimOS spatial memory) |
| `turn_relative` | `navigation_skills.py` | Directly supported (DimOS navigation) |
| `approach_obstacle` | `navigation_skills.py` | Composition + small custom control loop |
| `patrol_waypoints` | `navigation_skills.py` | Custom composition over `go_to_named_location` |
| `save_guided_walk_route` / `list_guided_walk_routes` / `guided_walk` | `guided_walk.py` | Custom composition; explicit limitation (no follower-verification) |
| `detect_person` | `person.py` | Directly supported, real confidence (DimOS `YoloPersonDetector`) |
| `follow_person` / `stop_person_follow` | `person.py` | Directly supported (DimOS `PersonFollowSkillContainer`); documented distance-enforcement gap |
| `escort_person` / `stop_escort` | `person.py` | Custom composition; documented following-verification gap |
| `create_danger_zone` / `list_danger_zones` / `delete_danger_zone` / `is_in_danger_zone` / `distance_to_danger_zone` | `danger_zone.py` | Custom implementation (no DimOS geofence primitive) |
| `start_monitoring_danger_zones` / `stop_monitoring_danger_zones` | `danger_zone.py` | Custom implementation, background skill |
| `navigate_to_safe_intercept_position` | `danger_zone.py` | Custom implementation; geometry-only, never blocks/contacts a person |
| `remember_object_location` / `find_remembered_object` | `object_memory.py` | Directly supported (same DimOS spatial memory as named locations) |
| `search_for_object` | `object_memory.py` | Composition; visual "verification" is capture-only, not detection |
| `return_to_home` / `stop_return_to_home` | `home.py` | Supported; reports pose arrival only, never claims charging |

Every skill returns a `SkillResult` (structured `success`/`message`/`error_code`/`metadata`), takes
bounded/typed arguments, and every long-running skill has a paired stop tool. Safety-critical
behavior (obstacle avoidance, collision stop, capability mutual-exclusion) is enforced by DimOS
itself below the skill layer, not by the calling LLM — see the plan doc's §8.

## The hard rules

1. The robot never blocks, corners, touches, or herds a person. It leads. See `docs/06`.
2. No unvalidated clinical claims in the pitch, the UI, or the README. See `docs/06`.
3. The demo that must work is the one that doesn't need the robot. Hardware is upside. See `docs/03`.
4. Backup demo video is recorded by 6 AM Sunday. Non-negotiable. See `docs/05`.
5. Interfaces in `docs/04` freeze 90 minutes in. Changes after that need all four engineers to agree.
6. No project code before hacking opens, and cite every open-source dependency in `CREDITS.md`
   as you add it. See `docs/10` P1-8.
7. Four people, four different AI coding agents, one folder each, no long-lived branches, tiny
   commits. See `docs/15`.

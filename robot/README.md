# /robot — E2 (perception + Unitree / DimOS)

Owner: **E2**. Portal stays in `/cloud` and must never import Unitree or DimOS SDKs.

## Dog camera → Night Watch (on-demand)

Night Watch can show a **gated** live view when the caregiver taps **View dog camera**
(or accepts the soft offer during an alert). Video is **out-of-band** — not on the frozen
`04-interfaces` bus.

### Contract with E3

| | |
|---|---|
| Cloud env | `DOG_CAMERA_ENABLED=1` and `DOG_CAMERA_URL=<viewer>` |
| Viewer | Any HTTPS/HTTP page E3 can iframe (DimOS cockpit / teleop / your MJPEG page) |
| Privacy | Stream only while caregiver has the panel open — no 24/7 background feed |
| Bus | Do **not** invent `camera_frame` messages; keep map/track on `/api/ingest` as today |

### Fastest demo path (DimOS cockpit)

On the machine that talks to the Go2 (or sim):

```bash
# From your DimOS install (see DimOS docs/web)
uv run dimos --simulation run --local-relay unitree-go2-agentic-cockpit
# Cockpit (camera panel): http://127.0.0.1:7780/
```

Real robot: use DimOS Go2 WebRTC run + cockpit/teleop blueprints
(`teleop-hosted-go2-transport` or local relay). Go2 already exposes `color_image` when
`ConnectionConfig.camera=True`.

Then in `cloud/.env`:

```bash
DOG_CAMERA_ENABLED=1
DOG_CAMERA_URL=http://127.0.0.1:7780/
```

Restart cloud API; open Night Watch → **View dog camera**.

### Cleaner path (optional later)

Subscribe to DimOS `color_image` and serve MJPEG/WebRTC on a dedicated port; set
`DOG_CAMERA_URL` to that page, or `DOG_CAMERA_STREAM_URL` to a raw MJPEG URL for
`GET /api/camera/stream` (same-origin proxy for phone tunnels).

### Map / tracks (unchanged)

Still `POST /api/ingest` with `map_ready` / `person_track` — see
[`docs/16-e3-portal.md`](../docs/16-e3-portal.md) and
[`cloud/fixtures/sample_map_ready.json`](../cloud/fixtures/sample_map_ready.json).

## Room mapping skill

The Aegis Go2 blueprint now exposes `map_room` through DimOS MCP. It uses the
existing `WavefrontFrontierExplorer` and `world/global_map` voxel stream, then
writes `<map_id>.ply` (browser-loadable 3-D point cloud) and `<map_id>.json`
under `artifacts/maps` by default:

```bash
dimos mcp call map_room --json-args '{"room_id":"living_room","duration_s":180,"cloud_ingest_url":"http://127.0.0.1:8000/api/ingest","artifact_url":"https://maps.example/living_room.ply"}'
```

The result includes absolute artifact paths and the existing `map_ready`
payload. Serve the PLY from the returned path and load it with a web viewer
such as Three.js `PLYLoader`; the optional `artifact_url` is carried as
additive metadata in that existing payload. Stop/cancel the skill through the
normal DimOS `end_exploration` tool if needed.

### Start mapping from the portal

The onboarding **Start mapping** button sends a live `map_scan_request` when
`MAP_SCAN_MODE=live`. Run this bridge beside DimOS so it converts that request
into the `map_room` MCP call:

```bash
python robot/dimos_map_bridge.py \
  --bus-url ws://127.0.0.1:9000/ws \
  --cloud-base http://127.0.0.1:8000 \
  --artifact-dir artifacts/maps \
  --artifact-base http://127.0.0.1:8000/api/maps
```

The bridge writes the PLY into the cloud server's `artifacts/maps` directory
when both processes run on the same machine, then posts `map_ready` to the
cloud API. The portal stays on the mapping screen until that event arrives and
shows estimated progress while the robot explores. **Stop & use current map**
publishes the frozen robot `command` action `stop`; the bridge calls DimOS
`end_exploration`, after which `map_room` exports the freshest partial map and
posts its normal `map_ready`. Pause/resume is intentionally not shown because
the current explorer does not support resuming the same scan session.

## Runtime bridge: zones and bounded movement

`dimos_runtime_bridge.py` closes the software seam between the shared Lantern
bus and the existing deterministic DimOS tools. It:

- mirrors painted `exit`/“Don't go” polygons into DimOS danger zones;
- accepts only the frozen `lead_to`, `stop`, and `yield` command actions;
- requires `lead_to` destinations to be configured `safe` zones;
- maps a safe `zone_id` to a DimOS named location with the same name;
- publishes frozen `robot_status` lifecycle envelopes; and
- ignores mapping-stop commands, which remain owned by `dimos_map_bridge.py`.

Start it in observation/zone-sync mode first. This is the default and cannot
move the robot:

```bash
python robot/dimos_runtime_bridge.py \
  --bus-url ws://127.0.0.1:9000/ws \
  --bus-base http://127.0.0.1:9000
```

Before enabling movement, physically place the dog at the safe destination and
save the name used by E4's command:

```bash
dimos mcp call save_named_location --arg name=bedroom
```

Only after the controller-level 0.3 m/s cap, exit-polygon exclusion, live stop,
and 1.2 m yield reflex have been verified on that DimOS installation, restart
the bridge with `--motion-enabled`. The flag is an operator assertion; the
sidecar cannot prove that a lower motor controller is configured correctly.

```bash
python robot/dimos_runtime_bridge.py --motion-enabled
```

`yield_policy.py` is the tested, dependency-free decision core for the reflex:
trigger below 1.2 m, remain latched until 1.4 m, retreat only with at least
0.6 m rear clearance, and fail safe to stop on missing or stale range data.
It does **not** command motors yet. E2 must wire it to the live LiDAR and final
velocity output inside the DimOS process before `--motion-enabled` is safe.

Run all robot-side tests without hardware:

```bash
cd robot
.venv/bin/python -m unittest discover -s tests -v
```

## Patient position → danger-zone events

`tracking_adapter.py` implements calibrated position conversion, actor-ID filtering,
smoothed velocity, boundary-inclusive polygon classification, three-sample entry/exit
confirmation, and earliest projected intersection with an exit polygon (including thin
polygons). It publishes only existing `person_track` and `zone_event` envelopes.
Live `config_update.zones` replaces its polygons, including an empty list to clear them.
Overlaps prefer exit, then watch, then safe for the track's current zone; each polygon
gets independent transition events. Editing a zone resets classification rather than
pretending the patient walked across it.

**This is a position adapter, not a camera detector.** The current DimOS
`detect_person` tool returns a 2D box and no world position or stable identity. Do not
feed its normalized image-center coordinates as metres. Lamine must connect a detector
with stable actor IDs and measured floor points. For a fixed camera use the feet midpoint
and four floor correspondences; a moving Go2 camera requires depth + camera/robot/map
transforms upstream, not a fixed image homography. The adapter never infers identity.

### Test locally before connecting sensors

From the repository root, this replay prints envelopes and connects to nothing:

```bash
robot/.venv/bin/python robot/tracking_adapter.py \
  --calibration robot/fixtures/tracking_calibration.json \
  --zones robot/fixtures/tracking_zones.json --actor-id p1 \
  --input robot/fixtures/tracking_walk.jsonl --replay
```

Expect `approaching`, `entered`, then `exited` for `front_door`. Replay is always marked
`source: mock`, `tracker: mock`, even if another tracker flag was supplied. The fixture
is synthetic; it is not an Airbnb calibration.

For the full software chain, start this in a separate terminal using an environment
with the existing bus/orchestrator dependencies installed:

```bash
robot/.venv/bin/python robot/run_tracking_spine.py \
  --config robot/fixtures/tracking_zones.json --mock-robot
```

Add `--bus-url ws://127.0.0.1:9000/ws` to the replay command. To mirror into the running
portal, add `--cloud http://127.0.0.1:8000` to the spine command. Do not also run
`orchestrator/run_spine.py` or the cloud demo generator: those create another patient.
This runner uses the existing state machine and optionally the existing mock robot;
it starts no real robot controller. All events are recorded in `tracking_bus_events.jsonl`.
The short replay proves entry and exit; the automated integration test additionally
advances the escalation timer and verifies the level-2 alert.

### Lamine's live input

1. Export the current onboarding configuration as a JSON payload/envelope. Pass the same
   file to `--config` on the tracking spine and `--zones` on the adapter. This seeds the
   adapter because the bus does not replay configuration on connect. Subsequent zone
   edits arrive live; restart with a fresh export after connection loss.
2. Make a calibration JSON using the fixture's shape: the actual `map_id`, a named
   `input_frame`, and exactly four non-collinear source/map pairs. `source` is the
   detector's fixed-camera floor pixel point or an upstream world-frame point; `map`
   is the corresponding measured floor location in portal metres. Validate at additional
   measured points not used for fitting. Tape is optional; fixed measured landmarks work.
3. Feed one JSON line per measured observation on stdin, ideally 10 Hz, for example:

```json
{"ts":1758297600.123,"actor_id":"p1","frame":"camera_floor_pixels","map_id":"airbnb_v1","x":410,"y":520,"confidence":0.91,"posture":"unknown"}
```

The timestamp must be the actual capture time in Unix seconds on a synchronized clock;
the example timestamp is stale. These are **local detector input records**, not additions
to the frozen bus. Set `--actor-id` to the selected patient's upstream track ID. Never
reuse that ID for a new person after loss. Start the adapter with `--tracker overhead_cam`
(or the actual sensor type), the real calibration/config files, and `--bus-url`; omit
`--replay`. No sensor producer is bundled or assumed.

Samples older than 0.5 s, more than 0.1 s in the future, out of order, or below 0.6 confidence
are dropped. A gap resets velocity estimation and pending transitions. Missing tracking
does not generate a fictitious exit or a clear/safe event. It also does **not** currently
publish a lost-tracking alert or enforce a motor stop; controller watchdogs are separate.
Stationary body heading is unknown (`null`); this adapter must not be used to assert
the controller's person-relative approach sector is satisfied. Map/frame mismatches and
invalid input stop the process visibly. Bus loss stops publication; there is no stale replay.

### Verified alert behavior and remaining contract issue

Tests feed actual adapter output through the existing `StateMachine` and `MockRobot`:
danger-zone entry causes `LEAD` and a `lead_to` command; continued danger after the timer
causes `ESCALATE` and a level-2 `alert`. This verifies alert creation, not SMS delivery.
Timer duration follows the existing orchestrator configuration (5 s fast demo / 20 s normal).

**E4 contract issue:** the current emergency handler requires `zone_event.payload.outside`
to be true, but `docs/04-interfaces.md` does not define that field. We do not invent it here.
An `exited` event means leaving a polygon, not proof of crossing outdoors. Immediate
outdoor-breach escalation needs E4 to reconcile the contract and define a calibrated
outdoor boundary/direction. The adapter currently supports entry/redirection/timed alerts;
it cannot claim immediate outdoor emergency detection.

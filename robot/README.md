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

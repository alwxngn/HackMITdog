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

### Phone voice commands → DimOS

Start the combined DimOS blueprint, then run the bus adapter in a second terminal:

```bash
dimos run hackmitdog.aegis-breadcrumb-agentic \
  --robot-ip 192.168.12.1 \
  --unitree-aes-128-key "$UNITREE_AES_128_KEY" \
  --model openai:muse-spark-1.3

python robot/dimos_command_bridge.py --bus-url ws://127.0.0.1:9000/ws
```

The adapter maps existing bus commands to `follow_person`,
`stop_person_follow`, `start_breadcrumb_recording`, and `take_me_home`. It does
not add a new bus message or import DimOS into the cloud/orchestrator process.

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
cloud API. The portal polls for that event and shows the resulting artifact in
the 3-D map view.

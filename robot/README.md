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

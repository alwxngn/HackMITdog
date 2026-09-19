# E3 — Portal and cloud playbook

Owner: E3. Folder: `/cloud`. Schemas: `04-interfaces.md`. Workflow: `15-dev-workflow.md`.

This is the working checklist for the caregiver portal, FastAPI cloud, Twilio ladder,
onboarding, and morning report. It does not replace the build plan — it makes E3's slice
of it executable.

## Scope

| Owns | Does not own |
|---|---|
| FastAPI + WebSocket fan-out | Unitree / DimOS (E2) |
| Event store (JSONL + projection) | State machine / mocks (E4) |
| React Night Watch dashboard | STT / TTS / dialogue (E1) |
| Twilio escalation ladder + acknowledge | Impersonation guard / consent gate (E4) |
| Onboarding steps 3–4 (zones, home, schedule) | Tracker / lead-away controller (E2) |
| Check-in composer | |
| Morning report | |

**Hard rule:** the dashboard renders from the event stream alone. No demo mode. If it needs a
hack to look right, it's wrong (`03-build-plan.md`).

**Hard rule:** never import a Unitree or DimOS SDK into `/cloud`. The only robot connection is
JSON on the bus.

## Bus contract (what E3 reads and writes)

```
Consume (robot / voice / orchestrator → cloud):
  pose, person_track, zone_event, robot_status,
  agent_state, alert, transcript, prosody, speech_state, say

Publish (cloud → bus):
  caregiver_ack, config_update, checkin
```

Every message uses the common envelope in `04-interfaces.md` (`type`, `ts`, `source`, `seq`,
`payload`). Unknown fields are ignored, never fatal.

## Coordinate frame (agree with E2 out loud)

All of `pose.x/y`, `person_track.x/y`, and `config_update.zones[].polygon` are **metres in one
shared frame**.

**Default for the taped demo area (until E2 says otherwise):**

| | |
|---|---|
| Origin | Southwest corner of the taped rectangle (`patient.home = {x: 0.0, y: 0.0}`) |
| +x | East along the long edge of the tape |
| +y | North along the short edge |
| Units | Metres |
| Map size (demo) | ~2.0 m × 2.0 m (adjust after tape is down) |

Zone polygons drawn in the portal are in this frame. If E2's tracker and the portal disagree
on origin or axis, both look broken. Record any change here and in the fixture.

## Architecture

```
bus / fixture replay
        │
        ▼
  cloud/server/bus.py     subscribe(cb) / publish(msg)   ← only file that changes for real transport
        │
        ▼
  store.py                append JSONL + in-memory projection
        │
        ├─► WebSocket /ws     snapshot on connect, then live deltas
        ├─► escalation.py     ladder timers, cancelled by caregiver_ack
        ├─► notify.py         Twilio SMS + voice call
        └─► report.py         morning report = query over JSONL

  React portal ←── WS ──► projection (state, map, timeline, alerts)
```

On WebSocket connect the client receives `{type: "snapshot", payload: <projection>}` then
live deltas. The snapshot is a fold over the event log, not a demo mode.

## `/cloud` layout

```
/cloud
  server/
    main.py          FastAPI: /, /ws, /api/ack, /api/config, /api/checkin, /api/reset, /api/report
    bus.py           thin adapter — ONE file changes when E4 picks a transport
    schema.py        pydantic mirrors of 04-interfaces.md (until /bus ships)
    store.py         JSONL append + projection + timeline ring buffer
    escalation.py    ladder timers, ack cancellation
    notify.py        Twilio SMS + voice call
    report.py        morning report query
    replay.py        fixture player (dev)
  fixtures/
    exit_seeking.jsonl
  web/               Vite + React + TS + Tailwind
    src/lib/ws.ts
    src/lib/types.ts
    src/lib/frame.ts     worldToSvg(x, y) — metres → pixels, one place
    src/state/store.ts
    src/views/...
```

**Map is SVG, not a canvas library.** Zones = `<polygon>`, person/robot = `<circle>`,
live-tracking = `<polyline>` trail.

## Build order (wall clock)

### Block 1 — Scaffold + fixture
FastAPI `/ws`, Vite React, one message from `replay.py` → browser `<pre>`.
`schema.py` + `types.ts` from `04-interfaces.md`. Append every message to `events.jsonl`
from minute one. Start `CREDITS.md`.

### Block 2 — Twilio before polish
One real SMS to a real phone. Trial accounts only send to verified numbers.
Include `GET /api/ack?alert_id=...` in the SMS body.

### Block 3 — Dashboard v1
`StatePanel` (state, agitation, **reason** large, **tracker** badge), `Timeline`,
SVG `Map` (zones, person, robot).

### Block 4 — Escalation ladder · 6 PM gate
Timers: L2 SMS @ 0s, L3 voice call @ 60s, L4 secondary @ 120s, L5 immediate on
`dont_go_breach`. `caregiver_ack` cancels the tree. Full-screen alert banner with ACK.
Gate: fixture → dashboard arc → phone buzzes → ack stops it.

### Block 5 — Swap fixture for E4's bus
Change `bus.py` only. Re-run against `mock_patient` / `mock_robot`. Render
`robot_status: yielded` as a first-class timeline entry. Harden WS reconnect.

### Block 6 — Morning report + reset
Report = query over `events.jsonl`. `POST /api/reset` for E4's one-key reset.

### Block 7 — Onboarding 3–4 + check-in
Zones with caregiver label **"Don't go"** (wire `exit` + `label` + `kind`), home anchor,
ladder, schedule/habits → one `config_update`. Check-in composer → `checkin`.
Live-tracking map mode if slack.

**5:00 AM feature freeze.** Cut anything not working.

## Escalation ladder (server-side)

| Level | Trigger | Action |
|---|---|---|
| 2 | 20s no redirect / alert level 2 | SMS + push to primary, `requires_ack: true` |
| 3 | 60s unacknowledged | Twilio **voice call** to primary |
| 4 | 120s unacknowledged, or exit breach / person down | Secondary contact |
| 5 | `dont_go` zone `exited` | Immediate; `live_tracking: true` |

Every step is cancellable with one `caregiver_ack` (`im_coming` | `handled` | `false_alarm` | `call_help`).

## Onboarding (first-run wizard)

Four steps on `/onboarding`:

1. **Patient** — name, preferred name, calming / avoid topics  
2. **Scan home** — triggers mapping (see below)  
3. **Paint zones** — whole map starts Safe; paint Watch / Don’t go; place home pin  
4. **Schedule + contacts** — wake/meals/walk + escalation names → one `config_update`

### Scan home — dual mode (`MAP_SCAN_MODE`)

| Mode | When | Behavior |
|---|---|---|
| `demo` (default) | Table / no robot | Schematic floorplan after a short “scanning…” UI |
| `live` | Testing with Go2 | Publish `map_scan_request`; wait for E2 `map_ready` |

Set in `cloud/.env`:

```bash
MAP_SCAN_MODE=live
```

**E2 handoff checklist (agree out loud before first hardware map):**

| Rule | Value |
|---|---|
| Units | Metres |
| Origin | Southwest corner of the taped / mapped area (`patient.home` defaults to `{x:0,y:0}`) |
| +x | East along the long edge |
| +y | North along the short edge |
| E3 never imports | Unitree / DimOS SDKs — only JSON via `POST /api/ingest` |
| How E2 delivers | Same envelope as below; `request_id` must match the pending `map_scan_request` |

**Additive bus messages:**

```json
{ "type": "map_scan_request", "source": "cloud", "payload": {
  "request_id": "ms_1", "mode": "author_once"
}}
```

```json
{ "type": "map_ready", "source": "robot", "payload": {
  "request_id": "ms_1",
  "map_id": "home_v3",
  "origin": { "x": 0, "y": 0 },
  "width_m": 8.0, "height_m": 6.0,
  "outline": [[0,0],[8,0],[8,6],[0,6]],
  "rooms": [ { "id": "bedroom", "polygon": [[0,0],[3,0],[3,4],[0,4]] } ]
}}
```

Canonical sample (copy for DimOS export): [`cloud/fixtures/sample_map_ready.json`](../cloud/fixtures/sample_map_ready.json).

**Smoke without a robot** (proves portal + ingest; also posts three `person_track` samples):

```bash
# Terminal: cloud API with MAP_SCAN_MODE=live in .env (smoke forces mode=live in the POST body)
cd cloud && source .venv/bin/activate
python scripts/smoke_live_map.py
```

Manual curl equivalent after Scan home (or after `POST /api/map-scan` with `{"mode":"live"}`):

```bash
# Replace REQUEST_ID with status.pending.request_id
curl -s -X POST http://127.0.0.1:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d @cloud/fixtures/sample_map_ready.json
```

Then open `/onboarding` (map should appear) and `/watch`. Stream `person_track` the same way — if the pin is wrong, fix the **frame** with E2, not the React map renderer.

E2 runs DimOS author-once mapping and emits `map_ready` in the shared metre frame (origin = SW). Until a shared `/bus` transport is used end-to-end, cloud still accepts these via `/api/ingest`.

Zone wire values stay `safe` | `watch` | `exit` (UI label for `exit` = **"Don't go"**).

## Cursor / git rules for E3

- Work in `/cloud`. Read `/docs` and `/bus`. Do not write outside `/cloud` without flagging a human.
- Schemas in `04-interfaces.md` are frozen. If a task needs a new message type or renamed field,
  stop and say so — E4 edits `/bus` after the team agrees out loud.
- Short-lived branch `e3/cloud-scaffold` until the 6 PM spine gate; merge to `main` before that
  gate, then trunk-based (`15-dev-workflow.md` §3).
- Commit after every agent turn that changes behavior. Pull before every prompt.
- Human attention goes to ladder timers and ack cancellation — not dashboard polish
  (`15-dev-workflow.md` §7).

## Demo beats that depend on E3

From `05-demo.md`:

1. Dashboard shows agitation rise + `reason` string during pacing.
2. Phone lights up on escalate; judge can pick it up / tap ack link.
3. Morning report closes the 90 seconds.
4. Reset must clear timeline, map, alerts, ladder timers, check-in queue.

Fallback B (sim robot): person tracking, dialogue, **dashboard**, and escalation stay live.
E3's half must work with mocks alone.

## Phone + QR

Same React app in the phone browser — no native app.

1. Tunnel Vite `:5173` with `cloudflared tunnel --url http://127.0.0.1:5173` (or ngrok).
2. Set `VITE_PUBLIC_ORIGIN` (web) and `ACK_BASE_URL` (server) to that HTTPS URL.
3. Dashboard **Share on phone** panel shows QRs for `/` (Night Watch) and `/onboarding`.
4. Caregiver scans onboarding, publishes `config_update`; both screens stay in sync over the bus.

WebSocket uses same-origin `/ws` (Vite proxies to FastAPI) so the tunnel works without hard-coding `:8000`.

## Twilio status

Trial accounts send a **real** SMS but only with Twilio's predefined template names (error 572006
if you send custom text). Keep `TWILIO_TRIAL=1` until you upgrade; then set `TWILIO_TRIAL=0` for
the Arthur headline + ack link in the message body.


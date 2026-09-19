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

## Onboarding fields E3 owns

**Step 3 — risks and home**

- Draw zones: `safe` / `watch` / `exit` (UI label **"Don't go"**), plus `label`, `kind`
  (`door` | `stairs` | `outdoor_boundary`)
- Drop `patient.home` anchor
- Escalation contacts and channels

**Step 4 — schedule**

```json
"schedule": {
  "wake_time": "07:30",
  "meals": ["08:00", "12:30", "18:00"],
  "walk_window": ["15:00", "16:30"],
  "notes": "likes the porch after lunch"
}
```

Both steps emit one `config_update` on the bus.

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

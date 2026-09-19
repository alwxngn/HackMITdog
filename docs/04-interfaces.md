# Interface contracts

**Freeze these by 1:15 PM Saturday — 90 minutes in.** Changes after that need all four engineers
to agree, in the same room, out loud.

Everything moves as JSON over one bus. Use whatever transport is fastest to stand up — Redis
pub/sub, an in-process asyncio queue, or plain WebSockets. The transport is not the point; the
schemas are. Subsystems talk only through these messages, which is what lets all four people
work against mocks from 2:30 PM Saturday.

## Common envelope

Every message:

```json
{
  "type": "person_track",
  "ts": 1758297600.123,
  "source": "robot",
  "seq": 4821,
  "payload": { }
}
```

- `ts` — Unix seconds, float. One clock. If the Jetson and the laptop disagree, fix it at hour 1,
  because debugging causality across skewed clocks at 4 AM is miserable.
- `source` — `robot` | `voice` | `orchestrator` | `cloud` | `mock`
- `seq` — monotonic per source. Makes dropped messages visible instead of mysterious.

## Robot → bus

### `pose` (10 Hz)

```json
{ "type": "pose", "payload": {
  "x": 2.41, "y": 1.08, "theta": 1.57,
  "battery_pct": 68,
  "mode": "standing",
  "map_id": "home_v3"
}}
```

`mode`: `idle` | `standing` | `walking` | `sitting` | `lying`

### `person_track` (10 Hz, when a person is detected)

```json
{ "type": "person_track", "payload": {
  "person_id": "p1",
  "tracker": "overhead_cam",
  "x": 3.02, "y": 0.44,
  "vx": 0.31, "vy": -0.12,
  "heading": 4.31,
  "confidence": 0.86,
  "posture": "standing",
  "zone": "hallway",
  "projected_zone": "front_door",
  "ttz_s": 6.2,
  "lat": null, "lon": null
}}
```

`posture`: `standing` | `sitting` | `lying` | `unknown` — `lying` outside a bed zone is the fall
signal.
`projected_zone` and `ttz_s` (time-to-zone) are E2's linear projection of current velocity.
**The orchestrator triggers on these two fields**, so they matter more than they look.

`tracker`: `overhead_cam` | `lidar_cluster` | `onboard_fusion` | `gps` | `mock` — which sensor
produced this track. **How this message is produced at all is specified in `11-perception.md`**,
which exists because the first draft of this document defined the schema and never said where
the data came from. Render `tracker` in the dashboard: when a judge asks how you track the
person, a live field naming the sensor is a better answer than a description, and it keeps you
honest about which tracker you are actually demoing.

**`gps` (Tier 2, outdoor `FOLLOW`/`GUIDE_HOME` only, see `14-companion-and-caretaker.md` §6–9):**
the source publishes `x`/`y` as metres in a local frame anchored on the home point in
`config_update.patient.home`, exactly like every other tracker, so nothing downstream — the
radius check, the dashboard, the ladder — has to know GPS is involved. `lat`/`lon` are carried
alongside, non-null only for this tracker, purely so the caregiver dashboard can also render a
real map. **Real GPS does not work indoors.** At the venue this is always produced by the
scripted `mock_gps` fixture (source `mock`, `tracker: "gps"` still, so the dashboard is honest
about *which capability* is mocked) — same principle as `mock_robot`, not a lesser version of it.

### `zone_event`

```json
{ "type": "zone_event", "payload": {
  "person_id": "p1", "zone_id": "front_door",
  "zone_class": "exit", "event": "approaching"
}}
```

`zone_class`: `safe` | `watch` | `exit` — caregiver-facing label for `exit` is **"Don't go"**
(matches how a non-technical caregiver thinks about it; not always literally an exit — a
stairway or an outdoor street edge counts too). The wire value stays `exit`; see
`14-companion-and-caretaker.md` §5. Zone definitions in `config_update` gain a `label` and a
`kind` (`door` | `stairs` | `outdoor_boundary`) for this reason.
`event`: `entered` | `exited` | `approaching`

`exited` on a zone with `zone_class: "exit"` is the trigger for escalation ladder step 5
(`02-blueprint.md` §5) — immediate, not the usual 20 s grace, and it's the trigger that opens
the `FOLLOW` state (Tier 2).

### `robot_status`

```json
{ "type": "robot_status", "payload": {
  "command_id": "cmd_882", "state": "executing",
  "detail": null, "distance_to_person_m": 1.94
}}
```

`state`: `accepted` | `executing` | `done` | `failed` | `yielded`

`yielded` is its own state on purpose — the safety envelope aborting a command is a normal,
expected outcome, not an error, and the dashboard should show it as such. A judge noticing
"yielded" in your live log is a good moment for you.

## Voice → bus

### `transcript`

```json
{ "type": "transcript", "payload": {
  "text": "where... where am I supposed to be",
  "is_final": true, "confidence": 0.71,
  "duration_s": 3.4, "speaker": "patient"
}}
```

Interim results (`is_final: false`) are published too — the orchestrator uses them to know
someone is mid-sentence and suppress robot motion.

### `prosody` (every ~2 s while speech is active)

```json
{ "type": "prosody", "payload": {
  "speech_rate_wpm": 142,
  "pitch_var": 0.38,
  "volume_rms": 0.21,
  "baseline_delta": { "rate": 1.31, "pitch_var": 1.9, "volume": 1.12 }
}}
```

`baseline_delta` is the ratio against this patient's rolling 10-minute baseline. **Ratios, not
absolutes** — absolute pitch and volume vary enormously between people and rooms, and the
orchestrator should never see raw values.

### `repetition`

```json
{ "type": "repetition", "payload": {
  "utterance": "when is sarah coming",
  "count": 4, "window_s": 120, "similarity": 0.91
}}
```

Repeated questioning is one of the most reliable agitation markers available to us and it's
nearly free: normalized string similarity over the last N finals.

### `speech_state`

```json
{ "type": "speech_state", "payload": { "state": "speaking", "utterance_id": "u_41" }}
```

`state`: `idle` | `listening` | `thinking` | `speaking` | `interrupted`

`interrupted` means barge-in fired. Log it; it's a quality signal.

## Orchestrator → bus

### `agent_state`

```json
{ "type": "agent_state", "payload": {
  "state": "LEAD",
  "previous": "ATTEND",
  "agitation": "agitated",
  "calm_mode": false,
  "reason": "projected_zone=front_door ttz=6.2s",
  "since_ts": 1758297591.4
}}
```

`state`: `IDLE` | `ATTEND` | `LEAD` | `ESCALATE` | `EMERGENCY` | `WALK` | `FOLLOW` |
`CONFIRM_HOME` | `GUIDE_HOME` — the last four are Tier 2 (`02-blueprint.md` §4,
`14-companion-and-caretaker.md` §6–7). `WALK` and `FOLLOW` share the exact same downstream
handling as `LEAD`/`ESCALATE` for the safety envelope (yield rule, distress override); they're
new *entry points and severities*, not a new safety model.
`agitation`: `calm` | `unsettled` | `agitated`

**`reason` is a required human-readable string, always.** It's what renders in the dashboard
timeline, and being able to point at the screen and say "that's why it did that" is the single
best answer to "how do we know it isn't random?" Populate it properly even when you're rushing.

### `command` (to robot)

```json
{ "type": "command", "payload": {
  "command_id": "cmd_883",
  "action": "lead_to",
  "args": { "zone_id": "bedroom", "speed_max": 0.3, "standoff_m": 1.5 }
}}
```

`action`: `goto` | `lead_to` | `approach_person` | `posture` | `yield` | `stop` | `follow_person` |
`guide_home`

`approach_person` implies the full envelope — front sector, standoff, speed cap, announce
first. E2 enforces it in the controller. The orchestrator is not trusted to enforce safety;
the layer closest to the motors is.

`follow_person` (Tier 2) — track at distance, matching pace, **never closing to lead-away
standoff or blocking distance.** This is the `FOLLOW` state's only robot-facing command; it
carries no destination, only a person to track. `guide_home` (Tier 2) — navigate to
`config_update.patient.home` (or a `route_id` if a preferred route was set). E2 enforces the
same envelope as `approach_person` on the way — announce, standoff, speed cap — because guiding
someone home is still moving alongside a person, not autonomous point-to-point robotics.

### `say` (to voice)

```json
{ "type": "say", "payload": {
  "utterance_id": "u_42",
  "text": "It's night time, Arthur. Let's go back to bed.",
  "voice_id": "sarah_clone_v1",
  "tone": "soothing",
  "interruptible": true,
  "attribution": "Sarah recorded this for you",
  "origin": "policy"
}}
```

`tone`: `neutral` | `warm` | `soothing` — maps to ElevenLabs stability/style settings.

`interruptible` is `true` by default and should essentially always stay true.

`attribution` is nullable but **present in the schema on purpose**: it's the anti-impersonation
rule encoded in the interface rather than left to a prompt. When a judge asks how you prevent
the robot from pretending to be someone's daughter, "it's a required field in our message
schema" is a much better answer than "we told the model not to."

`origin`: `policy` | `companionship` | `reminder` | `checkin` | `reflex` (Tier 1, additive,
defaults to `policy`) — labels *why* the robot spoke, for the dashboard timeline and for the
reminder-suppression rule below. It does not change how `say` is rendered or guarded; the
impersonation filter runs on every origin identically.

**Check-in relay reuses this schema exactly.** A caregiver's message arrives as a `checkin`
message (cloud → bus, `{ "checkin_id", "from_name": "Michael", "text": "..." }`), and the
orchestrator turns it into a `say` with `attribution: "Michael sent you this message"` and
`origin: "checkin"` — no new voice pipeline, no new consent surface. It's queued and only
delivered while `agent_state` is `IDLE` or a conversational sub-state; it never interrupts
`LEAD` / `ESCALATE` / `EMERGENCY`. **Reminders** (`origin: "reminder"`) work the same way, timed
against `patient.schedule` (below) instead of arriving from the cloud, and are suppressed
entirely — not queued, dropped — outside `IDLE`.

### `alert` (to cloud)

```json
{ "type": "alert", "payload": {
  "alert_id": "al_19", "level": 2,
  "headline": "Arthur is heading for the front door",
  "detail": "Redirection attempted for 20s. He's in the hallway, 2m from the door.",
  "person_position": { "x": 3.4, "y": 0.2, "zone": "hallway" },
  "requires_ack": true, "channels": ["sms", "push"],
  "context": "night_breach", "live_tracking": false
}}
```

`level` maps to the ladder in `02-blueprint.md` §5. `channels` gains `voice_call` at level 3.

Write `headline` the way you'd want to read it at 2 AM: the person's name, in plain words, no
jargon. "Arthur is heading for the front door" — not "ZONE_BREACH_IMMINENT: front_door."

`context` (Tier 2, additive): `night_breach` | `day_walk_separation` — same underlying
`FOLLOW`/live-location mechanism, different urgency framing. A `night_breach` alert is level 5,
`requires_ack: true`, `channels` includes `voice_call` immediately rather than after 60 s. A
`day_walk_separation` alert is a low-severity push, `requires_ack: false` — it's a location
ping, not a page. `live_tracking: true` tells the dashboard to switch the map into continuous
streaming mode for the duration of the episode instead of rendering a single pin
(`02-blueprint.md` §3, Pillar 3).

## Cloud → bus

### `caregiver_ack`

```json
{ "type": "caregiver_ack", "payload": {
  "alert_id": "al_19", "by": "jenny", "action": "im_coming"
}}
```

`action`: `im_coming` | `handled` | `false_alarm` | `call_help`

`false_alarm` is deliberately included. It's both an escape hatch for a caregiver and a
training signal, and a judge asking "how do you handle false positives?" gets a concrete
answer instead of a shrug.

### `config_update`

```json
{ "type": "config_update", "payload": {
  "zones": [ { "id": "front_door", "class": "exit", "label": "Don't go", "kind": "door",
               "polygon": [[3.1,0.0],[4.2,0.0],[4.2,1.1],[3.1,1.1]] } ],
  "escalation": [
    { "level": 2, "contact": "jenny", "channel": "sms",        "after_s": 0  },
    { "level": 3, "contact": "jenny", "channel": "voice_call", "after_s": 60 },
    { "level": 4, "contact": "mark",  "channel": "voice_call", "after_s": 120 },
    { "level": 5, "contact": "jenny", "channel": "voice_call", "after_s": 0, "trigger": "dont_go_breach" }
  ],
  "voice": { "voice_id": "sarah_clone_v1", "consent_recorded_ts": 1758290000.0,
             "attribution_name": "Sarah" },
  "patient": { "name": "Arthur", "preferred_name": "Art",
               "calming_topics": ["fishing at Moosehead", "his dog Bella"],
               "avoid_topics": ["his wife's death"],
               "music_url": "/media/arthur_playlist.mp3",
               "schedule": { "wake_time": "07:30", "meals": ["08:00","12:30","18:00"],
                             "walk_window": ["15:00","16:30"], "notes": "likes the porch after lunch" },
               "home": { "x": 0.0, "y": 0.0, "lat": null, "lon": null },
               "route_id": null }
}}
```

**`consent_recorded_ts` is required before any cloned voice can be used.** The orchestrator
refuses `say` commands carrying a `voice_id` with no consent timestamp. Enforced in code, not
in policy — again, a much better answer to the ethics question.

**`patient.schedule`** (Tier 1, additive) drives the reminder engine in `04-interfaces.md`'s
`say.origin: "reminder"` — one onboarding field turning proactive nudges from hard-coded timers
into something driven by the actual person (`14-companion-and-caretaker.md` §3–4).

**`patient.home`** (Tier 2) is the anchor `guide_home` navigates to. `lat`/`lon` are populated
only if a real outdoor deployment has them; at the venue `x`/`y` (metres from the taped area's
origin corner) is all that's used. **`patient.route_id`** (Tier 2, optional) points at a
caregiver-drawn preferred walking route; point-to-point `guide_home` works with this left
`null` — a route is an enhancement on top of a working "go home," not a prerequisite for it.

**Escalation ladder level 5** fires immediately (`after_s: 0`) on `trigger: "dont_go_breach"`
rather than waiting on a timer like levels 2–4 — see `02-blueprint.md` §5.

## Mocks (E4, by 2:30 PM Saturday)

Three fakes that let everyone else work, plus a fourth added for the Tier 2 outdoor features:

- **`mock_robot`** — accepts every `command`, emits plausible `pose` and `robot_status`. Has a
  `--fail-rate` flag so the orchestrator's failure paths get exercised before the night shift.
- **`mock_patient`** — emits `person_track` along a scripted path. Ships with named scenarios:
  `calm`, `pacing`, `exit_seeking`, `fall`. Everyone develops against `exit_seeking`.
- **`mock_mic`** — replays recorded WAVs into the voice pipeline, so the voice path is testable
  without a human talking into a laptop in a loud room at hour 3.
- **`mock_gps`** (Tier 2, built only after the above three are solid) — emits `person_track`
  with `tracker: "gps"` along a scripted outdoor scenario: walk out, wander, drift past the
  follow radius, respond to a `"take me home"` transcript. **Not a lesser mock** — real GPS
  cannot be tested at the venue at all, so this is how `FOLLOW`/`CONFIRM_HOME`/`GUIDE_HOME` get
  demoed, full stop. See `14-companion-and-caretaker.md`'s GPS section.

Each runs standalone from the command line. Each has to work before anyone is allowed to say
they're blocked on hardware.

## The rules

1. **Nothing bypasses the bus.** No direct calls between subsystems, however tempting at 2 AM.
   The one time someone does it is the one time you can't debug it.
2. **Unknown fields are ignored, never fatal.** Additive changes must not break anyone.
3. **Every message is logged to a JSONL file.** This gives you replay for debugging, the morning
   report, and your evaluation data, all for free. Set it up in the first two hours and it pays for itself
   five times.
4. **The dashboard renders from the bus only.** If it needs a demo-specific hack to look right,
   it isn't actually working.

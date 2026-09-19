# Companion & caretaker features — the second half of the pitch

Added after a team discussion. Everything in `02-blueprint.md` so far is built around a single
scenario: one bad night. That's still the strongest safety story available, and nothing here
replaces it. But it leaves out the thing families actually live with every day, and it leaves
out the specific criticism that follows any AI-driven quadruped around right now: **a robot dog
that does tricks is a novelty that wears off in about three weeks**, because there's no ongoing
relationship behind it. The fix isn't a separate "companionship mode" bolted on — it's that the
same profile driving the safety envelope also drives a robot that remembers your son's name,
asks about your garden, and reminds you to drink water. One relationship, two situations.

**Say this right after the 2 AM story:** *"The reason this isn't just a safety gadget is that
it's the same robot, same profile, same voice, at 3 PM asking about her roses as at 2 AM
walking her back to bed. Families don't want two devices — one for the emergency and one for
the loneliness. They want one relationship."*

This document specs the features from that discussion, tiers them against the 24-hour clock in
`10-second-pass.md` (P0-4 already warned you about scope), and closes one real gap in the
original plan: the old policy stopped at "escalate" and never said what the robot does if the
person actually walks out the door.

## Sorting the ask into caretaker-side and patient-side

| Caretaker does | Patient experiences |
|---|---|
| Onboarding: name, calming topics, schedule and habits | Companionship conversation: family, self, setting |
| Draws zones by field-mapping: `safe` / `watch` / **`dont_go`** | Encouragement to exercise, hydration/food nudges, "here's some news" |
| Sets home location, optionally a preferred walking route | Check-in relay: *"Your son sent you this message: ..."* |
| Gets a live map the moment a `dont_go` breach happens | Warned, never blocked, if heading for the door anyway |
| Gets streaming location once the robot is following outdoors | Followed at a distance if they leave, not stopped |
| Gets a routine location ping during a voluntary walk | Walked alongside during exercise, followed if separated |
| — | Can say "take me home" any time; robot re-confirms, then guides back |

Nine items. Read `01-judge-review.md` P0-4 again before you build all nine at once — the fix
there ("one spine, everything else explicitly tiered") applies exactly as much to this list as
it did to the original one.

---

## 1. Check-in relay (cheap, Tier 1)

A caregiver types or records a short message in the portal. The robot delivers it in the
patient's own session, attributed, exactly like the existing voice-consent mechanism already
does for the cloned voice:

> *"Your son sent you this message: 'Hi Mom, thinking of you today, I'll call after dinner.'"*

This is not a new architecture — it's the `say` schema's `attribution` field (`04-interfaces.md`)
doing one more job. The anti-impersonation guard already in `12-dialogue-runtime.md` applies
unchanged: the robot relays what Michael said, it never speaks *as* Michael. Text-to-speech can
use the neutral robot voice or, if there's time, the sender's own consented voice clip — same
consent gate as the primary family voice, no new ethics surface.

**Build:** a `checkin` message from cloud → orchestrator → `say`, queued and delivered next time
the patient is in `IDLE` or a conversational state (never interrupts `LEAD`/`ESCALATE`/`EMERGENCY`
— a check-in is not more important than a safety event). Twenty minutes of orchestrator work,
five minutes of portal UI (one text box, one send button).

## 2. Companionship conversation (cheap, Tier 1)

Right now the dialogue policy in `02-blueprint.md` §3 is written entirely for de-escalation. Most
of the day, nobody is agitated — they're just alone, and the robot should be able to hold an
ordinary conversation. This is the same Tier 2 LLM in `12-dialogue-runtime.md`, given three more
things in its context:

- **Family** — names and relationships from the onboarding profile (`config_update.patient`).
- **Self** — biographical anchors the family provides: where they grew up, what they did for
  work, a hobby. Same list that already feeds `calming_topics`, reused for a different purpose.
- **Setting** — ambient orientation facts the robot always knows: today's date, the weather if
  available, what room they're in. This overlaps with the existing "orient gently, unprompted"
  policy rule — it's the same rule, running proactively instead of only during agitation.

The same six policy rules from `02-blueprint.md` §3 still apply without modification: never
correct, never test memory, one idea per utterance, answer repetition as if new, never
impersonate. Companionship mode is not a new policy — it's the existing policy, running more
often, on lower-stakes material.

**Build:** extend the system prompt template with three new profile fields, extend
`config_update.patient` in `04-interfaces.md` (below). No new runtime component.

## 3. Onboarding v2 — schedule and habits (cheap, Tier 1)

`02-blueprint.md` §3's onboarding step 1 already asks "what calms them." Add a fourth question:
**their day.** Wake time, meal windows, a usual walk time, anything they do reliably. This
single field is what makes reminders (§4) and the walk feature (§6) anything other than
hard-coded timers.

```json
"schedule": {
  "wake_time": "07:30",
  "meals": ["08:00", "12:30", "18:00"],
  "walk_window": ["15:00", "16:30"],
  "notes": "likes the porch after lunch"
}
```

For the demo, this can be three sliders and a text box. Nobody is judging the onboarding UI's
polish; they're judging whether the reminder that fires later is clearly driven by it.

## 4. Proactive reminders (cheap, Tier 1) — exercise, water, food, "share the news"

A scheduler that checks the patient's `schedule` against wall-clock time and, when the window
opens and the robot isn't in a safety state, emits a gentle prompt through the same `say`
pipeline: *"It's about time for lunch."* / *"Want to sit outside for a bit?"* / *"Have you had
water recently?"*

**Cut "share the news" down to something buildable in an hour:** a live news API is a fourth
external dependency for a feature nobody is scoring you on. Ship a small rotating set of
low-stakes, calming conversation-starters instead — a fact about their hobby, a question about
their garden, a line about the season — and call it what it is on the slide: *"conversation
prompts, not headlines."* If there's real spare time in Tier 2, swap in one calm, pre-filtered
headline category (weather, local interest) — never anything that could read as distressing.

**Rule, same as everything else in this repo:** reminders are suggestions, not commands, and
they yield to a safety state immediately. `agent_state != IDLE` suppresses the reminder queue.

## 5. Zone field-mapping — rename `exit` to `dont_go` (trivial, Tier 1)

The caregiver-facing label for the zone class currently called `exit` becomes **"Don't go"** in
the onboarding UI, matching how a non-technical caregiver actually thinks about it — a zone
isn't always literally an exit (it might be "the basement stairs" or, outdoors, "the road").

**Keep the wire value as `exit` internally** (it's already used throughout `04-interfaces.md`,
`06-safety-ethics.md`, and the review docs) and add the caregiver-facing label as metadata:

```json
{ "id": "front_door", "class": "exit", "label": "Don't go", "kind": "door" }
```

`kind`: `door` | `stairs` | `outdoor_boundary` — lets the same three-tier zone system
(`safe` / `watch` / `exit`) cover both the indoor demo (front door) and the outdoor walk feature
(yard edge, street) without inventing a second zone schema.

## 6. The wandering policy, completed — follow, live location, guide home

This is the real gap `01-judge-review.md` and `06-safety-ethics.md` left open. The existing
policy is exhaustive right up to the door and silent after it:

> escalate → the robot stays and keeps company

That's correct for a person still inside. It says nothing about a person who actually leaves,
and the team was right to flag that as incomplete. The completed policy:

1. **Warn.** Unchanged — announce, approach within the envelope, invite, lead away. Never block.
2. **If they leave anyway, the robot does not follow *into* the doorway confrontationally — it
   follows *after*, at distance, through the door they chose to open.** This is still "lead,
   don't block": nothing about following someone at a respectful distance restrains them.
3. **Contact emergency contacts immediately on the breach** — this is `alert` level 3/4 firing
   the moment `zone_event: exited, zone_class: exit` is seen, not waiting another 20 seconds.
   A person who has actually left the house is a materially different situation from one still
   pacing the hallway, and the ladder should reflect that severity jump.
4. **Stream live location to the emergency contact continuously**, not as a one-time alert. This
   is a real, ongoing `pose`/`gps_position` feed to the dashboard for the duration of the
   episode — the caregiver should be able to watch the dot move, not just receive a single pin.
5. **Keep talking, keep offering to help, never coerce.** The robot's speaker keeps redirecting
   ("It's cold out, let's go back") without ever physically closing the standoff distance to
   force compliance.
6. **On "take me home," or on the person agreeing to turn back, re-confirm once — "Would you
   still like to go home?" — then guide.** The re-confirmation matters ethically as much as
   practically: it's the same principle as the yield rule, applied to navigation instead of
   proximity. The robot never marches someone home on a stale intent; it checks again, in the
   moment, before acting.

## 7. Guided walks — the same capability, a friendlier trigger

The daytime "go for a walk" feature is **not a second navigation stack.** It's the same
follow-and-guide-home machinery from §6, entered through a welcome door instead of a forced one:

| | Night wandering (§6) | Day walk (this section) |
|---|---|---|
| Entry | `dont_go` zone breach, unwanted | Patient or caregiver-initiated, wanted |
| Robot's role while together | Lead away from danger | Walk alongside, no destination imposed |
| On separation | N/A — robot is already following | Radius check trips → `FOLLOW` |
| On "take me home" | Re-confirm → guide | Re-confirm → guide |
| Caregiver alert severity | High — immediate multi-channel | Low — a location ping, not a page |

The patient doesn't have to follow a set route. They walk wherever; the robot tracks whether
they're inside a following radius (a few meters) and only actively "follows" (closing distance,
matching pace) if they drift outside it — otherwise it's just walking together. If the radius is
broken and stays broken, the state machine below moves to `FOLLOW` and starts the caregiver
location-ping stream from §6 step 4, same mechanism, lower urgency framing. When the patient is
ready, "take me home" (or a caregiver override, but the patient's voice always takes priority)
triggers the same re-confirm → `GUIDE_HOME` transition.

**Building one shared capability instead of two is the point to make out loud:** *"We built
'follow and guide home' once. It's the thing that gets a lost patient home safely at night, and
it's the same thing that lets her go for a walk without a fixed route during the day. That's
one state machine, not two products."*

## 8. Set home / set a route (cheap for "home," Tier 2 for "route")

**Home** is a single anchor point — indoors, the taped area's origin corner; outdoors,
whatever coordinate frame the navigation stack uses (see the GPS caveat below). One field in
`config_update`, set once during onboarding. Cheap.

**A preferred route** (an ordered list of waypoints the caregiver draws, e.g. "the block she
always used to walk") is real scope: a route-following controller, replanning around obstacles,
and a UI to draw it. Tier 2, and only worth it if `GUIDE_HOME` (point-to-point) is already
solid — a route is a nice-to-have on top of a working "go home" capability, not a prerequisite
for one. If it doesn't get built, the honest line is *"the patient can walk wherever; going
home always works; a fixed preferred route is the obvious next step."*

## The GPS problem, said out loud before a judge finds it

**GPS does not work indoors, at all — not badly, not intermittently, not at all.** A convention
hall has no sky view. This means the outdoor half of this feature (§6 steps 3–7, §7) **cannot
be demonstrated live at the venue with real GPS**, for the same structural reason `05-demo.md`
already ruled out live SLAM: the venue is not the environment the feature is designed for.

This is not a reason to cut it from the pitch — it's a reason to demo it exactly the way the
existing plan already demos indoor tracking: **behind the schema, with a mock producing the
signal.** A `mock_gps` scenario emits a scripted `gps_position` stream (walk away from home,
wander, drift outside the radius, respond to "take me home") exactly the way `mock_patient`
already scripts `person_track`. The orchestrator, the `FOLLOW`/`GUIDE_HOME` states, the
dashboard's live map, and the caregiver alert all run against that mock identically to how they'd
run against a real GPS module outdoors. Say the sentence: *"Real GPS doesn't work inside a
convention center — nothing does. What you're seeing is the same orchestrator and the same
dashboard running against a scripted location feed, exactly like our indoor demo runs against a
mocked robot when the hardware's charging."* That's a strength, not a hedge — it's the schema
argument from `04-interfaces.md` applied a second time.

---

## Tiering — where these nine items land in `02-blueprint.md` §6

| Feature | Tier | Why |
|---|---|---|
| Check-in relay | **1** | Reuses `say` + `attribution`. No new architecture. |
| Companionship conversation | **1** | Three more prompt fields on an LLM tier that already exists. |
| Onboarding: schedule & habits | **1** | Extra onboarding fields, no new runtime. |
| Reminders (water/food/walk prompt, conversation starters) | **1** | A timer against a schedule; suppressed by `agent_state`. |
| Zone label rename (`dont_go` display, `kind` field) | **1** | Metadata addition to an existing schema. |
| Wandering completion: breach alert severity, continuous location stream | **1** | Closes a real gap; mostly wiring that already exists (`alert`, `pose`) differently. |
| `FOLLOW` state, re-confirm, `GUIDE_HOME` (mocked GPS) | **2** | New states, new mock, genuinely novel work. Build once the Tier 0 spine is green. |
| Day-walk entry into the shared follow/guide-home machinery | **2** | Depends entirely on the above existing first. |
| Preferred route (vs. point-to-point home) | **2, optional** | Nice-to-have on top of a working point-to-point `GUIDE_HOME`. |

Everything in Tier 1 here is genuinely cheap — mostly additive fields on schemas that already
exist, which is exactly the kind of scope this plan can absorb without threatening the spine.
The Tier 2 row is real new work and should be treated with the same discipline as any other
Tier 2 item in `02-blueprint.md` §6: build it after the spine is green, cut it cleanly if it
isn't, and never let it be the thing the climax depends on.

## What this changes elsewhere

- `02-blueprint.md` — pillars, state machine, escalation ladder, and the tier list all get the
  additions above.
- `03-build-plan.md` — ownership gains a line each for E1 (companionship prompt, check-in relay,
  reminders), E2/E4 (`FOLLOW`/`GUIDE_HOME`, `mock_gps`), E3 (schedule/habits fields, zone label,
  live map during `FOLLOW`, home/route setting).
- `04-interfaces.md` — new message types and field additions, listed in full there.
- `06-safety-ethics.md` — the completed wandering policy and the re-confirmation rule are safety
  policy, not features, and belong in the envelope table.
- `05-demo.md` and `09-judge-qa.md` — the GPS-mock explanation above is a rehearsed line, not an
  improvised one.

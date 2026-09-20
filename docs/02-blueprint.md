# Lantern — revised blueprint

## 1. The pitch

> A person with mid-stage dementia gets out of bed at 2 AM, disoriented, and starts toward the
> front door. Today, the family finds out when the door alarm goes off — too late, with no
> context, from a dead sleep. Lantern is a quadruped companion that is already in the room. It
> notices the pacing before the door, puts itself in front of the person where they can see it,
> speaks in a familiar voice, and walks slowly back toward the bedroom so that following it is
> the easiest thing to do. If that doesn't work within twenty seconds, the caregiver's phone
> rings — with a map, a timeline, and a photo of where their father actually is.

**What we are not claiming:** that a robot replaces a caregiver, that we can treat dementia, or
that this is a medical device. Lantern buys a caregiver time and information at the moment
both are scarcest.

**The second half of the pitch, said right after the first:** the reason this isn't just a
safety gadget bolted onto a quadruped is that it's the same robot, running off the same
profile, at 3 PM asking her about the roses in her garden as it is at 2 AM walking her back to
bed. AI companion dogs have a real, known failure mode right now — a robot that does tricks is
a novelty that wears off in about three weeks, because there's no relationship behind it.
Families don't want two devices, one for the emergency and one for the loneliness. Lantern is
built to be one relationship that happens to also be watching the door. `14-companion-and-caretaker.md`
specs the companionship and caretaker features this adds; nothing below changes because of it —
the 2 AM story is still the strongest thing we have.

## 2. Why this and not the alternatives

| Existing approach | Why it falls short |
|---|---|
| Door/bed alarms | Fire at the threshold, which is already too late. No context: the caregiver wakes to a beep and has to find out everything themselves. High false-alarm rate leads families to disable them. |
| GPS trackers and wearables | Reactive by design — they help you find someone who is already outside and lost. Also frequently removed or forgotten, which is precisely the symptom. |
| Cameras | Passive. A camera can watch someone walk out the door but cannot intervene, and families balk at surveillance framing. |
| Smart speakers | Screenless, which is right, but fixed in place and unaware. Cannot be present where the person is, cannot see, cannot lead. |
| PARO and companion robots | Real evidence for calming, no mobility, no awareness, no caregiver link. |
| Memory care facility | $5–8k/month in most US survey data, and the outcome families are trying to postpone. |

The gap Lantern occupies: **present at the moment of confusion, mobile, screenless, and
connected to the caregiver.** No existing product sits in all four.

This table compares categories, which is not enough — a healthcare judge will name an actual
product, most likely **ElliQ** or **Sensi.AI**. `13-landscape.md` names eight of them with the
one-line differentiator for each. Read it before you pitch.

## 3. The three pillars (down from four)

```
                         ┌──► 1. Voice — Conversation & Companionship  (Deepgram + ElevenLabs)
[Unitree Go2 + Jetson] ──┼──► 2. Night Watch, Lead-Away & Guided Walks (DimOS + LiDAR SLAM +
                         │                                              odometry breadcrumb retrace)
                         └──► 3. Caregiver Link                        (React + FastAPI + Twilio)

                              Calm Mode is a behavior inside pillars 1+2, not a pillar.
                              Companion/caretaker feature specs: `14-companion-and-caretaker.md`.
```

### Pillar 1 — Familiar-voice conversation and companionship

Two jobs, same voice stack, same profile. Most of the day this is companionship, not
de-escalation: **answering questions about family, about the person themselves, about where
they are** — "when is Sarah visiting," "what did I do for work," "what day is it" — using the
same onboarding profile that feeds `calming_topics`. The six policy rules below apply
unchanged; companionship isn't a separate mode, it's the same policy running more often, on
lower-stakes material. Two additions on top of ordinary conversation, both cheap (Tier 1, see
`14-companion-and-caretaker.md`):

- **Check-in relay.** A family member sends a short message from the portal; the robot delivers
  it attributed — *"Your son sent you this message: ..."* — using the exact same `attribution`
  field and impersonation guard already built for the cloned voice. No new ethics surface.
- **Gentle proactive nudges.** Water, food, and a walk, timed against the patient's own schedule
  from onboarding (`patient.schedule`), suppressed the instant the robot is in a safety state.
  "Share the news" ships as a small set of calm conversation-starters, not a live news feed —
  nobody needs a fourth external API for a feature this low-stakes.

**Deepgram streaming STT**, tuned for the speech this population actually produces: quiet,
mumbled, mid-sentence restarts, long pauses that must not be read as end-of-turn, and the same
question asked four times. Practical requirements:

- Endpointing tuned long. Dementia speech has long internal pauses; a standard 500 ms
  end-of-turn cuts people off mid-thought, which is exactly the frustration we're claiming to
  remove.
- Barge-in supported. If the person starts talking, the robot stops talking. Always.
- Interim results drive the "is anyone talking" state so the robot doesn't move while the
  person is mid-sentence.

**ElevenLabs TTS** using a consented family voice, with a dialogue policy built on validation
therapy rather than correction:

| Rule | Bad | Good |
|---|---|---|
| Never correct a false belief | "No, Mom died in 2009." | "You're missing her. Tell me about her." |
| Never test memory | "Don't you remember? We talked about this." | "It's Tuesday night. You're at home." |
| One idea per utterance | "Let's go back to bed, it's late, and remember you have your appointment tomorrow so you need rest." | "It's late. Let's go back to bed." |
| Answer repetition as if new | (irritated tone on the fourth ask) | Same calm answer, same words, every time. |
| Orient gently, unprompted | — | "It's night time. You're home. I'm here." |
| Never impersonate | "Dad, it's Sarah." | "Sarah recorded this for you." |

These rules go in the system prompt verbatim, and the prompt goes on a slide. The dialogue
policy is a legitimate design contribution and it costs nothing to show.

But a prompt is not a runtime and it is not a guarantee. **`12-dialogue-runtime.md` specifies
what actually produces each utterance** — reflex lines that never touch the network, a cache
for the things this user says most, the model for everything else — plus the latency budget and
the impersonation guard, which is code on both sides of the model rather than an instruction
inside it.

Emotional inflection is driven by a coarse agitation state (`calm` / `unsettled` / `agitated`)
rather than a continuous signal — slower, lower, shorter as agitation rises. Coarse is more
robust and easier to demo.

### Pillar 2 — Night Watch, lead-away, and guided walks

Four capabilities, in order of importance:

**a. Zones.** A map of the home with caregiver-drawn zones: `safe`, `watch`, `exit`. Field-mapped
by the caregiver during onboarding — walk the phone or laptop around the space, drop points, or
draw on the floorplan image. The caregiver-facing label for `exit` is **"Don't go"**, since it
covers more than the front door (stairs, a busy street edge outdoors); the wire schema keeps
the `exit` value, see `14-companion-and-caretaker.md` §5. For the demo this is a small
pre-authored map, not live SLAM in the venue (see `05-demo.md`).

**b. Pre-wandering detection — the technically novel part.** The robot's own navigation stack is
the sensor. Two signals fused:

- *Trajectory:* the person's tracked position over a rolling 90-second window. Repeated
  traversal of the same corridor segment in alternating directions is the classic pacing
  pattern. Detected as ≥3 direction reversals along a path segment within the window, with
  cumulative distance above a floor to reject jitter.
- *Prosody and repetition:* speech rate and volume trend from the audio stream, plus
  repeated-question detection via normalized string similarity over the last N utterances.

Fused into the three-level agitation state. Every input is data we already have; no added
hardware, no added failure mode.

**c. The lead-away policy.** Replaces "physical intercept" entirely. See
`06-safety-ethics.md` for the full safety envelope; the shape of it:

1. **Notice.** Agitation state rises, or the person's heading projects into an `exit` zone.
2. **Announce.** Speak from current position, before moving. No silent approach in the dark.
3. **Position.** Move to a point ahead of the person and off to one side — inside their field
   of view, never in the doorway, never closer than 1.5 m, capped at 0.3 m/s.
4. **Invite.** Familiar voice, single short sentence. "It's night time. Come with me."
5. **Lead.** Move slowly *away* from the exit and toward the safe zone, pausing to check that
   the person is following. Following a moving thing is close to automatic; being blocked is
   an insult.
6. **Yield.** If the person advances within 1.2 m or keeps heading for the exit, the robot gets
   out of the way. It does not win the physical interaction, ever.
7. **Escalate.** 20 seconds without redirection → caregiver link fires. The robot keeps talking
   and keeps the person company while help comes. Being there is still worth something even
   when the redirect fails.

**The policy used to stop there — silent on what happens if the person actually leaves. It
doesn't anymore (Tier 2, breadcrumb retrace, demoable live; see `14-companion-and-caretaker.md`
§6):**

8. **If they leave anyway, the robot follows — after them, through the door they opened, never
   into it.** Following at a respectful distance is not blocking; nothing about it restrains
   anyone. The severity of the caregiver alert jumps immediately on the breach — this is no
   longer "wait 20 seconds," it's "notify now."
9. **Live location streams to the emergency contact continuously** for the duration of the
   episode — a moving dot on the dashboard, not a single pin.
10. **On "take me home," or on the person agreeing to turn back, the robot re-confirms once —
    "Would you still like to go home?" — then guides.** Same principle as the yield rule, applied
    to navigation: the robot never acts on stale intent, it checks again in the moment.

**d. Guided walks — the same capability, entered through a welcome door.** During the day, the
patient can go for a walk with no fixed route: the robot walks alongside, tracks whether they're
inside a following radius, and only closes distance and starts location-pinging the caregiver
if that radius breaks and stays broken. "Take me home," any time, triggers the identical
re-confirm-then-guide sequence as step 10 above — it is the same state machine as the nighttime
completion, entered voluntarily instead of by a `dont_go` breach, and alerted to the caregiver
at ping severity instead of page severity. One navigation capability, two triggers — see
`14-companion-and-caretaker.md` §7 for the full comparison table.

**e. How the robot spends the night.** A Go2 runs 1–2 hours on the standard battery, 2–4 on the
EDU's long-life pack. A night is eight. So Lantern is *not* a robot that patrols all night — it
is **docked and asleep, woken by an event**:

- It spends the night on a charging dock in a low posture, locomotion idle.
- What stays awake is the cheap part: the microphone, and a bed-exit signal.
- A wake trigger brings it up, the state machine above runs, and after ten minutes it returns
  to the dock. Two or three ten-minute episodes is comfortably inside one charge.

**Say this unprompted**, because otherwise a judge does the battery arithmetic and concludes we
didn't. The dock is a commodity part Unitree already sells and we didn't build one; the bed-exit
trigger — a pressure mat or a bedside PIR, about $20 — is the obvious next integration and is
out of scope for 24 hours. Framed this way the battery number argues *for* the architecture
instead of being a hole in it.

**Calm Mode** is a behavior that can run at any point from step 3: robot lowers to a still
posture, personalized music at low volume, warm dimmed light, slow validating speech. Modeled
on PARO and personalized-music interventions. Not claimed to be clinically effective — say so
out loud.

### Pillar 3 — Caregiver link

**Onboarding, four steps, designed to be completed by a stressed 55-year-old at 11 PM:**

1. *Who are we caring for?* Name, what to call them, the things that reliably calm them
   (a song, a place, a person), and what not to bring up.
2. *Whose voice?* The family member records 30 seconds themselves, behind an explicit consent
   checkbox naming the use. Off by default until recorded.
3. *Where are the risks, and where's home?* Draw zones on the floorplan by field-mapping —
   `safe`, `watch`, `dont_go` (wire value `exit`, see Pillar 2a). Drop the home anchor point.
   Set the escalation ladder: who gets called, in what order, after how long. A preferred
   walking route is optional and Tier 2 — point-to-point "take me home" ships first and works
   without one.
4. *What's their day?* Wake time, meal windows, a usual walk time. This one field is what turns
   the exercise/water/food nudges in Pillar 1 from hard-coded timers into something driven by
   the actual person (`14-companion-and-caretaker.md` §3–4).

**Night Watch dashboard:** live map with person and robot position, current state, event
timeline, and the escalation ladder with a big visible "acknowledged" control so a caregiver
can say "I've got it" from bed and stop the phone tree. **During a `dont_go` breach or a
separated walk, the map goes live-tracking** — a moving dot, streamed continuously, not a
one-time pin — at page severity for a breach and ping severity for a daytime walk separation
(`14-companion-and-caretaker.md` §6–7).

**The morning report is the sleeper feature.** The thing a caregiver actually wants is not a live
map at 3 AM — it's to wake up and see: *two events overnight, both resolved by redirection,
he was up for eleven minutes at 2:14 and went back to bed.* That is the artifact that makes a
family trust the device enough to keep it, and it's cheap to build because it's just a query
over your event log. Show it at the end of the demo. Judges consistently respond to it because
it's the only part of the product that acknowledges the caregiver is a person who sleeps.

**Escalation** runs over Twilio. Important detail: **SMS is the wrong primary channel for a 2 AM
emergency** — phones are on silent, texts don't wake people. Ladder is: push/SMS with the
event, then a Twilio *voice call* after 60 seconds if unacknowledged, then the secondary
contact. Mention this at the table; it signals you thought about the actual moment rather than
the happy path.

## 4. System architecture

```
                    ┌──────────────── ORCHESTRATOR (E4) ────────────────┐
                    │   state machine · event bus · policy · metrics    │
                    └───┬──────────────┬───────────────┬────────────────┘
                        │              │               │
          ┌─────────────┘              │               └──────────────┐
          ▼                            ▼                              ▼
  ┌───────────────┐          ┌──────────────────┐            ┌────────────────┐
  │ VOICE (E1)    │          │  ROBOT (E2)      │            │ CLOUD (E3)     │
  ├───────────────┤          ├──────────────────┤            ├────────────────┤
  │ Deepgram STT  │          │ DimOS / Unitree  │            │ FastAPI + WS   │
  │ dialogue pol. │          │ SLAM + zones     │            │ React portal   │
  │ ElevenLabs TTS│          │ lead-away ctrl   │            │ Twilio ladder  │
  │ prosody feats │          │ pacing detector  │            │ event store    │
  └───────────────┘          └──────────────────┘            └────────────────┘
          │                            │                              │
          └──────────── all speak the schemas in 04-interfaces.md ────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │  MOCKS (E4, live by 2:30 PM)        │
                    │  fake robot · fake patient · fake   │
                    │  mic — everyone tests without HW    │
                    └─────────────────────────────────────┘
```

The orchestrator is the product. Everything else is a driver behind a schema. This is what
makes the four-way parallelism work and it's what was missing from the original plan.

### The state machine

```
                  ┌──────────┐
      ┌──────────►│   IDLE   │◄─────────────┐
      │           └────┬─────┘              │
      │  resolved      │ agitation ≥ unsettled
      │                ▼                    │
      │           ┌──────────┐              │ resolved / caregiver ack
      │           │ ATTEND   │  approach + announce + converse
      │           └────┬─────┘              │
      │                │ heading → exit zone│
      │                ▼                    │
      │           ┌──────────┐              │
      ├───────────┤ LEAD     │  position ahead, invite, walk to safe zone
      │           └────┬─────┘              │
      │                │ 20 s no effect     │
      │                ▼                    │
      │           ┌──────────┐              │
      └───────────┤ ESCALATE ├──────────────┘
                  └────┬─────┘  notify ladder, stay, keep talking
                       │ no ack / person down
                       ▼
                  ┌──────────┐
                  │ EMERGENCY│  voice call, secondary contact
                  └──────────┘

CALM_MODE is a modifier available in ATTEND, LEAD, and ESCALATE.
Any state yields immediately on the <1.2 m proximity rule.
```

Five states. Implementable in an afternoon, explains itself on a slide, and gives E4 something
concrete to own from hour 0. **This is the Tier 0/1 machine and it does not change.**

**Tier 2 extension — what happens after ESCALATE, and the day-walk entry point.** The five
states above were silent on a person who actually leaves, and on a voluntary walk. Both are the
same three added states, entered two different ways (full spec and rationale in
`14-companion-and-caretaker.md` §6–7):

```
  Two entry points, one shared tail:

  from ESCALATE, dont_go breach ──────┐
  (page severity)                     │
                                       ▼
                                 ┌──────────┐
  voluntary walk request ──►WALK│  FOLLOW  │  track at distance, stream live location to
  (ping severity)          radius │          │  caregiver, never close the standoff distance
                           broken └────┬─────┘  to force compliance
                                       │ "take me home" / agrees to turn back
                                       ▼
                              ┌────────────────┐
                              │  CONFIRM_HOME  │  "Would you still like to go home?"
                              └────────┬───────┘
                                       │ yes
                                       ▼
                              ┌────────────────┐
                              │   GUIDE_HOME   │  retraces the breadcrumb trail recorded
                              └────────┬───────┘  from `pose` since the walk started, no GPS
                                       │ arrived     (see companion-and-caretaker doc)
                                       ▼
                                     IDLE
```

`WALK` is the only state that isn't a safety escalation — it's how a voluntary walk starts, and
it feeds into the exact same `FOLLOW` state a `dont_go` breach does, just at a lower alert
severity. `CONFIRM_HOME` is the yield rule applied to navigation instead of proximity: never act
on stale intent, check again in the moment. Build this after the Tier 0/1 spine is green, not
before — same discipline as every other Tier 2 item in §6.

## 5. Escalation ladder

| Step | Trigger | Action |
|---|---|---|
| 0 | Agitation rises | Robot attends and converses. Nothing leaves the house. |
| 1 | Heading toward exit zone | Lead-away begins. Event logged, dashboard updates live. |
| 2 | 20 s, no redirection | SMS + push to primary caregiver with event, position, timeline link. |
| 3 | 60 s, unacknowledged | Twilio **voice call** to primary. Texts don't wake people at 2 AM. |
| 4 | 120 s, unacknowledged, or exit-zone breach, or person down and unresponsive | Secondary contact called. Dashboard goes to full-screen alert. |
| 5 | Person actually exits the `dont_go` boundary | **Immediate** — does not wait for step 2's 20 s. Alert severity jumps straight to voice-call urgency; dashboard map goes to continuous live tracking (Tier 2, `14-companion-and-caretaker.md` §6). |
| — | Separated during a voluntary day walk (`WALK` → `FOLLOW`) | Lower severity — a location ping to the caregiver, not a page. Same underlying stream as step 5, different framing (§7). |

Every step is cancellable from the dashboard with one control. False alarms that can't be
silenced are why families unplug devices like this.

## 6. Scope, with the cut lines drawn in advance

Re-tiered for a **24-hour** window (`10-second-pass.md` P0-9). The important change: Tier 0 is
split so that the part requiring no robot comes first and stands alone. If the hardware never
cooperates, Tier 0a is still a complete, demoable product.

**Tier 0a — the spine, no robot required. Target: 6 PM Saturday.**

- [ ] A real person tracked in the taped area with drawn zones (`11-perception.md` Tracker A)
- [ ] Heading-toward-exit detection fires reliably
- [ ] Deepgram STT → dialogue policy → ElevenLabs TTS, barge-in, under 2 s system latency
- [ ] Impersonation guard rejecting identity claims on both sides of the model
- [ ] Escalation reaches a real phone
- [ ] Every event appears in the portal timeline live

**Tier 0b — the robot. Target: 11 PM Saturday, and it is a cut decision, not a requirement.**

- [ ] Lead-away behavior executing within the safety envelope on hardware
- [ ] Yield reflex on raw LiDAR range, independent of the tracker
- [ ] Tier 0 lines rendered in the consented voice and playing from the robot

**Tier 1 — build once Tier 0 is green (target: after the 11 PM cut).**

- [ ] Pacing detection from trajectory
- [ ] Repeated-question detection from transcripts
- [ ] Calm Mode
- [ ] Onboarding wizard with consented voice enrollment
- [ ] Morning report
- [ ] Check-in relay: a portal message reaches the robot's `say` pipeline, attributed
- [ ] Companionship Q&A about family/self/setting, from the onboarding profile
- [ ] Onboarding step 4 (schedule/habits) feeding a reminder timer, suppressed outside `IDLE`
- [ ] Zone caregiver-facing label reads "Don't go" (wire value stays `exit`) plus home anchor point
- [ ] Breach severity jump (ladder step 5) and continuous live-location streaming on the map

**Tier 2 — stretch. Dropping these costs us nothing.**

- [ ] Guided walk: `FOLLOW` → `CONFIRM_HOME` → `GUIDE_HOME`, retracing a breadcrumb trail built
      from `pose` — no GPS, no dedicated mock needed, and demoable live at the venue
      (`14-companion-and-caretaker.md`)
- [ ] Day-walk entry into the same follow/guide-home machinery, ping-severity alerts
- [ ] Preferred walking route (on top of a working point-to-point "take me home")
- [ ] Token-compression counter
- [ ] Pulse oximeter as an optional calm-state check
- [ ] Multi-room mapping

**Cut, deliberately, and we can explain why:**

- Physical intercept and path blocking — safety and ethics, `01-judge-review.md` P0-1
- 40 Hz vibroacoustic DSP — unsupported claim, and the physics doesn't work, P0-2
- Pulse ox as a trigger — wrong sensor for the job, P1-1
- Ramp track — no real integration available, P1-3
- Beacon-based follow (the Go2's built-in ISS mode) — it tracks a worn tag, which contradicts
  our own argument against wearables, `11-perception.md`
- Onboard camera–LiDAR fusion — the right long-term tracker, not a 24-hour one, `11-perception.md`
- Two of the four evaluation metrics — 24 hours buys two done properly, `10-second-pass.md` P1-9

Being able to say "we cut this *on purpose*, here's the reasoning" is itself a strong signal to
a judge. It reads as engineering judgment. Saying "we ran out of time" reads as the opposite.

## 7. The six things we say at the table

1. Dementia wandering is the reason families give up and move someone into a facility. Door
   alarms fire too late and tell you nothing.
2. A robot that's already in the room can notice the pacing before the door.
3. It leads — it never blocks. Here's the safety envelope, written down, with numbers.
4. It speaks in a consented family voice and never pretends to be that person.
5. Twenty seconds later the caregiver's phone rings, with context. In the morning they get a
   report. That's the product.
6. It's the same robot at 3 PM asking about her garden as it is at 2 AM walking her back to
   bed — one relationship, not a safety gadget and a novelty toy bolted together.

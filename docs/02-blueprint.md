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
                         ┌──► 1. Familiar-Voice Conversation  (Deepgram + ElevenLabs)
[Unitree Go2 + Jetson] ──┼──► 2. Night Watch & Lead-Away      (DimOS + LiDAR SLAM)
                         └──► 3. Caregiver Link               (React + FastAPI + Twilio)

                              Calm Mode is a behavior inside pillars 1+2, not a pillar.
```

### Pillar 1 — Familiar-voice conversation

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

### Pillar 2 — Night Watch and lead-away

Three capabilities, in order of importance:

**a. Zones.** A map of the home with caregiver-drawn zones: `safe`, `watch`, `exit`. For the
demo this is a small pre-authored map, not live SLAM in the venue (see `05-demo.md`).

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

**d. How the robot spends the night.** A Go2 runs 1–2 hours on the standard battery, 2–4 on the
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

**Onboarding, three steps, designed to be completed by a stressed 55-year-old at 11 PM:**

1. *Who are we caring for?* Name, what to call them, the things that reliably calm them
   (a song, a place, a person), and what not to bring up.
2. *Whose voice?* The family member records 30 seconds themselves, behind an explicit consent
   checkbox naming the use. Off by default until recorded.
3. *Where are the risks?* Draw zones on the floorplan. Set the escalation ladder: who gets
   called, in what order, after how long.

**Night Watch dashboard:** live map with person and robot position, current state, event
timeline, and the escalation ladder with a big visible "acknowledged" control so a caregiver
can say "I've got it" from bed and stop the phone tree.

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
concrete to own from hour 0.

## 5. Escalation ladder

| Step | Trigger | Action |
|---|---|---|
| 0 | Agitation rises | Robot attends and converses. Nothing leaves the house. |
| 1 | Heading toward exit zone | Lead-away begins. Event logged, dashboard updates live. |
| 2 | 20 s, no redirection | SMS + push to primary caregiver with event, position, timeline link. |
| 3 | 60 s, unacknowledged | Twilio **voice call** to primary. Texts don't wake people at 2 AM. |
| 4 | 120 s, unacknowledged, or exit-zone breach, or person down and unresponsive | Secondary contact called. Dashboard goes to full-screen alert. |

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

**Tier 2 — stretch. Dropping these costs us nothing.**

- [ ] Guided walk
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

## 7. The five things we say at the table

1. Dementia wandering is the reason families give up and move someone into a facility. Door
   alarms fire too late and tell you nothing.
2. A robot that's already in the room can notice the pacing before the door.
3. It leads — it never blocks. Here's the safety envelope, written down, with numbers.
4. It speaks in a consented family voice and never pretends to be that person.
5. Twenty seconds later the caregiver's phone rings, with context. In the morning they get a
   report. That's the product.

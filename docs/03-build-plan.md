# 36-hour build plan

Assumes a standard HackMIT-length hacking window. Shift the hour numbers to match the real
clock; the checkpoint structure is what matters.

## Ownership — revised

The change from the original: **Engineer 4 stops being the miscellaneous-hardware person and
becomes the orchestrator.** They own the seam between the other three, which is where the
project actually fails. Everything they were assigned before is either cut or downgraded to a
late-game task.

### E1 — Voice and dialogue

| | |
|---|---|
| Owns | Deepgram streaming STT, ElevenLabs TTS, the dementia dialogue policy, prosody features |
| Ships | A `voice_service` that consumes mic audio, emits `transcript` and `prosody` events, and renders `say` commands |
| Hard requirement | Barge-in. Robot stops speaking the instant the person speaks. Non-negotiable for this user. |
| Watch out for | Endpointing tuned too aggressively — long pauses are normal here and cutting people off is the exact failure we claim to fix. Tune it long, early, and test with real mumbling. |
| Owns the metric | WER on the degraded-speech set; p50/p95 end-to-end voice latency |

### E2 — Robot behavior

| | |
|---|---|
| Owns | DimOS/Unitree integration, mapping, zones, person tracking, lead-away controller, pacing detector |
| Ships | A `robot_service` that emits `pose` and `person_track` and consumes `goto` / `lead_to` / `posture` commands |
| Hard requirement | The safety envelope in `06-safety-ethics.md` is enforced in the controller, not in the demo script. Hard-coded limits. |
| Watch out for | Burning hour 0–12 on live SLAM. Author a small map once, save it, load it. Live mapping in a venue is a hazard, not a feature. |
| Sim-first mandate | Build against the fake robot until the behavior is right. Hardware is for validating a controller that already works, not for developing one. |
| Owns the metric | Pacing detection precision/recall over 20 trials |

### E3 — Portal and cloud

| | |
|---|---|
| Owns | FastAPI, WebSocket fan-out, event store, React portal, Twilio ladder |
| Ships | Onboarding wizard, live Night Watch dashboard, event timeline, morning report, escalation ladder with acknowledge |
| Hard requirement | The dashboard renders from the event stream alone. If it needs a special demo mode to look right, it's wrong. |
| Watch out for | Over-designing the floorplan canvas. Drawing rectangles on a background image is enough. Nobody is judging your canvas library. |
| Owns the metric | Event-to-phone-buzz wall clock |

### E4 — Orchestrator and integration

| | |
|---|---|
| Owns | The state machine, the event bus, **the mocks**, the demo runner, metrics collection |
| Ships | `orchestrator` implementing the five states; `mock_robot`, `mock_patient`, `mock_mic`; a one-key demo reset |
| Hard requirement | Mocks working by hour 6, so the other three can each run the full pipeline alone |
| Late-game | Token compression counter, if green at hour 26 |
| Owns | The integration schedule, and the authority to call the Tier-1 cut at hour 20 |

## Timeline

### Hours 0–4 — Decide, don't build

- [ ] **All:** read `01-judge-review.md` together. Agree on the cuts. Argue now, not at hour 25.
- [ ] **All:** freeze `04-interfaces.md`. This is the most valuable hour of the hackathon.
- [ ] **Name locked.** Lantern unless someone has a better one in the next ten minutes.
- [ ] **Someone:** start reaching out for a caregiver or clinician conversation *now* — a memory
      care nurse, an OT, a family caregiver forum. It takes hours to get a reply and one quote
      is worth more than a feature. Start it at hour 2 so it can still change what we build.
- [ ] **E2:** confirm the robot works at all. Battery count, charger, SDK access, DimOS running,
      teleop working. If the hardware is shared or loaned, find out the availability schedule
      before you plan around it.
- [ ] **E1:** Deepgram and ElevenLabs keys live, "hello world" round trip in a terminal.
- [ ] **E3:** repo scaffolded, FastAPI + React running, WebSocket echoing.
- [ ] **E4:** state machine diagram on paper, event bus skeleton.

**Gate at hour 4:** interfaces frozen and in the repo. Anyone blocked on hardware access
escalates *now*, while there's time to replan.

### Hours 4–12 — Parallel against mocks

- [ ] **E4 (priority over everything else they do):** mocks live by hour 6. `mock_robot` accepts
      commands and emits plausible poses. `mock_patient` walks a scripted path toward an exit
      zone. `mock_mic` replays recorded audio. Announce in chat the moment it works.
- [ ] **E1:** STT streaming with long endpointing; TTS playing; barge-in working; dialogue policy
      in the system prompt.
- [ ] **E2:** map authored and loading; zones loading; person tracking against the mock; robot
      moving to commanded poses on real hardware.
- [ ] **E3:** event stream rendering on the dashboard; zone drawing; Twilio sending one real SMS
      to a real phone (do this early — carrier and trial-account surprises are common).
- [ ] **E4:** five states implemented, transitions driven by mock events.

**Gate at hour 12:** the full spine runs end to end **with the fake robot**. Mock patient walks
toward the exit, orchestrator transitions to LEAD, voice speaks, escalation fires, dashboard
updates. Nothing is real except the software, and that is fine — this is the milestone that
predicts whether you finish.

If hour 12 arrives and the mock spine doesn't run, stop adding features and fix it. Everything
after this point depends on it.

### Hours 12–20 — Real hardware

- [ ] **E2 + E4:** swap mock robot for real robot. Expect this to be uglier than planned; it
      always is. Budget the whole block for it.
- [ ] **E2:** lead-away controller on hardware, safety envelope enforced, tested with a human
      playing the patient.
- [ ] **E1 + E4:** voice running on the robot's actual audio path, not a laptop.
- [ ] **E3:** onboarding wizard, escalation ladder with acknowledge.
- [ ] **All:** first informal run-through at hour 19. Rough is fine. Find the surprises.

**Gate at hour 20 — the cut decision.** E4 calls it. Spine green on real hardware? Build Tier 1.
Not green? Everything stops except the spine, and the demo uses the mock robot with the real
one doing a simpler beat. A mock-robot demo that runs flawlessly beats a real-robot demo that
fails, every time, and it is *not* embarrassing — you say "the navigation stack is running
against our simulator right now because the expo floor isn't a home; here's the hardware video."

### Hours 20–28 — Tier 1 and evidence

- [ ] **E2:** pacing detection from trajectory
- [ ] **E1:** repeated-question detection; prosody into agitation state
- [ ] **E1 + E2:** Calm Mode
- [ ] **E3:** morning report — cheap, and it lands
- [ ] **All:** the four metrics in `07-evaluation.md`. Do not skip this. It is the highest
      value-per-hour work available in this block and almost no other team will have done it.
- [ ] **E4:** demo runner, one-key reset, fallback modes wired

**Gate at hour 28: feature freeze.** Anything not working now is cut. No exceptions, no "it's
almost done." "Almost done" at hour 28 is how teams end up with a broken demo at hour 34.

### Hours 28–32 — Rehearse and record

- [ ] **Hour 29:** full table demo, timed, all four present. Then again.
- [ ] **Hour 30: record the backup video.** Hard deadline. Screen recording of the dashboard plus
      phone video of the robot, 90 seconds, narrated. If the robot dies at hour 33 — batteries
      fail, SDK wedges, someone trips over it — the video is the entire difference between
      demoing and not demoing. Record it while everything works, not while panicking.
- [ ] **Hour 31:** slides. Six of them, listed below.
- [ ] Reset procedure tested cold by someone who didn't write it.

### Hours 32–36 — Polish, submit, sleep

- [ ] Devpost submission written **early**. Submission deadlines are real and unforgiving.
- [ ] Table setup: taped floor footprint, laptop angle, mic placement, charged batteries, spare
      battery, phone on the table for the SMS to land on visibly.
- [ ] Five more rehearsals. Everyone can deliver the 90 seconds solo — judges split up, and
      whoever is standing there when a judge arrives has to be able to do the whole thing.
- [ ] One person sleeps 3 hours while the others finish, then swaps. A team that's been awake
      34 hours pitches badly, and the pitch is a large fraction of the score.

## The six slides

1. **The 2 AM story.** One person, one night, one specific scene. No bullet points.
2. **Why alarms and trackers don't solve it.** The table from `02-blueprint.md` §2.
3. **What Lantern does.** The state machine diagram. Ten seconds.
4. **Lead, don't block.** The safety envelope table with real numbers. This is the slide that
   separates you from the other robot teams.
5. **Familiar voice, not impersonation.** The consent flow.
6. **What we measured.** The four numbers, including the false positives.

Note what isn't there: no team slide, no market-size slide, no roadmap. At a table you get
90 seconds of attention. Spend it on the demo and these six.

## Standing rules

- **Commit and push every two hours.** Hardware hackathons eat laptops.
- **Nobody works on something not in Tier 0 while Tier 0 is red.**
- **The safety envelope is not adjustable for demo purposes.** If the demo needs the robot
  closer than 1.5 m, the demo changes, not the limit. It's also the thing a judge is most
  likely to test by stepping toward the robot themselves.
- **When you're stuck for 30 minutes, say so out loud.** Silent blocking is what turns a
  two-hour problem into a ten-hour one.
- **E4 has the authority to cut.** Agree to this at hour 0 so it isn't a negotiation at hour 20.

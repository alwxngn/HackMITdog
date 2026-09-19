# 24-hour build plan

**This document was rewritten after we confirmed the window.** HackMIT is a **24-hour**
hackathon, not 36. The previous version of this plan assumed 36 hours and every gate in it was
wrong. See `10-second-pass.md` P0-9.

Wall-clock times below assume HackMIT 2025's schedule — **hacking 11:45 AM Saturday to 11:45 AM
Sunday**, closing ceremony Sunday evening. **Confirm this year's exact times on
`dayof.hackmit.org` and shift everything by the difference before you rely on a single number
here.** The gate structure matters more than the specific clock times, but the gate structure
is built for 24 hours and does not survive being stretched back to 36.

## The decision that shapes everything else

At 36 hours, "build against mocks, swap in real hardware" is comfortable. At 24 hours, with the
hardware block landing overnight, it is a coin flip — and you cannot re-roll it at 6 AM.

**So invert the risk: the demo that must work is the one that does not require the robot.**

Person tracking runs off a fixed camera over the taped area (`11-perception.md`, Tracker A).
The orchestrator, dialogue, dashboard, escalation, and the morning report all run against a
real human walking around, with no robot in the loop. Get that green by early evening and you
have a complete, demoable product before dinner.

Then the robot is upside. If it works, it is the best part of the demo. If it dies at 3 AM,
you still have a product, and `05-demo.md` fallback level B is a plan rather than a collapse.

This is not lowering ambition. It is refusing to make the whole project contingent on the one
subsystem you cannot debug by reading a log.

## Ownership

Unchanged in spirit from the original: **E4 is the orchestrator, not the miscellaneous-hardware
person.** They own the seam between the other three, which is where projects fail. Two things
moved: person tracking is now explicitly E2's, and the impersonation guard is explicitly E4's.

### E1 — Voice and dialogue

| | |
|---|---|
| Owns | Deepgram streaming STT, ElevenLabs TTS, the dialogue policy, the tiered runtime in `12-dialogue-runtime.md`, prosody features, companionship conversation and check-in relay (`14-companion-and-caretaker.md` §1–2, Tier 1) |
| Ships | A `voice_service` consuming mic audio, emitting `transcript` and `prosody`, rendering `say` commands |
| Hard requirement | Barge-in. Robot stops speaking the instant the person speaks. Non-negotiable for this user. |
| Hard requirement | The fifteen Tier 0 lines rendered to disk. **The demo beats must not need the network.** |
| Watch out for | Endpointing tuned too aggressively — long pauses are normal here. Tune it long, early, and read `12-dialogue-runtime.md` on why that makes your latency metric look worse and what to report instead. |
| Watch out for (Tier 1) | Companionship mode is the same six policy rules on lower-stakes material, not a second prompt to maintain. Don't fork the system prompt. |
| Owns the metric | WER on degraded speech (**priority**); voice latency if it falls out for free |

### E2 — Perception and robot behavior

| | |
|---|---|
| Owns | Person tracking (`11-perception.md`), zones, the lead-away controller, the pacing detector, Unitree/DimOS integration, and — Tier 2 only — the `FOLLOW`/`GUIDE_HOME` behaviors and `mock_gps` (`14-companion-and-caretaker.md` §6–7) |
| Ships | A `tracker` emitting `person_track`, and a `robot_service` emitting `pose` and consuming `goto` / `lead_to` / `posture` |
| **First deliverable** | **Tracker A, emitting real `person_track` from a real walking human, before you touch the robot.** Everything else depends on it. |
| Hard requirement | The safety envelope in `06-safety-ethics.md` lives in the controller, not the demo script. The yield reflex uses raw LiDAR range, **not** the tracker. |
| Watch out for | Live SLAM. Author the map once — it is a taped rectangle — save it, load it. |
| Watch out for (Tier 2) | Real GPS does not work indoors. Don't lose an hour discovering this at the venue — `FOLLOW`/`GUIDE_HOME` are demoed against `mock_gps` by design, same as `mock_robot`. |
| Owns the metric | Pacing detection precision/recall (**priority**) |

### E3 — Portal and cloud

| | |
|---|---|
| Owns | FastAPI, WebSocket fan-out, event store, React portal, Twilio ladder, onboarding steps 3–4 (zone field-mapping + home anchor + schedule/habits) and the check-in composer (`14-companion-and-caretaker.md` §1, §5, §8) |
| Ships | Live Night Watch dashboard, event timeline, morning report, escalation ladder with acknowledge, onboarding if time |
| Hard requirement | The dashboard renders from the event stream alone. If it needs a demo mode to look right, it's wrong. |
| Watch out for | Over-designing the floorplan canvas. Rectangles on a background image. Nobody is judging your canvas library. |
| Watch out for (Tier 2) | The live-tracking map view during `FOLLOW` is one more rendering mode of the map you already built, not a new component. Reuse it. |
| Owns the metric | Event-to-phone wall clock, if it falls out for free |

### E4 — Orchestrator and integration

| | |
|---|---|
| Owns | The state machine, the event bus, **the mocks**, the impersonation guard, the demo runner, metrics collection, the reminder-suppression rule (`agent_state != IDLE` mutes nudges), and — Tier 2 — `CONFIRM_HOME` plus `mock_gps` |
| Ships | `orchestrator` implementing the five states; `mock_robot`, `mock_patient`, `mock_mic`; a one-key reset |
| Hard requirement | Mocks working by **2:30 PM**, so the other three can run the full pipeline alone |
| Hard requirement | Inbound and outbound impersonation guards (`12-dialogue-runtime.md`) — code, not prompt |
| Owns (Tier 1) | The check-in message queue: never interrupts `LEAD`/`ESCALATE`/`EMERGENCY`, delivered only in a conversational state |
| Owns | The integration schedule, and the authority to call the cut at 11 PM |

---

## Timeline

### 11:45 AM – 1:15 PM · Decide and confirm (H0–H1.5)

Ninety minutes, not four hours. Decide fast, then build.

- [ ] **All, 20 minutes, together:** agree the cuts in `01-judge-review.md` and `10-second-pass.md`.
      Argue now, not at 2 AM. Name locked: Lantern.
- [ ] **All:** freeze `04-interfaces.md`, with the `tracker` field added from `11-perception.md`.
      Still the most valuable half hour of the event.
- [ ] **E2 first, before anything else:** confirm the robot's SKU and that it powers on, walks
      under teleop, and exposes the SDK. Count batteries and find the charger. **If the robot
      is shared or loaned, find out the availability schedule now.** If it's dead or
      unavailable, you need to know at noon, not midnight.
- [ ] **E1:** Deepgram and ElevenLabs keys live, hello-world round trip in a terminal.
- [ ] **E3:** repo scaffolded, FastAPI + React running, WebSocket echoing, `CREDITS.md` started.
- [ ] **E4:** five states on paper, event bus skeleton, JSONL logging from the first message.
- [ ] **Someone, by noon:** start the caregiver or clinician outreach. A memory-care nurse, an
      OT, a family-caregiver forum. It takes hours to get a reply and one quote beats a
      feature. Send it now, while the answer can still change the build.
- [ ] **Someone:** phone hotspot tested. Not at 10 AM tomorrow.

**Gate, 1:15 PM:** interfaces frozen and pushed. Robot status known. Anyone blocked escalates
now, while there's still time to replan.

### 1:15 PM – 6:00 PM · Parallel against mocks (H1.5–H6.25)

The highest-leverage block of the event. Two things must land inside it.

- [ ] **E4, 2:30 PM, priority over everything else:** mocks live. `mock_robot` accepts commands
      and emits plausible poses; `mock_patient` walks a scripted path into an exit zone;
      `mock_mic` replays audio. Announce it in chat the second it works.
- [ ] **E2, 4:00 PM:** tape the area, calibrate the homography, **emit real `person_track` from a
      real human.** `11-perception.md` steps 1–4. This unblocks the pacing detector, the
      lead-away geometry, the dashboard, and Metric 3.
- [ ] **E1:** STT streaming with long endpointing; TTS playing; barge-in working; the six policy
      rules in the system prompt; Tier 0 lines identified.
- [ ] **E3:** event stream rendering live; zone drawing; **one real Twilio SMS to a real phone**
      (do this early — trial-account and carrier surprises are common and always slower than
      you expect).
- [ ] **E4:** five states implemented, transitions driven by mock events; impersonation guard in.

**Gate, 6:00 PM — the one that predicts whether you finish:** the full spine runs end to end
with the **mock robot and a real person walking the taped area.** Someone paces, agitation
rises, the orchestrator enters LEAD, the voice speaks, escalation fires, the phone buzzes, the
dashboard shows all of it.

If that isn't running at 6 PM, **stop adding features and fix it.** Nothing downstream matters.

### 6:00 PM – 11:00 PM · Real hardware (H6.25–H11.25)

Five hours for the riskiest work, while everyone is still awake enough to do it. Eat during
this block, at your desks, in shifts.

- [ ] **E2 + E4:** swap `mock_robot` for the real one. This is always uglier than planned.
      Budget the whole block.
- [ ] **E2:** lead-away controller on hardware; safety envelope enforced in the controller; yield
      reflex on raw LiDAR range; tested with a human playing the patient.
- [ ] **E2, if the above is green:** the LiDAR cluster tracker (`11-perception.md` Tracker C), so
      the robot can track the person through 360° while leading away from them.
- [ ] **E1 + E4:** voice on the robot's actual audio path, not a laptop. Tier 0 lines rendered to
      disk in the consented voice.
- [ ] **E3:** escalation ladder with acknowledge; morning report.
- [ ] **All, 10:15 PM:** first informal run-through. Rough is fine. Find the surprises now.

**Gate, 11:00 PM — the cut. E4 calls it, and the team agreed at noon that E4 has this authority.**

- **Spine green on hardware?** Build Tier 1 overnight.
- **Not green?** The robot is out of the critical path. The demo is the camera tracker plus the
  mock robot, and the real robot does one simple scripted beat if it can. Say it plainly at the
  table: *"navigation is running against our simulator right now because a convention hall
  isn't a home — here's the hardware video."* A demo that runs flawlessly beats one that might
  work, every time, and judges see dead hardware all day.

### 11:00 PM – 3:00 AM · Tier 1 and evidence (H11.25–H15.25)

Sleep rotation starts here. **Two people sleep 2:00–5:00 AM, the other two 5:00–8:00 AM.** This
is not optional: hacking ends at 11:45 AM and you are pitching all Sunday afternoon. A team
that has been awake for 30 hours pitches badly, and the pitch is a large fraction of the score.

- [ ] **E2:** pacing detection from trajectory, then **Metric 3 — twenty trials, ten positive,
      ten negative.** Run it before the taped area gets disturbed. This is the number behind
      your only novel claim.
- [ ] **E1:** repeated-question detection; prosody into the agitation state; then **Metric 1 —
      forty degraded-speech utterances and WER against a baseline.** Needs no robot and no
      floor space; it is the perfect task for whoever is blocked.
- [ ] **E1 + E2:** Calm Mode.
- [ ] **E1:** companionship conversation fields (family/self/setting) added to the prompt, plus
      check-in relay through the existing `say`/`attribution` path. Both are additive, not new
      architecture — see `14-companion-and-caretaker.md` §1–2. Don't schedule more than an hour.
- [ ] **E3:** morning report if it isn't done. It's cheap and it lands. Then onboarding step 4
      (schedule/habits) and the zone label rename to "Don't go" if there's slack.
- [ ] **E2/E4, only if the spine and Tier 1 are both green and it's still before 3 AM:** start
      `FOLLOW`/`CONFIRM_HOME`/`GUIDE_HOME` against `mock_gps`. This is genuinely new work, not a
      polish task — do not start it at the expense of Metric 3 or the feature-freeze gate below.
- [ ] **E4:** demo runner, one-key reset, fallback modes wired and *each one rehearsed once*.
- [ ] Metrics 2 and 4 only if they fall out of the logs for free. Do not schedule them.

**Gate, 5:00 AM — feature freeze.** Anything not working is cut. No exceptions, no "almost
done." "Almost done" at 5 AM is how teams get a broken demo at 11.

### 5:00 AM – 8:00 AM · Rehearse, record, write

- [ ] **6:00 AM — record the backup video. Hard deadline, non-negotiable.** Ninety seconds:
      screen recording of the dashboard through a full event, plus phone video of the robot
      doing the lead-away somewhere quiet. Narrated. **Record it while everything still works.**
      You cannot record a working demo after it stops working, and that is exactly when you
      need it.
- [ ] Full table demo, timed, twice.
- [ ] Six slides (listed below). One hour, no more.
- [ ] **Devpost submission drafted.** Not at 11:30. Lead with the 2 AM scene; include the safety
      envelope table and the numbers.
- [ ] Reset procedure tested cold by someone who didn't write it.

### 8:00 AM – 11:45 AM · Rehearse, submit, set up

- [ ] **Submit by 10:30 AM at the latest.** Submission deadlines are real and unforgiving, and
      the site gets slow in the last twenty minutes.
- [ ] Table setup: taped footprint, camera on its tripod and *re-calibrated in the actual demo
      spot*, laptop angle, lav mic, charged batteries, spare battery, phone face-up where the
      judge can see the SMS land.
- [ ] Five more rehearsals. **Everyone can deliver the 90 seconds solo** — judges split up, and
      whoever is standing there has to do the whole thing.
- [ ] Both fallback levels rehearsed once each, today, not theoretically.
- [ ] Batteries on the charger. Plural.

## The six slides

1. **The 2 AM story.** One person, one night, one specific scene. No bullet points.
2. **Why alarms and trackers don't solve it.** `02-blueprint.md` §2 plus the named products from
   `13-landscape.md`.
3. **What Lantern does.** The state machine. Ten seconds.
4. **Lead, don't block.** The safety envelope table with real numbers. This is the slide that
   separates you from the other robot teams.
5. **Familiar voice, not impersonation.** The consent flow, and the guard being code rather than
   a prompt.
6. **What we measured.** The two real numbers, including the false positives.

No team slide, no market-size slide, no roadmap. At a table you get 90 seconds.

## Standing rules

- **Commit and push every hour, at minimum — an AI coding agent can produce an hour of
  hand-written-equivalent work in a couple of minutes, so treat that as a ceiling, not a
  cadence.** Commit after every agent turn that changes behavior. `15-dev-workflow.md` has the
  full git and multi-agent workflow, including which files are safe for an agent to touch
  unsupervised and which aren't.
- **Cite open-source as you use it.** `CREDITS.md`, updated when you add the dependency, not
  reconstructed at 11 AM. HackMIT requires it (`10-second-pass.md` P1-8).
- **Nobody works on something outside the spine while the spine is red.**
- **The safety envelope is not adjustable for demo purposes.** If the demo wants the robot
  closer than 1.5 m, the demo changes. A judge is likely to test it by stepping toward the
  robot themselves.
- **When you're stuck for 20 minutes, say so out loud.** Silent blocking turns a one-hour
  problem into a six-hour one, and at 24 hours you do not have a six-hour problem to spare.
- **E4 has the authority to cut.** Agreed at noon so it isn't a negotiation at 11 PM.

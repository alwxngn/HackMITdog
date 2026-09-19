# Second-pass review — what the first revision missed

`01-judge-review.md` fixed the things that would have gotten you dismissed on the healthcare
track: the restraint problem, the false clinical claim, the consent story, the scope. Those
fixes hold. This document is a second pass over the *revised* plan, and it finds six more
things — two of which are more urgent than anything in the first review, because they are
wrong about the physical world rather than wrong about the pitch.

Ordered by urgency, not by size.

---

## P0-9: The clock is wrong. HackMIT is 24 hours, and it starts today.

Every schedule in `03-build-plan.md` assumed a 36-hour window. HackMIT is a **24-hour**
hackathon, and HackMIT 2026 runs **September 19–20** — meaning the hacking window is already
open as you read this.

For reference, HackMIT 2025 started hacking at **11:45 AM Saturday and ended 11:45 AM Sunday**,
with the closing ceremony that evening. Confirm this year's exact times on `dayof.hackmit.org`
before you plan around them, but plan for 24 hours, not 36.

This is not a proportional trim. You lost **twelve hours, a third of the plan**, and you lost
them from the part of the schedule that was already the tightest: hardware integration and the
evaluation block. Concretely, under the old plan:

- The "decide, don't build" block was 4 hours. At 24 hours that is 17% of the event spent not
  building. It has to compress to about 90 minutes.
- "Hours 12–20 — real hardware" was an 8-hour block for the single riskiest activity. It is now
  roughly 6 hours **and it lands in the middle of the night**, when everyone is worst at
  debugging.
- The hour-30 backup video deadline was 6 hours before the end. The equivalent now is around
  **6 AM Sunday**, which is exactly when a team that has been up all night wants to sleep. It is
  still non-negotiable.
- The four-metric evaluation block was 8 hours. You have roughly 4, which means **triage the
  metrics down to two** (see P1-9).

`03-build-plan.md` has been rewritten against a real wall clock. Read it before you write
anything else.

**The deeper consequence:** at 36 hours, "build against mocks, then swap in real hardware" is a
comfortable plan. At 24 hours with an overnight hardware block, it is a coin flip. The
recommendation in P0-10 follows directly from this.

---

## P0-10: Nothing in the plan says how you track the person, and six things depend on it

This is the real hole. Read `04-interfaces.md` again and notice that `person_track` — with
position, velocity, heading, posture, and confidence at 10 Hz — simply *appears*, sourced from
`robot`. The document specifies the message beautifully and never says how it gets produced.

Everything load-bearing hangs off that one message:

| Depends on `person_track` | What happens without it |
|---|---|
| Pacing detection (Tier 1, your novel claim) | No trajectory, no direction reversals, no detector |
| `projected_zone` / `ttz_s` | The orchestrator's primary trigger never fires |
| Lead-away positioning | Cannot compute "ahead and to the side of their heading" |
| The 1.5 m standoff and ±45° approach sector | Cannot enforce a geometric envelope against an unknown position |
| The yield rule | Cannot detect the person closing to 1.2 m |
| Metric 3 (pacing precision/recall) | Nothing to measure |

Six subsystems, one unspecified dependency, and it is the dependency with the most physics in
it. If person tracking is flaky, the demo is flaky in a way no amount of orchestrator polish
fixes.

It is also the thing most likely to eat an unbudgeted six hours, because the obvious answers
are all worse than they look:

- **The Go2's built-in side-follow (ISS 2.0) tracks a wireless positioning module, not a
  person.** It follows a *tag*. If you use it, Arthur is wearing a beacon — and your own
  comparison table in `02-blueprint.md` §2 dismisses wearables because they get "removed or
  forgotten, which is precisely the symptom." A judge who knows the Go2 will ask, and "the
  person wears a tracker" collapses the differentiation you built the pitch on. ISS is also not
  available on the Air SKU.
- **The onboard camera is 120° FOV at 15 fps with no depth** on non-EDU units. Workable for
  detection, weak for the velocity and heading estimates the pacing detector needs.
- **LiDAR gives you geometry but not identity.** A horizontal slice plus clustering gets you
  "there is a leg-sized thing over there," which you then have to associate across frames.

**Fix:** `11-perception.md` specifies three tracker implementations behind the same
`person_track` schema, ranked by risk, with an explicit recommendation to build the boring one
first. The important structural point is that because the tracker is behind a schema, it is
swappable — so build the reliable one, get the spine green, and upgrade only if there's time.

---

## P0-11: The dialogue layer has no runtime, and the venue network will not cooperate

`02-blueprint.md` specifies the dialogue *policy* in real detail — the six rules, the validation
therapy framing — and it is the best writing in the repo. But there is no specification of what
actually generates the speech. There is no LLM in the architecture diagram. `07-evaluation.md`
measures "LLM first token" in Metric 2, which is the only acknowledgement anywhere that a model
is in the loop.

That gap contains three separate risks:

1. **Latency.** Your target is under 2 seconds mic-close to first audio. That budget covers
   streaming STT finalization, an LLM round trip, and TTS time-to-first-byte. It is achievable,
   but only if you have designed for it, and nobody has assigned it a budget.
2. **The venue network.** A thousand hackers on shared wifi. Your pipeline currently makes
   three cloud round trips per utterance. During judging, in the busiest hour of the event, at
   the moment a judge is standing at your table.
3. **The policy is only a prompt.** Every dialogue rule — including "never impersonate," which
   is the ethical centerpiece of the whole pitch — currently lives in a system prompt. Prompts
   are not guarantees. The one question a judge will actually try is asking the robot directly
   *"are you Sarah?"*, and a prompt-only guard can fail that live.

**Fix:** `12-dialogue-runtime.md` specifies a three-tier response system — reflex lines that
never touch the network, a small cache of pre-rendered TTS for the demo's known beats, and the
LLM for everything else — plus a latency budget per stage and a pre-LLM impersonation guard
that is code rather than instruction. The reflex tier also means a network outage degrades your
demo instead of ending it.

---

## P1-6: A two-hour battery does not watch a house all night

Your entire pitch is a 2 AM story. The Go2's standard 8000 mAh battery runs **1–2 hours** of
active use; the EDU's 15000 mAh pack runs **2–4 hours**. A night is eight.

`06-safety-ethics.md` already lists "robot battery dies overnight" as a failure mode with
"dashboard shows battery" as the mitigation, which is right as far as it goes — but it treats a
structural problem as an edge case. The honest framing is that **Lantern is not a robot that
walks around all night.** It is a robot that is docked and asleep, woken by an event.

This is a better story than the one you have, and it costs nothing to tell:

- The robot spends the night on a charging dock in a low posture. Radios and locomotion idle.
- What stays awake is the cheap part: the microphone, and a bed-exit signal.
- On a wake trigger it stands, and from there the state machine in `02-blueprint.md` runs
  exactly as written. Ten minutes of active intervention, then back to the dock.
- Ten-minute episodes, two or three a night, is well inside a single charge — and now the
  battery number is an argument *for* the architecture instead of a hole in it.

You do not have to build the dock. Unitree sells a charging pile and the Go2 supports it; say
"the dock is commodity, we didn't build one" and move on. What you do have to do is **say the
sentence out loud in the pitch**, because otherwise a judge does the arithmetic themselves and
concludes you didn't.

The bed-exit trigger is genuinely out of scope for 24 hours. Name it as the obvious next
integration — a bed pressure mat or a bedside PIR is a $20 part — rather than pretending the
robot is listening all night.

---

## P1-7: Your competitive table has no named products in it, and a healthcare judge knows them

`02-blueprint.md` §2 compares Lantern against *categories*: door alarms, GPS trackers, cameras,
smart speakers, PARO, facilities. It is a good table. It is also the version of the table you
write when you haven't looked at the market, and a digital-health judge will read it that way.

They will name something. The two most likely:

- **ElliQ** (Intuition Robotics) — a tabletop voice-first companion for older adults, with a
  caregiver app, commercially deployed, with published research. It is the closest thing to
  your pillars 1 and 3 that exists, and "how is this different from ElliQ?" is a question you
  should be able to answer in eight seconds.
- **Sensi.AI** — camera-free in-home *audio* monitoring for senior care that explicitly claims
  detection of nighttime wandering patterns and cognitive change, deployed across home-care
  agencies. Someone has built a large business on the passive half of your pillar 2.

Not knowing these exist reads as not having done the work. Knowing them and having a crisp
differentiator reads as the opposite — and you genuinely do have one, because neither of them
can *move*.

**Fix:** `13-landscape.md` names eight real products with a one-line differentiator each, and
gives you the two sentences to say when a judge names one.

---

## P1-8: Check the rules before you write a line — some of them bind this repo

Read this year's rules on Devpost and `go.hackmit.org/coc`. The 2023 rules are the best
available guide and contain four things that matter to you specifically:

- **Teams are 1 to 4 hackers.** You are four. Fine, and there is no room for a fifth.
- **All project code must be written during the hacking window.** Planning in advance is
  explicitly allowed, which is exactly what this repo is — nine documents, zero lines of
  project code. **Keep it that way until hacking opens.** Do not be tempted to pre-write the
  mocks or the orchestrator because they're "just scaffolding." HackMIT has disqualified teams
  for misrepresenting when work was done.
- **Open-source code and libraries are allowed but must be clearly cited** in the submission and
  the demo. You will lean on the Unitree SDK, DimOS, a detection model, and the sponsor SDKs.
  Keep a `CREDITS.md` as you go; reconstructing it at 11 AM Sunday is miserable.
- **Hardware may be brought but not assembled or programmed prior to the hacking period.** The
  Go2 is a commercial product used as sold, which is fine. Anything you flash or wire is not.

One more, non-rules but same category: **confirm the robot's SKU today.** Air, Pro, and EDU
differ in ways that decide your architecture — the Jetson Orin compute module and the long-life
battery are EDU-only, and side-follow is unavailable on Air. Find out which one you have before
you plan a night around what it can do.

---

## P1-9: At 24 hours, four metrics is one too many. Pick two.

`07-evaluation.md` is right that measurement is your cheapest differentiator, and it stays. But
it budgeted four metrics into an 8-hour block that is now 4 hours, in the small hours of the
morning, while the spine is probably still being fixed.

Two of the four carry nearly all the value:

- **Metric 3, pacing precision and recall.** This is the number behind your only genuinely novel
  claim. Non-negotiable. It is also the one that needs the mapped space, so run it before you
  tear the demo area down.
- **Metric 1, word error rate on degraded speech.** Your strongest Deepgram-track artifact, and
  the only one that requires no robot at all — which means it can be done by whoever is blocked
  on hardware, at any hour, in a corner.

The other two are cheap opportunism rather than planned work: **Metric 2 (voice latency)** falls
out for free if E1 instruments four timestamps early, and **Metric 4 (alert-to-phone)** is ten
runs of something you're testing anyway. Collect them if they collect themselves. Do not
schedule a block for them.

---

## What the second pass did not change

The revised plan is still the right project, and it is worth being explicit that nothing above
undermines it:

- Lead-away instead of blocking, with the numeric envelope — still the best thing in the deck.
- The consent and anti-impersonation architecture — still the strongest ethics story you'll see
  at the expo.
- "The navigation stack is the agitation sensor" — still the most interesting technical claim
  available to you, and P0-10 is about making it *true*, not about abandoning it.
- The morning report — still the sleeper feature.
- Claims discipline — still the thing that makes a healthcare judge trust the rest.

What changed is that the plan now has to survive 24 hours instead of 36, and two of its
assumptions about the physical world needed a specification behind them.

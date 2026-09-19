# Evaluation — the numbers on the slide

The original plan contains no measurements. On a healthcare track this is the cheapest available
differentiator: roughly four hours of work, four numbers, and almost nobody else at the expo
will have done it.

Nobody expects a trial in 36 hours. They expect evidence that you know whether your own thing
works.

**Budget:** hours 20–28, in parallel with Tier 1. **Owner:** E4 coordinates, each engineer runs
their own.

Everything below is computed from the JSONL bus log (`04-interfaces.md` rule 3), which is why
setting that up at hour 2 pays for itself.

---

## Metric 1 — Speech recognition on degraded speech (E1)

**The claim it supports:** "Deepgram handles the speech this population actually produces."
Right now that's an assertion. Make it a number.

**Procedure.** 40 utterances, recorded from consenting teammates, deliberately produced in the
patterns you're targeting:

| Category | n | Example |
|---|---|---|
| Quiet / low volume | 8 | barely audible "where am I" |
| Mumbled / slurred | 8 | poor articulation throughout |
| Mid-sentence restart | 8 | "I need to— where's the— I need to go" |
| Long internal pause | 8 | "I want to... [3 s] ...go home" |
| Repeated question | 8 | same question 4× in 2 min |

Ground-truth transcripts written by hand. Compute WER against Deepgram output, and against a
baseline (whatever's easy — Whisper-small locally, or the browser's built-in recognition).

**Report:** WER per category and overall, ours vs. baseline. **Report the categories where you
lose too.** A team that shows a category where their system underperforms is telling the judge
the other numbers are real.

**Bonus, nearly free:** the long-pause category also validates your endpointing tuning. Report
how many utterances a default 500 ms endpoint would have truncated mid-thought. That number is
your strongest single argument for the Deepgram track, because it's a design decision justified
by data rather than a feature you enabled.

---

## Metric 2 — End-to-end voice latency (E1)

**The claim:** the conversation feels alive.

**Procedure.** Instrument four timestamps: last audio frame in → final transcript → LLM first
token → first TTS audio out. 30 turns across the demo scenarios. Measure, don't estimate.

**Report:** p50 and p95 end-to-end, plus the per-stage breakdown so you can say where the time
goes. If you're over 2 s, say so and say what you'd fix — knowing your own bottleneck is the
point.

Also count **barge-in success**: of 20 deliberate interruptions, how many stopped playback in
under 300 ms. For this user, interrupting a machine that keeps talking over you is exactly the
frustration the product claims to eliminate, so this number is on-thesis.

---

## Metric 3 — Pacing detection precision and recall (E2)

**The claim:** "the robot's own navigation stack is the agitation sensor" — your best technical
claim, and the only one that's genuinely novel. It needs a number behind it.

**Procedure.** 20 scripted trials in the mapped space:

- **10 positive:** a person pacing — repeated corridor traversal with direction reversals.
- **10 negative:** ordinary movement — walking to a chair and sitting, crossing once, standing
  and turning in place, walking to the kitchen and back once, standing still.

The negatives matter more than the positives. Anything triggers on pacing; the question is
whether it triggers on someone just walking around their house.

**Report:** precision, recall, and the **false positive count, out loud**. A device that wakes a
caregiver for nothing at 3 AM gets unplugged inside a week, and saying that yourself is how you
show you understand the deployment reality rather than the demo.

**Bonus:** median lead time from detection to the person reaching the exit zone. This quantifies
the whole premise — how many seconds earlier than a door alarm does this fire? If it's 8
seconds, say 8 seconds. A real small number is more persuasive than "much earlier."

---

## Metric 4 — Event to caregiver's phone (E3)

**The claim:** the escalation is real, not a mock.

**Procedure.** 10 runs, wall clock from `alert` emitted to the phone actually buzzing. Log both
timestamps; use the phone's received-time.

**Report:** median and worst case, split into backend processing vs. Twilio/carrier delivery.
Carrier delivery will dominate and will be variable — report it honestly. A team that says
"our backend is 40 ms and carrier SMS is 2–9 seconds, which is why level 3 is a voice call" is
demonstrating systems thinking.

---

## Optional, if time — dialogue policy adherence

Nice if you have a spare hour; it makes the dialogue policy measurable rather than aspirational.

Run 20 scripted patient utterances designed to tempt the model into violations — false beliefs
("when is my wife coming home?"), memory tests, repeated questions, direct challenges ("are you
Sarah?"). Have a human grade each response against the six rules in `02-blueprint.md` §3.

**Report:** violations out of 20, by rule. The "are you Sarah?" case is the important one — it
directly tests the anti-impersonation guarantee. If it ever answers "yes," you need to know
before a judge finds it.

---

## The slide

One slide, six rows, at the end of the pitch:

```
What we measured                                    ours      baseline
────────────────────────────────────────────────────────────────────────
Word error rate, degraded speech (n=40)             __ %        __ %
  └ utterances a 500ms endpoint would have cut      __ / 40
Voice latency, mic-close → first audio (p50/p95)    __ / __ s
Barge-in stopped playback <300ms                    __ / 20
Pacing detection (n=20: 10 pos / 10 neg)            P __  R __   FP __
  └ median lead time before exit zone               __ s
Alert → caregiver's phone (median / worst)          __ / __ s
```

Fill in the blanks with real numbers, including the ones that make you look bad. That slide is
the difference between "cool robot" and "these people are serious."

## Two rules

1. **Never report a number you didn't measure.** One fabricated figure, caught, discredits the
   entire slide — and judges do ask "how did you measure that?"
2. **Report the bad ones.** Voluntarily surfacing your false-positive rate is the most
   credibility-per-second thing you can do in a hackathon pitch.

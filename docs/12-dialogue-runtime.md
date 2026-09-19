# Dialogue runtime — what actually produces the speech

Closes P0-11. Owner: **E1**, with E4 owning the guard.

`02-blueprint.md` §3 specifies the dialogue *policy* — six rules, validation therapy, never
impersonate — and it is the best writing in the repo. This document specifies the *runtime*:
what generates each utterance, how fast, and what happens when the venue wifi buckles during
judging.

## The conflict nobody noticed

Two decisions you are rightly proud of are in direct opposition, and they meet inside one of
your four metrics.

- `02-blueprint.md`: **"Endpointing tuned long."** Dementia speech has long internal pauses; a
  standard 500 ms end-of-turn cuts people off mid-thought. This is correct, it is on-thesis,
  and `08-tracks.md` makes it your headline Deepgram artifact.
- `07-evaluation.md` Metric 2: **latency measured from "last audio frame in → first audio out."**

Tuning endpointing to 1.5 s makes your own latency metric 1.5 s worse. The better your speech
handling, the worse your latency slide — measuring the exact thing you deliberately traded away.

**Fix: report two numbers, and explain the gap.**

| Number | Measured from | What it means |
|---|---|---|
| **System latency** | endpoint fired → first audio out | What your engineering controls. This is the one to optimize. |
| **Perceived latency** | last audio frame in → first audio out | System latency plus the endpoint window. Larger on purpose. |

Then say the sentence: *"Our perceived latency is higher than a standard voice agent's, and it's
deliberate — we hold the turn open about a second and a half longer because this user pauses
mid-sentence and being interrupted is the exact frustration we're claiming to remove. Here's
how many utterances a 500 ms default would have truncated."* That is a design trade defended
with data, which is worth considerably more than a fast number.

**Cheap upgrade if there's time:** start the LLM speculatively at ~500 ms of silence and cancel
if speech resumes. You get the short-endpoint latency with the long-endpoint behavior, at the
cost of some wasted tokens. Only do this once the spine is green.

---

## The three-tier response system

Not every utterance needs a language model, and the ones that matter most need it least.

### Tier 0 — reflex lines (no network, no model, pre-rendered audio on disk)

A fixed set of utterances, rendered to audio files in the consented voice **ahead of the demo**
and played from disk. Zero network, latency bounded by file read.

Everything safety- or ethics-critical lives here:

| Trigger | Line |
|---|---|
| Announce before approach | "It's me. I'm coming over to you." |
| Identity challenge ("are you Sarah?") | "No — I'm not Sarah. But Sarah recorded this for you." |
| Lead invitation | "It's night time. Come with me." |
| Yield / person advances | "Okay. I'll move." |
| Escalation begun | "I'm going to let Sarah know you're up." |
| Orientation | "It's night time. You're home. I'm here." |
| Distress override | "I'm sorry. I'll give you some room." |

Roughly fifteen lines. Render them in batch once the voice is enrolled. **These carry the demo
beats**, which means the moments a judge is actually watching never depend on three cloud round
trips over congested wifi.

### Tier 1 — cached common responses

The handful of things this user says most: asking for a person, asking what time it is, asking
where they are, asking to go home. Pre-render the responses too. Hit by normalized string match
against the transcript before anything else runs.

This also handles repeated questioning correctly *by construction*. Policy rule four says
"answer repetition as if new — same calm answer, same words, every time." A cache does that
automatically; an LLM with conversation history in context drifts toward "as I mentioned," which
is a policy violation and a clinical one. **The cache is the better implementation of the rule,
not a shortcut around it.**

### Tier 2 — the language model

Everything else. Small fast model, streaming, **hard cap of one or two sentences**.

The cap is not a latency hack bolted on. Policy rule three is "one idea per utterance," and the
clinical reason (a person with mid-stage dementia cannot hold a compound sentence) and the
engineering reason (fewer output tokens, faster first audio) are the same constraint. Say that
out loud at the table — a constraint that serves the user and the latency budget simultaneously
is a genuinely good slide.

Stream tokens into TTS at sentence boundaries rather than waiting for the full completion.

---

## Latency budget

Target: **under 2 s system latency**, endpoint to first audio.

| Stage | Budget | How to hold it |
|---|---|---|
| Final transcript after endpoint | 100–200 ms | Deepgram streaming; the transcript is already built from interims |
| Tier 0/1 cache lookup | <5 ms | Normalized string match, runs before anything else |
| LLM first token | 300–600 ms | Small model, short prompt, stream |
| LLM to sentence boundary | 200–400 ms | One-sentence cap makes this the same as first token |
| TTS time to first byte | 150–400 ms | Streaming endpoint, low-latency model tier |
| Audio out | 50 ms | Local playback |

Tier 0 and Tier 1 skip the middle four rows entirely and land around 100 ms. Instrument all six
boundaries from the first hour — Metric 2 is free if the timestamps are in the bus log, and
expensive if you add them at 4 AM.

**Keep the prompt short.** The system prompt is the six policy rules plus the patient profile
from `config_update`. Conversation history: last three or four turns, not the whole night. Long
context is latency, and for this user it is also worse behavior.

---

## The impersonation guard is code, not a prompt

The anti-impersonation guarantee is the ethical centerpiece of the pitch and it currently lives
in a system prompt. Prompts are not guarantees. A judge *will* lean toward the robot and ask
"are you Sarah?" — it is the obvious thing to try — and a prompt-only guard can fail live, in
front of the person evaluating you on exactly that claim.

Make it two-sided, deterministic, and owned by E4 in the orchestrator:

**Inbound.** Match the transcript against identity-challenge patterns — *are you*, *is that
you*, *who are you*, *is this Sarah*, the attribution name as a bare question. On a hit, bypass
the model entirely and return the Tier 0 reflex line. The model never sees the question.

**Outbound.** Before any `say` is emitted, reject generated text asserting first-person identity
— `I'm <name>`, `it's <name>`, `this is <name>`, `<name> here`. On a hit, drop it and substitute
the reflex line. Log the rejection.

Both are twenty minutes of string matching. What they buy you is the answer to the hardest
question you'll be asked: *"It's not a prompt instruction — it's a filter on both sides of the
model, and `attribution` is a required field in the message schema. If it ever generated an
identity claim, the orchestrator would drop the utterance."*

Log every rejection to the bus. If the counter is zero after a day of testing, that is a real
result you can report; if it isn't zero, you very much want to know before a judge finds out.

---

## When the network fails

A thousand hackers on shared wifi, and your worst hour is the judging hour.

**Prepare, in this order:**

1. **Phone hotspot, tethered, tested at hour 1.** Not discovered at hour 22. `05-demo.md`
   already says this for the stage demo; it applies to the table demo too.
2. **Tier 0 and Tier 1 audio rendered to disk and committed.** The demo beats then need no
   network at all. This is the single highest-value hour in the voice workstream.
3. **A local TTS fallback** (any offline engine) wired behind a flag. It sounds worse and it is
   not the family voice, but a robot that talks in a robot voice beats a robot that is silent
   while you apologize.
4. **A visible degradation indicator** in the dashboard — `voice: cached` versus `voice: live`.
   Pointing at it and saying "we're running cached because the hall wifi is saturated, here's
   the live path on the hotspot" reads as competence. Silence while nothing happens does not.

## Definition of done

- [ ] Fifteen Tier 0 lines rendered in the consented voice and on disk
- [ ] Cache lookup runs before the model, every time
- [ ] Inbound and outbound impersonation guards, with logged rejections
- [ ] Six latency boundaries timestamped into the bus log
- [ ] One-sentence output cap enforced in code, not requested in the prompt
- [ ] Barge-in stops playback in under 300 ms, including cached audio
- [ ] Full demo runs with wifi switched off, on cached audio, start to finish

# Sponsor track strategy

Verify the current track list and criteria against this year's official sponsor page before
committing — sponsor lineups and prize criteria change, and the assessment below is based on
the tracks named in the original plan.

The general principle: **sponsor track judges want to see you used their product in a way that
mattered.** A slide asserting relevance scores nothing. Four tracks you genuinely hit beats six
you gestured at, because the scattershot version makes all of your claims look thinner.

---

## Healthcare — main track. Strong, if you make the fixes.

**What wins here:** a real clinical problem, evidence you understand the care context, honest
claims, and some measurement.

**What you're bringing:**

- Nighttime exit-seeking is a genuine driver of institutionalization. Not a toy problem.
- The lead-away safety envelope, with numbers — demonstrates you understand that the hard part
  is behavioral, not navigational.
- Claims discipline. Removing the 40 Hz claim and saying *why* you removed it is worth more
  than the feature was.
- Four measured numbers, including the false positives.
- The consent architecture, enforced in schema.

**What still hurts you if you skip it:** no contact with anyone who does this work. One
conversation with a memory care nurse or family caregiver, one quote, and you move from
"plausible" to "grounded." Send it by noon Saturday.

**The fixes that are load-bearing:** kill physical intercept (P0-1), kill the clinical claim
(P0-2), get the numbers (P0-7). Without those three you're a cool robot with a safety problem.

---

## Long Lake — "Convince a Non-Believer." Your strongest secondary, and currently buried.

This is a storytelling track and you have the best story available:

> My grandmother won't use the tablet we bought her. Everyone assumes it's because she's bad at
> technology. It isn't. It's that the tablet demands she perform a competence she no longer
> has, and it fails her publicly, every single time. Every menu is a memory test she didn't
> agree to take.
>
> Lantern has no screen, no login, no menus, and no correct way to hold it. There is nothing to
> get wrong. You talk, and it's there.

Screenlessness reframed from a feature cut into a design position. Put a real person in it —
someone on the team has a grandparent — because the specificity is what makes it land.

Right now this is one line in a matrix at the bottom of the document. It should be the second
thing you say at the table.

---

## Deepgram — strong, once you have Metric 1.

Their judges see thirty teams that called the streaming API. What they rarely see is a team
that identified a *specific hard speech domain* and measured itself on it.

- Quiet, mumbled, fragmented, restarting speech from a confused speaker.
- **Endpointing tuned long, justified by data** — the count of utterances a default 500 ms
  endpoint would have truncated mid-thought. This is your best artifact for this track: a
  configuration decision defended with evidence rather than a feature you turned on. Pair it
  with the two latency numbers from `12-dialogue-runtime.md` and own the trade out loud: the
  perceived latency is higher *on purpose*, and here's the number that says why.
- WER on a purpose-built 40-utterance degraded-speech set, against a baseline.
- Barge-in and interim-result handling.

Lead with the measurement, not the integration. Everyone has the integration.

---

## ElevenLabs — strong, and the ethics work is the differentiator.

- Consented voice cloning with the consent enforced in the message schema, not in a prompt.
- **The anti-impersonation guarantee**, implemented as a deterministic filter on both sides of
  the model (`12-dialogue-runtime.md`) rather than an instruction inside it. Invite them to ask
  the robot "are you Sarah?" — a guarantee you can let a judge attack is worth far more than one
  you describe.
- Emotional inflection driven by a real detected state rather than a demo toggle.
- Low-latency streaming with barge-in, measured.

Their judges will have seen a dozen voice-cloning demos by the time they reach you. The one
that thought carefully about consent and impersonation for a vulnerable user is the one they
remember and talk about afterwards.

---

## The Token Company — fine as a side dish. Do not let it eat an engineer.

A tokens-saved counter in the dashboard corner, backed by real before/after counts on the
compressed scene-graph and sensor JSON. Two hours of backend work, assigned to whoever is green
after the 11 PM cut.

If nobody is green by then, drop it. A half-built compression layer costs you more in
integration risk than the track is worth.

---

## Ramp — drop it.

Ramp is corporate cards and spend management. Their track will be judged on whether you used
their product. "Reduces memory care staffing overhead" is a market-sizing argument, not an
integration, and a family caring for a parent at home is not issuing corporate cards. There's
no honest hook here.

Chasing it costs you pitch time and makes your other track claims look like a sweep rather than
a fit. Drop it and spend the time on Metric 1.

---

## How to talk about tracks

**Don't** open with "we're going for six tracks." It reads as prize-farming and it's the fastest
way to make a judge discount everything after it.

**Do** tell one story and let the track relevance be obvious inside it. The Deepgram judge hears
the degraded-speech problem because it's load-bearing in your story, not because you announced
it.

**Track-specific closers**, delivered in the last ten seconds if the judge is from that sponsor:

| Sponsor | Closer |
|---|---|
| Healthcare | "We cut the physical-blocking feature on safety grounds. Here's the envelope we replaced it with." |
| Long Lake | "No screen, no login, no menus. Nothing for her to get wrong." |
| Deepgram | "We tuned endpointing long because dementia speech has long internal pauses — here's how many utterances a default would have cut off." |
| ElevenLabs | "It uses her daughter's voice, and it never claims to *be* her daughter. That's enforced in the message schema." |
| Token Company | "Live counter, bottom right — that's real tokens saved on every spatial prompt." |

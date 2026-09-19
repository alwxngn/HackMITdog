# Lantern — HackMIT planning repo

Planning and scoping documents for a voice-native quadruped companion for in-home
dementia care. (Working name: **Lantern**. Previously "Project Aegis" — see
[`docs/01-judge-review.md`](docs/01-judge-review.md#p0-8-the-name) for why the name changed.)

This repo holds the **plan**, not the code — deliberately. HackMIT allows you to plan in
advance but requires all project code to be written during the hacking window, so nothing here
is implementation and nothing should become implementation until hacking opens. See
[`docs/10-second-pass.md`](docs/10-second-pass.md) P1-8.

It exists so that four engineers can agree on scope, interfaces, and the demo before anyone
writes a line, because the most common way a 4-person hardware hack dies is integration at the
seam, in the middle of the night.

## Read this first: the clock

**HackMIT is 24 hours, not 36**, and HackMIT 2026 runs September 19–20. The original build plan
assumed 36 hours and every gate in it was wrong; it has been rewritten against a real wall
clock in [`docs/03-build-plan.md`](docs/03-build-plan.md). Confirm this year's exact start and
end times on `dayof.hackmit.org` and shift the schedule before relying on it.

## Read in this order

| Doc | What it's for | Who needs it |
|---|---|---|
| [`docs/01-judge-review.md`](docs/01-judge-review.md) | Teardown of the original plan from a judge's seat | Everyone, first |
| [`docs/10-second-pass.md`](docs/10-second-pass.md) | Second teardown, of the revised plan. The clock, and the two unspecified dependencies | Everyone, immediately after |
| [`docs/02-blueprint.md`](docs/02-blueprint.md) | The revised product: what we are actually building | Everyone |
| [`docs/03-build-plan.md`](docs/03-build-plan.md) | 24-hour schedule, ownership, cut lines | Everyone |
| [`docs/04-interfaces.md`](docs/04-interfaces.md) | Frozen event schemas so we can work in parallel | Everyone, in the first 90 minutes |
| [`docs/15-dev-workflow.md`](docs/15-dev-workflow.md) | Repo layout, git rules, and running four different AI coding agents without them colliding | Everyone, before anyone opens an agent |
| [`docs/11-perception.md`](docs/11-perception.md) | How the person actually gets tracked. Six things depend on it | E2, E4 |
| [`docs/12-dialogue-runtime.md`](docs/12-dialogue-runtime.md) | What produces each utterance, the latency budget, the impersonation guard | E1, E4 |
| [`docs/14-companion-and-caretaker.md`](docs/14-companion-and-caretaker.md) | Check-in relay, companionship conversation, onboarding schedule, guided walks, the completed wandering policy | Everyone |
| [`docs/05-demo.md`](docs/05-demo.md) | Table demo, stage demo, fallback ladder | Everyone |
| [`docs/06-safety-ethics.md`](docs/06-safety-ethics.md) | Safety envelope, consent, privacy, claims discipline | Everyone |
| [`docs/07-evaluation.md`](docs/07-evaluation.md) | The numbers we put on the slide | E1, E2, E4 |
| [`docs/08-tracks.md`](docs/08-tracks.md) | Sponsor track strategy, honestly assessed | Whoever pitches |
| [`docs/13-landscape.md`](docs/13-landscape.md) | Named prior art, and the answer when a judge names one | Whoever pitches |
| [`docs/09-judge-qa.md`](docs/09-judge-qa.md) | Anticipated questions and our answers | Whoever pitches |

## The one-sentence pitch

When someone with dementia gets up at 2 AM and starts heading for the front door, a door
alarm tells the family too late and tells them nothing; Lantern is there at the moment of
confusion, uses the same redirection technique a trained memory-care aide would, and hands
the caregiver a head start plus a record of exactly what happened.

## The hard rules

1. The robot never blocks, corners, touches, or herds a person. It leads. See `docs/06`.
2. No unvalidated clinical claims in the pitch, the UI, or the README. See `docs/06`.
3. The demo that must work is the one that doesn't need the robot. Hardware is upside. See `docs/03`.
4. Backup demo video is recorded by 6 AM Sunday. Non-negotiable. See `docs/05`.
5. Interfaces in `docs/04` freeze 90 minutes in. Changes after that need all four engineers to agree.
6. No project code before hacking opens, and cite every open-source dependency in `CREDITS.md`
   as you add it. See `docs/10` P1-8.
7. Four people, four different AI coding agents, one folder each, no long-lived branches, tiny
   commits. See `docs/15`.

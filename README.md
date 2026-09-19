# Lantern — HackMIT planning repo

Planning and scoping documents for a voice-native quadruped companion for in-home
dementia care. (Working name: **Lantern**. Previously "Project Aegis" — see
[`docs/01-judge-review.md`](docs/01-judge-review.md#p0-8-the-name) for why the name changed.)

This repo currently holds the **plan**, not the code. It exists so that four engineers can
agree on scope, interfaces, and the demo before anyone writes a line, because the most
common way a 4-person hardware hack dies is integration at hour 30.

## Read in this order

| Doc | What it's for | Who needs it |
|---|---|---|
| [`docs/01-judge-review.md`](docs/01-judge-review.md) | Teardown of the original plan from a judge's seat | Everyone, first |
| [`docs/02-blueprint.md`](docs/02-blueprint.md) | The revised product: what we are actually building | Everyone |
| [`docs/03-build-plan.md`](docs/03-build-plan.md) | 36-hour schedule, ownership, cut lines | Everyone |
| [`docs/04-interfaces.md`](docs/04-interfaces.md) | Frozen event schemas so we can work in parallel | Everyone, by hour 4 |
| [`docs/05-demo.md`](docs/05-demo.md) | Table demo, stage demo, fallback ladder | Everyone |
| [`docs/06-safety-ethics.md`](docs/06-safety-ethics.md) | Safety envelope, consent, privacy, claims discipline | Everyone |
| [`docs/07-evaluation.md`](docs/07-evaluation.md) | The numbers we put on the slide | E1, E2, E4 |
| [`docs/08-tracks.md`](docs/08-tracks.md) | Sponsor track strategy, honestly assessed | Whoever pitches |
| [`docs/09-judge-qa.md`](docs/09-judge-qa.md) | Anticipated questions and our answers | Whoever pitches |

## The one-sentence pitch

When someone with dementia gets up at 2 AM and starts heading for the front door, a door
alarm tells the family too late and tells them nothing; Lantern is there at the moment of
confusion, uses the same redirection technique a trained memory-care aide would, and hands
the caregiver a head start plus a record of exactly what happened.

## The hard rules

1. The robot never blocks, corners, touches, or herds a person. It leads. See `docs/06`.
2. No unvalidated clinical claims in the pitch, the UI, or the README. See `docs/06`.
3. Backup demo video is recorded by hour 30. Non-negotiable. See `docs/05`.
4. Interfaces in `docs/04` freeze at hour 4. Changes after that need all four engineers to agree.

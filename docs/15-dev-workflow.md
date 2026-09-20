# Dev workflow — four people, four different AI coding agents, one repo

The team split in `03-build-plan.md` (E1 voice, E2 robot, E3 cloud, E4 orchestrator) already
solves *who does what*. This document solves the problem that split doesn't: **four engineers
probably means four different AI coding tools** (Cursor, Claude Code, Copilot, Codex CLI,
whatever), none of which share context with each other, all of which can generate thirty
minutes of diff in ninety seconds. That combination breaks a normal PR-review workflow, and it
breaks it fastest exactly where `01-judge-review.md` P0-5 already said projects die: the seam.

The fix isn't a process. It's **making the seam a file, not a conversation** — which
`04-interfaces.md` already did for humans. This document extends the same idea to agents that
have never seen each other's chat history and never will.

## 1. Repo layout: one folder per subsystem, one owner per folder

```
/voice/          — E1. Deepgram, ElevenLabs, dialogue policy, prosody.
/robot/          — E2. DimOS/Unitree, tracker, lead-away/follow controller; dog camera relay URL for Night Watch.
/cloud/          — E3. FastAPI, WebSocket, React portal, Twilio.
/orchestrator/   — E4. State machine, event bus, mocks, impersonation guard.
/bus/            — shared schema definitions from 04-interfaces.md. E4 owns it. Everyone reads it.
/docs/           — this repo. Read-only during hacking. The plan, not the code.
AGENTS.md        — root steering file, below.
CREDITS.md       — open-source citations, updated as you add a dependency.
```

**The rule that matters most:** each person's AI agent primarily reads and writes inside their
own subsystem folder. It reads `/bus` and `/docs` for context but doesn't write there without a
human in the loop (§4). Different agents literally not touching the same files is a much
stronger guarantee than "please don't step on each other," because it doesn't depend on four
different AI products all interpreting a polite request the same way.

## 2. `AGENTS.md` — the one file every agent has to find

Whatever brand of coding agent each person uses, point it at a root `AGENTS.md` (several tools
now auto-discover this filename; for the ones that don't, paste it into the first prompt of the
session). It should be short — a few dozen lines — and contain only what every agent needs
regardless of which subsystem it's working in:

- Link to `04-interfaces.md`: **the schemas are frozen; don't invent new message types or
  rename fields.** If the task seems to need one, stop and say so instead of improvising.
- Link to `06-safety-ethics.md`'s hard rules (never block, never impersonate, consent before
  any cloned voice, yield reflex is a controller-level reflex not a state transition).
- The subsystem boundary from §1: "you are working in `/robot`; read `/bus` and `/docs`, don't
  write outside `/robot` without flagging it to a human first."
- Where the mocks are (`mock_robot`, `mock_patient`, `mock_mic` — Tier 2's `GUIDE_HOME` reuses
  `mock_robot` rather than needing a fourth) and the instruction to run against them before
  declaring anything done.

This is the only piece of "implementation" that's fair game to write before hacking opens —
it's configuration for how you'll work, not project code. Draft it this week; don't touch
`/voice`, `/robot`, `/cloud`, or `/orchestrator` until the clock starts (`10-second-pass.md`
P1-8, and see §6 below).

## 3. Git: trunk-based, tiny commits, no long-lived branches

Feature branches assume a review cycle you don't have time for, and they assume diffs arrive at
human speed. Neither is true here — an agent can hand you two hours of hand-written-equivalent
work in one turn, and a branch that's a few hours old will conflict badly by the time it merges.

- **Everyone commits straight to `main`.** No PRs, no review queue. This only works because §1
  keeps people out of each other's files.
- **Commit before you hand the agent a prompt that touches shared surface** (anything in
  `/bus`, a cross-cutting refactor, anything you're not sure about) — that commit is your
  rollback point if the agent's change is wrong. `git reset --hard` costs you nothing if the bad
  change is isolated in its own commit; it costs you real work if it's tangled into everything
  else you did that hour.
- **Commit after every agent turn that changes behavior**, not once an hour. `03-build-plan.md`'s
  standing rule ("commit and push every hour") was written for human-speed work; tighten it —
  hourly is now a ceiling, not a cadence. Small, frequent commits are strictly better with an AI
  agent in the loop: cheaper to review, cheaper to revert, cheaper to bisect at 3 AM.
- **Pull before you prompt.** Rebase or just re-pull at the start of every agent session, since
  three other people are pushing to `main` continuously. Stale context is how an agent
  confidently rewrites something that already changed underneath it.
- **A merge conflict outside your own folder is a "stop and get in the room" event**, not
  something to resolve solo or auto-resolve. If two people's changes collide in `/bus`, that's
  the interface-freeze rule from `04-interfaces.md` firing exactly as designed — treat it the
  same way: all four, out loud, decide, then one person commits the resolution.

## 4. The schema file is the one file nobody's agent edits alone

`/bus`'s schema definitions are the seam. E4 owns them, same as E4 owns the orchestrator in
`02-blueprint.md` §4. If E2's agent decides the `follow_person` command needs one more argument,
that's a real need but not a unilateral edit — E2 says so out loud, E4 makes the change, everyone
else's next `git pull` picks it up. This is the same discipline `04-interfaces.md` already
states for humans ("changes after the freeze need all four engineers to agree, in the same
room, out loud") — it just matters more now, because an agent will happily "fix" a schema
mismatch by changing the schema instead of its own code, and it won't know that three other
subsystems depend on the field it just renamed.

## 5. Sync points, reused from the existing gate structure

You don't need continuous sync if the folders are separate and the schema is frozen — you need
sync *at the gates that already exist* in `03-build-plan.md`:

| Gate | What "sync" means here |
|---|---|
| 1:15 PM — interfaces frozen | Everyone pulls `/bus` after it's written. This is the one schema everyone's agent needs before doing anything else. |
| 2:30 PM — mocks live | Everyone pulls `/orchestrator`'s mocks. From here, each subsystem develops and tests against mocks independently — this is the point where four people (and four agents) genuinely stop needing to coordinate in real time. |
| 6:00 PM — spine green | Full-team pull and a real end-to-end run. Any drift between what someone's agent *thinks* the schema is and what's actually in `/bus` shows up here, not at 2 AM. |
| 11:00 PM — the cut | Pull, re-sync scope against whatever E4 decided, and update `AGENTS.md` if the cut changes what any subsystem's agent should still be building. |
| 5:00 AM — feature freeze | Last sync. After this, commits are fixes and rehearsal only — no agent should be handed a prompt that adds scope. |

Between gates: work in your own folder, against the mocks, and don't wait on anyone.

## 6. What agents should not be asked to do before hacking opens

Everything in this document — the folder layout, `AGENTS.md`, the git rules — is workflow
configuration, and it's fine to have ready. **It is not fine to have any agent generate
`/voice`, `/robot`, `/cloud`, or `/orchestrator` code before the hacking window opens**, even as
a "draft" you plan to redo. HackMIT requires project code to be written during the hacking
window (`10-second-pass.md` P1-8), and "an agent wrote it Thursday and I re-ran the prompt
Saturday" is not meaningfully different from writing it by hand Thursday. If you want to
de-risk a subsystem in advance, write more plan (a doc, a schema sketch inside `04-interfaces.md`)
— don't write code.

## 7. Human-in-the-loop, non-negotiably, for four specific things

Agents move fast and code that looks right is not the same as code that is right. Everyone
should personally read, not just skim, the agent-generated implementation of:

1. **The yield reflex** (`06-safety-ethics.md` §1) — it's the thing a judge will physically
   test, and it has to be a controller-level reflex, not something that only fires if the
   orchestrator's state machine happens to be in the right state.
2. **The impersonation guard** (`12-dialogue-runtime.md`) — inbound and outbound, both sides of
   the model. This is the one a judge asks about directly ("are you Sarah?"), and it's exactly
   the kind of thing an agent will implement as "good enough" pattern matching unless someone
   checks the edge cases by hand.
3. **The consent gate on cloned voice** (`06-safety-ethics.md` §3) — `consent_recorded_ts`
   actually blocking a `say` with no timestamp, not just checked and logged.
4. **The `dont_go` breach and `CONFIRM_HOME` re-ask** (`14-companion-and-caretaker.md` §6) —
   the newest and least-tested logic in the plan, and the one where "close enough" produces a
   robot that either doesn't escalate when it should or marches someone home without asking
   twice.

Everything else — dashboard styling, the onboarding form, the morning-report query — ship
whatever the agent produces and move on. Spend the human attention where a mistake is a safety
or ethics failure, not a UI nit.

## 8. Quick reference

- One folder per engineer, one shared `/bus` folder owned by E4, `/docs` read-only.
- `AGENTS.md` at the root, every agent pointed at it, before any subsystem code exists.
- Trunk-based, tiny commits, commit before any risky prompt, pull before every session.
- Schema changes: say it out loud, E4 edits `/bus`, everyone pulls. Never a unilateral agent edit.
- Sync at the five existing gates, not continuously.
- No agent writes subsystem code before the clock starts.
- Four things get a human's actual eyes on the diff, every time: yield reflex, impersonation
  guard, voice consent gate, `CONFIRM_HOME`.

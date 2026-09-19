# Lantern — agent steering (all subsystems)

- Schemas in `docs/04-interfaces.md` are **frozen**. Do not invent message types or rename
  fields. If a task seems to need one, stop and tell a human — E4 owns `/bus`.
- Safety hard rules (`docs/06-safety-ethics.md`): never block a person; never impersonate;
  consent before cloned voice; yield reflex is controller-level.
- One folder per owner: `/voice` E1, `/robot` E2, `/cloud` E3, `/orchestrator` E4.
  Read `/docs` and `/bus`. Do not write outside your folder without flagging a human.
- Develop against mocks (`mock_robot`, `mock_patient`, `mock_mic`, Tier 2 `mock_gps`) before
  declaring anything done.
- Cite new open-source deps in `CREDITS.md` when you add them.

## E3 /cloud

- You work in `/cloud` only. Never import Unitree or DimOS SDKs.
- Dashboard renders from the event stream alone — no demo mode.
- Map coordinates: metres, origin = SW corner of taped area, +x east
  (`docs/16-e3-portal.md`).
- Human attention: escalation ladder timers + ack cancellation — not UI polish.

## E4 /orchestrator + /bus

- Own `/orchestrator` and `/bus`. Portal stays in `/cloud`; bridge via `POST /api/ingest`.
- Spine on mocks: `cd orchestrator && python run_spine.py` (cloud API must be on :8000).
- Mocks speak `04-interfaces` only. No Unitree/DimOS in this folder.

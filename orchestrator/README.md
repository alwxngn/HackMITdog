# /orchestrator — state machine, mocks, spine runner (E4)

Owns the product spine: `IDLE → ATTEND → LEAD → ESCALATE → EMERGENCY`, mocks, and the
bridge into `/cloud`. Schemas: [`docs/04-interfaces.md`](../docs/04-interfaces.md).

## Install

```bash
cd orchestrator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# bus package on PYTHONPATH via run_spine (adds ../bus)
```

## Spine on mocks (6 PM prototype)

**Terminal 1 — cloud API**

```bash
cd cloud && source .venv/bin/activate
cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — portal (optional)**

```bash
cd cloud/web && npm run dev
# http://127.0.0.1:5173/watch
```

**Terminal 3 — spine**

```bash
cd orchestrator && source .venv/bin/activate
python run_spine.py --scenario exit_seeking
```

What you should see:

1. `mock_patient` walks bedroom → hallway → Don't-go
2. Orchestrator publishes `agent_state` ATTEND → LEAD → ESCALATE + `alert` + `say` + `command`
3. `mock_robot` accepts `lead_to` and emits `pose` / `robot_status`
4. Bridge POSTs every message to `cloud /api/ingest` → Night Watch updates
5. Twilio SMS fires (or console dry-run); ack from the portal cancels the ladder and returns IDLE

Bus hub also listens on **:9000** (`POST /publish`, `WS /ws`) for E1/E2 CLIs.

```bash
# Automated check (cloud must be on :8000)
python verify_spine.py
```

## Standalone mocks

```bash
# Needs hub: python ../bus/run_hub.py
python mocks/mock_patient.py --scenario exit_seeking --hub http://127.0.0.1:9000
python mocks/mock_robot.py --fail-rate 0
```

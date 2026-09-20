# /bus — shared event bus (E4)

Frozen schemas: [`docs/04-interfaces.md`](../docs/04-interfaces.md).

## Install

```bash
cd bus
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run hub (multi-process)

```bash
cd bus && source .venv/bin/activate
python run_hub.py --port 9000
```

- `POST http://127.0.0.1:9000/publish` — publish an envelope
- `WS  ws://127.0.0.1:9000/ws` — subscribe
- JSONL log: `bus/bus_events.jsonl`

For the full mock spine (hub + mocks + orchestrator + cloud bridge), prefer:

```bash
cd orchestrator && python run_spine.py
```

# /cloud — Lantern caregiver portal (E3)

See [docs/16-e3-portal.md](../docs/16-e3-portal.md) for the full playbook.

## Quick start

```bash
# API
cd cloud
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill Twilio for real SMS
cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Portal (other terminal)
cd cloud/web && npm install && npm run dev
# open http://127.0.0.1:5173
```

## Fixture replay (no mocks needed)

```bash
cd cloud/server
python replay.py --fixture ../fixtures/exit_seeking.jsonl --rate 4
```

## Twilio spike

1. Copy `.env.example` → `.env`, fill `TWILIO_*` (trial: verify the destination number).
2. `cd cloud/server && python twilio_spike.py`
3. Confirm SMS arrives; tap the ack link → dashboard alert clears.

Without credentials, `notify.py` dry-runs to the console so the ladder still demos.

## Bridge for E4

When mocks / orchestrator are live, POST bus messages to:

`POST http://127.0.0.1:8000/api/ingest`

That is the only swap needed until a shared `/bus` transport lands — `bus.py` stays the adapter.

## Reset

`POST /api/reset` — clears JSONL projection, timeline, alerts, ladder timers, check-in queue.

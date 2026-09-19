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

## Phone + QR (same app, browser on phone)

Phones cannot open `localhost` on your laptop. Tunnel **Vite :5173** (it already proxies `/api` and `/ws` to FastAPI).

```bash
# Install once: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
cloudflared tunnel --url http://127.0.0.1:5173
# or: ngrok http 5173
```

Copy the HTTPS URL into both places, then restart Vite:

```bash
# cloud/web/.env.local
VITE_PUBLIC_ORIGIN=https://YOUR-SUBDOMAIN.trycloudflare.com

# cloud/.env
ACK_BASE_URL=https://YOUR-SUBDOMAIN.trycloudflare.com
```

1. Laptop Night Watch shows **Share on phone** QR codes (Night Watch + Onboarding).
2. Scan Onboarding → enter zones / home / schedule → Publish.
3. Scan Night Watch (or tap the link) → live dashboard on the phone; laptop stays the judge screen.
4. Ack from either device clears the alert on both (shared WebSocket / event store).

## Fixture replay (no mocks needed)

```bash
cd cloud/server
python replay.py --fixture ../fixtures/exit_seeking.jsonl --rate 4
```

## Twilio

1. Copy `.env.example` → `.env`, fill `TWILIO_*` (trial: verify the destination number).
2. `cd cloud/server && python twilio_spike.py`
3. Confirm SMS arrives.

**Trial vs upgrade**

| | Trial (`TWILIO_TRIAL=1`) | Upgraded (`TWILIO_TRIAL=0`) |
|---|---|---|
| Real SMS to your phone | Yes | Yes |
| Message body | Twilio stock template (`sms_account_alerts`) | Custom “Arthur is heading…” + ack URL |
| Ack link in SMS | Not in stock template | Works when `ACK_BASE_URL` is the tunnel HTTPS URL |

Without credentials, `notify.py` dry-runs to the console so the ladder still demos.

## Bridge for E4

When mocks / orchestrator are live, POST bus messages to:

`POST http://127.0.0.1:8000/api/ingest`

That is the only swap needed until a shared `/bus` transport lands — `bus.py` stays the adapter.

## Reset

`POST /api/reset` — clears JSONL projection, timeline, alerts, ladder timers, check-in queue.

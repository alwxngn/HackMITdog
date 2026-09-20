# /cloud — Lantern caregiver portal (E3)

See [docs/16-e3-portal.md](../docs/16-e3-portal.md) for the full playbook.

**Teammates (E1 voice, etc.):** you need **two processes** — API + React. Install once, then run both.

**Mobile check-in is now integrated:** use the existing dashboard Check-in card or the new
Welcome **Check in** button. See [combined portal + phone setup](../voice/PORTAL_SETUP.md).
The cloud API mounts phone audio at `/voice`; do not run a separate voice server on port 8000.

## Prerequisites

| Tool | Check |
|---|---|
| Python 3.11+ | `python3 --version` |
| Node.js 20+ | `node -v` / `npm -v` |

## Install everything (once)

From the **repo root**:

```bash
# Backend deps
cd cloud
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Twilio optional for SMS; leave blank to dry-run

# Frontend deps
cd web
npm install
```

Or one shot from `cloud/`:

```bash
cd cloud
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp -n .env.example .env
(cd web && npm install)
```

## Run the whole portal (two terminals)

**Terminal 1 — API**

```bash
cd cloud
source .venv/bin/activate
cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend**

```bash
cd cloud/web
npm run dev
```

Open **http://127.0.0.1:5173**

| URL | Screen |
|---|---|
| http://127.0.0.1:5173/ | Welcome + phone QR |
| http://127.0.0.1:5173/onboarding | Scan home → paint zones → schedule |
| http://127.0.0.1:5173/watch | Night Watch dashboard (live map / alerts / check-in) |

Demo alert without the robot:

```bash
cd cloud/server
python replay.py --fixture ../fixtures/exit_seeking.jsonl --rate 4
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

## Onboarding

Open `/onboarding` (or QR). Flow: Patient → **Scan home** → Paint zones → Schedule.

- `MAP_SCAN_MODE=demo` (default): Scan loads a schematic floorplan.
- `MAP_SCAN_MODE=live`: publishes `map_scan_request`; E2 must POST `map_ready` to `/api/ingest`.
- Paint: whole map starts Safe (green); drag Watch / Don't go; Place home pin.
- Finish publishes one `config_update`.

**Live map smoke (no robot):**

```bash
cd cloud && source .venv/bin/activate
python scripts/smoke_live_map.py
```

Sample E2 payload: [`fixtures/sample_map_ready.json`](fixtures/sample_map_ready.json). Frame + checklist: [`docs/16-e3-portal.md`](../docs/16-e3-portal.md).

3-D map artifacts are served through the API at `/api/maps/<filename>`. Set
`LANTERN_MAP_ARTIFACT_DIR` if the robot writes maps outside the repository's
default `artifacts/maps` directory. Pass the frontend-visible URL as
`artifact_url` when calling `map_room`, for example:

```text
http://127.0.0.1:5173/api/maps/floor_map.ply
```

### Dog camera (on-demand)

```bash
# cloud/.env — off by default
DOG_CAMERA_ENABLED=1
DOG_CAMERA_URL=http://127.0.0.1:7780/   # DimOS cockpit; see robot/README.md
```

Night Watch shows **View dog camera**; alert modal can soft-offer open. No always-on feed.

See [docs/16-e3-portal.md](../docs/16-e3-portal.md) for the E2 bus contract.

## Twilio

1. Copy `.env.example` → `.env`, fill `TWILIO_*` (trial: verify the destination number).
2. `cd cloud/server && python twilio_spike.py`
3. Confirm SMS arrives.

**Trial vs upgrade**

| | Trial (`TWILIO_TRIAL=1`) | Upgraded (`TWILIO_TRIAL=0`) |
|---|---|---|
| Real SMS to your phone | Yes | Yes |
| Message body | Twilio stock template (`sms_account_alerts`) | Custom “Susan is heading…” + ack URL |
| Ack link in SMS | Not in stock template | Works when `ACK_BASE_URL` is the tunnel HTTPS URL |

Without credentials, `notify.py` dry-runs to the console so the ladder still demos.

## Bridge for E4 / voice

Spine runner (`orchestrator/run_spine.py`) POSTs every bus message to:

`POST http://127.0.0.1:8000/api/ingest`

Optional: set `LANTERN_ORCH_PUBLISH_URL=http://127.0.0.1:9000` in `cloud/.env` so
caregiver acks/checkins also POST to the bus hub.

Check-in from the dashboard hits the API and publishes a `checkin`; the orchestrator turns it
into a `say` when IDLE. Until a shared transport lands, `bus.py` + the spine bridge are the seam.

## Reset

`POST /api/reset` — clears JSONL projection, timeline, alerts, ladder timers, check-in queue.

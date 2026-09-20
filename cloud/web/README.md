# Night Watch portal (frontend)

React + Vite UI for Lantern. Lives under `/cloud/web`. Needs the FastAPI backend running too — full setup is in [`../README.md`](../README.md).

## Prerequisites

- **Node.js 20+** (`node -v`)
- Backend on `http://127.0.0.1:8000` (see parent README)

## Install (once)

```bash
cd cloud/web
npm install
```

Optional phone tunnel: copy `.env.example` → `.env.local` and set `VITE_PUBLIC_ORIGIN` (see parent README).

## Run

```bash
cd cloud/web
npm run dev
```

Open **http://127.0.0.1:5173**

| Path | What |
|---|---|
| `/` | Welcome / QR share |
| `/onboarding` | Zones + schedule |
| `/watch` | Live Night Watch dashboard |

Vite proxies `/api` and `/ws` to the backend on port 8000 — you do **not** need to point the browser at `:8000` for the UI.

## Other scripts

```bash
npm run build    # production build
npm run preview  # serve the build
npm run lint     # oxlint
```

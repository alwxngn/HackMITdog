# Combined portal + phone voice

The caregiver app is the existing E3 React portal, unchanged apart from the check-in addition.
The welcome page has a **Check in** button. Night Watch uses its existing Check-in card and
Timeline. Onboarding, styling, maps, alerts, reports and navigation remain the E3 versions.

The voice service is mounted inside the cloud API at `/voice`; do **not** run the old standalone
voice server on port 8000 alongside it. The phone only needs Start, the spoken message,
Talk/Finish, Stop and an optional typed reply. API keys remain in the ignored repository-root
`.env`. The phone never receives them.

## Run on Windows

From the repository root, install once:

```powershell
.\.venv\Scripts\python.exe -m pip install -r cloud/requirements.txt -r voice/requirements.txt
npm --prefix cloud/web ci
```

Terminal 1, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir cloud/server --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd cloud/web
npm run dev
```

Open **http://127.0.0.1:5173/**. The old standalone caregiver page is not used; `/voice/`
redirects to the portal root. Provider health is at `/voice/api/health` on the same origin.

## Phone pairing

1. Open the portal's **HTTPS** URL on the laptop (see tunnel instructions below).
2. Click **Check in** on Welcome, or use the existing **Check-in** card on `/watch`.
3. Enter the sender's name and click **Connect phone**.
4. Scan the QR on the phone. It opens `/voice/phone` with private session credentials.
5. Tap **Start Lantern** on the phone and leave it unlocked with the page visible.
6. On the laptop, send a message or leave it blank to ask how the person is feeling.
7. The phone speaks with ElevenLabs. Tap **Talk to Lantern**, allow microphone access,
   speak, then tap **Finish and send reply**.
8. Deepgram transcribes the recording. The reply appears in the check-in panel and in the
   original Night Watch **Timeline**. A short scripted reply plays on the phone.

The patient's name comes from existing onboarding. Sender names are applied on each check-in.
Check-ins are rejected during a safety state (anything other than IDLE/ATTEND); they are not
silently played over a safety interaction or falsely labeled as queued. The actual E4 queue
can replace this gate later. Closing the check-in panel does not stop the phone; reopening it
restores the session. Browser reload preserves pairing until the server restarts or it expires.

## Robot requests on the paired phone

The phone has two sections: **Caregiver check-in** for replies, and **Talk to
the robot** for movement requests. Tap **Speak a robot request**, say “let's go
on a walk”, then tap **Finish and send request** (recording also stops after
10 seconds). A typed request is available in the same section. Robot requests
work before a caregiver check-in and do not mark an existing check-in as answered.

The cloud API needs `LANTERN_ORCH_PUBLISH_URL=http://ROBOT_BUS_HOST:9000` in
`cloud/.env`; restart the API after changing it. Use `127.0.0.1` only if the
bus runs on the API's computer. The existing bus, orchestrator, and DimOS command
bridge must be running as described in [the robot runbook](../robot/VOICE_WALK_RUNBOOK.md).
The phone sends existing transcript messages through that route; it does not
call robot hardware directly. Check-in replies stay in the check-in flow.

**Robot activity** shows the portal's event stream. “Request sent” alone does
not mean the robot moved. “Take me home” displays the orchestrator's confirmation
prompt; answer by voice or use **Yes, go home** / **Keep walking**. “Stop” also
works while that confirmation is pending. If delivery fails, the phone shows
the error and does not automatically replay the movement request.

For a mock run, use the runbook's mock spine, never the live DimOS consumer at
the same time. Regression checks (no hardware or paid provider calls):

```powershell
.\.venv\Scripts\python.exe -m unittest voice.tests.test_robot_pipeline
.\.venv\Scripts\python.exe -m unittest voice.tests.test_portal_bridge
.\.venv\Scripts\python.exe -m unittest voice.tests.test_robot_phone_ui voice.tests.test_playback_handoff
```

## One tunnel for everything

The teammate's repo uses a **Quick Tunnel to localhost:5173**. Its public URL forwards to the
computer running that `cloudflared` process. Copying the URL or pulling his code does not
make his tunnel serve your laptop.

- **Use his working tunnel:** he needs to run this integrated branch's API and frontend on
  his laptop, with his own local provider keys, and keep his tunnel running. Use his URL on
  both the caregiver laptop and patient phone. No second voice tunnel is needed.
- **Run here:** tunnel your own frontend, using HTTP/2 to avoid the QUIC timeout you saw:

  ```powershell
  cloudflared tunnel --protocol http2 --url http://127.0.0.1:5173
  ```

Set `cloud/web/.env.local` to the actual generated URL (not the placeholder):

```dotenv
VITE_PUBLIC_ORIGIN=https://YOUR-SUBDOMAIN.trycloudflare.com
```

Restart Vite. This both allows the exact tunnel hostname through Vite's host check and makes
the QR codes point to it. When using a different tunnel URL, update this setting and restart
Vite again. Existing E3 onboarding/share QR codes still work.

Vite forwards `/api`, `/ws`, and **all `/voice` HTTP/WebSocket traffic** to the one cloud API.
The phone and portal must reach the same running backend; a session created on your laptop
does not exist on your teammate's server. Do not mix his public URL with your local backend.

If TCP/HTTP2 also times out, port 7844 may be blocked by the network. Use a working network or
hotspot on the hosting laptop, or have the teammate host the integrated app on his working
connection. This code cannot route through a tunnel connector running on a different laptop
without that laptop serving or forwarding the integrated app.

[Cloudflare Quick Tunnel behavior](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
and [Vite host/proxy settings](https://vite.dev/config/server-options).

## Integration boundary

`cloud/server/voice_bridge.py` mounts the existing voice service and forwards its `checkin`,
`say`, `transcript`, and `speech_state` envelopes to the existing cloud bus, store, and WebSocket.
No shared schemas were changed. Local playback completion is mapped to the existing `idle`
speech state. Voice pairing/status uses its existing separate transport under `/voice`.

The standalone voice launch remains available for E1 development; the integrated demo should
always start `cloud/server/main.py` as above. The original `/api/checkin` endpoint remains for
E4/external bus clients; the new portal control uses the paired voice endpoint to confirm
actual phone availability and playback status.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s voice/tests -v
npm --prefix cloud/web run build
```

With both servers running and provider keys enabled, the explicit live browser test is:

```powershell
.\.venv\Scripts\python.exe voice/tests/portal_browser_smoke.py
```

It uses Chrome, both live APIs, and synthetic microphone audio through MediaRecorder; it
consumes a small amount of provider credit. It checks the welcome button, pairing, phone
playback, transcript arrival in the existing timeline, and navigation back to onboarding.

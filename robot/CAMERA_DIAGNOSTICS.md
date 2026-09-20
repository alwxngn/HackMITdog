# Dog camera feed diagnostics report

## Current evidence

The cloud API reports:

```json
{
  "enabled": true,
  "master_enabled": true,
  "url": "http://127.0.0.1:9877/",
  "stream_url": null,
  "proxy_stream": null
}
```

This proves that:

- The cloud API is reading `DOG_CAMERA_ENABLED=1`.
- The cloud API is reading `DOG_CAMERA_URL`.
- The frontend camera button is allowed to activate.

It does **not** prove that port `9877` serves a usable camera page.

The following command also showed a process listening on the port:

```bash
lsof -nP -iTCP:9877 -sTCP:LISTEN
```

That proves a process owns the port, but not that it returns valid HTTP, a
camera viewer, or an iframe-compatible page.

## Run these checks in order

Run them on the same Mac where the `9877` process is running:

```bash
curl -v --max-time 5 http://127.0.0.1:9877/
```

```bash
open http://127.0.0.1:9877/
```

```bash
lsof -nP -iTCP:9877 -sTCP:LISTEN
```

Interpretation:

| Result | Meaning | Next step |
|---|---|---|
| Connection refused or timeout | Listener is not serving HTTP correctly | Check the DimOS/cockpit process logs and startup command |
| HTTP 404/plain text | Port is not the viewer root | Find the actual cockpit/WebRTC viewer path |
| A working viewer page | DimOS viewer is alive | Check iframe policy and browser console errors |
| Redirect/login page | Viewer needs a session or authentication | Open/authenticate the viewer directly first |

## Check the Lantern API configuration

```bash
curl http://127.0.0.1:8000/api/camera/status
```

Expected:

```json
{
  "enabled": true,
  "url": "http://127.0.0.1:9877/"
}
```

If the values are wrong, set `cloud/.env`:

```dotenv
DOG_CAMERA_ENABLED=1
DOG_CAMERA_URL=http://127.0.0.1:9877/
```

Restart the API after changing `.env`:

```bash
cd /Users/laminegueye/Desktop/repos/HackMITdog
source cloud/.venv/bin/activate
cd cloud/server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Browser and network checks

If `http://127.0.0.1:9877/` works directly but the embedded panel is blank,
open browser DevTools → Console and look for:

```text
Refused to display ... in a frame
```

This means the DimOS page sends `X-Frame-Options` or CSP that blocks iframe
embedding. The Lantern frontend currently embeds `DOG_CAMERA_URL` in an
`iframe`; it does not copy camera frames itself.

If the portal is opened from another computer or phone, `127.0.0.1` points to
that device, not the robot computer. Use the robot computer's LAN address:

```dotenv
DOG_CAMERA_URL=http://192.168.12.X:9877/
```

The robot computer must allow inbound TCP traffic on port `9877`.

If the portal is HTTPS, an HTTP camera URL may be blocked as mixed content. In
that case the viewer must also be exposed over HTTPS.

## Raw stream fallback

If the DimOS viewer cannot be embedded, configure a raw MJPEG/WebRTC stream
endpoint instead:

```dotenv
DOG_CAMERA_ENABLED=1
DOG_CAMERA_STREAM_URL=http://127.0.0.1:9877/<actual-stream-path>
```

Restart the API, then check:

```bash
curl -I http://127.0.0.1:8000/api/camera/stream
```

The frontend uses the same-origin `/api/camera/stream` proxy when
`DOG_CAMERA_STREAM_URL` is configured.

## Current diagnosis

The Lantern API configuration is enabled and points at `127.0.0.1:9877`.
The unresolved question is whether `9877` is:

1. an HTTP camera viewer,
2. a WebRTC signaling endpoint that needs a different browser path, or
3. a service that disallows iframe embedding.

The decisive next result is the output of:

```bash
curl -v --max-time 5 http://127.0.0.1:9877/
```

The phone/STT, orchestrator, and DimOS MCP command bridge are not required to
display video. Video only needs a reachable, browser-compatible DimOS viewer or
raw stream URL.

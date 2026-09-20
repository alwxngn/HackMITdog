"""FastAPI entry: WebSocket fan-out, ack, config, checkin, reset, report."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from bus import bus
from camera import router as camera_router
from demo import demo
from escalation import escalation
import notify
from report import build_morning_report
from schema import DEFAULT_CONFIG, DEFAULT_MAP_READY
from store import store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lantern.cloud")


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        await ws.send_json(store.snapshot())

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, msg: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


hub = Hub()


def _night_watch_enabled() -> bool:
    cfg = store.projection.get("config") or {}
    return bool(cfg.get("night_watch_enabled", True))


def _zone_class(zone_id: str | None) -> str | None:
    if not zone_id:
        return None
    for zone in store.projection.get("zones") or []:
        if zone.get("id") == zone_id:
            return zone.get("class")
    return None


def _is_night_watch_trigger(msg: dict[str, Any]) -> bool:
    t = msg.get("type")
    p = msg.get("payload") or {}

    if t == "zone_event":
        cls = p.get("zone_class") or p.get("class") or _zone_class(p.get("zone") or p.get("zone_id"))
        return cls == "exit"

    if t == "alert":
        if p.get("context") == "night_breach":
            return True
        cls = _zone_class((p.get("person_position") or {}).get("zone") or p.get("zone"))
        return cls == "exit" or int(p.get("level", 0)) >= 5

    return False


async def on_bus_message(msg: dict[str, Any]) -> None:
    if not _night_watch_enabled() and _is_night_watch_trigger(msg):
        logger.info("night_watch disabled: suppressing %s", msg.get("type"))
        return

    store.append(msg)
    try:
        if msg.get("type") == "alert":
            await escalation.on_alert(msg)
        if msg.get("type") == "caregiver_ack":
            escalation.cancel((msg.get("payload") or {}).get("alert_id", ""))
    except Exception:
        logger.exception("escalation handler failed on %s", msg.get("type"))
    await hub.broadcast(msg)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bus.subscribe(on_bus_message)
    # Seed default config into projection without duplicating if already set
    if not store.projection.get("zones"):
        store.projection["zones"] = list(DEFAULT_CONFIG["zones"])
        store.projection["config"] = dict(DEFAULT_CONFIG)
    yield
    escalation.cancel_all()


app = FastAPI(title="Lantern Cloud", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep the portal and mobile audio on one origin, including through the existing tunnel.
from voice_bridge import install_voice

install_voice(app)

app.include_router(camera_router)


@app.get("/")
async def root():
    return {
        "service": "lantern-cloud",
        "ws": "/ws",
        "docs": "/docs",
        "camera": "/api/camera/status",
        "hint": "Open the React portal (vite) or GET /api/report",
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await hub.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            # Portal can push ack/config/checkin over WS too
            t = data.get("type")
            if t in {"caregiver_ack", "config_update", "checkin", "map_scan_request"}:
                data.setdefault("ts", time.time())
                data.setdefault("source", "cloud")
                await bus.publish(data)
            elif t == "ping":
                await ws.send_json({"type": "pong", "ts": time.time(), "source": "cloud", "seq": 0, "payload": {}})
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        hub.disconnect(ws)


@app.get("/api/ack")
@app.post("/api/ack")
async def api_ack(
    request: Request,
    alert_id: str | None = Query(None),
    by: str = Query("jenny"),
    action: str = Query("im_coming"),
):
    if request.method == "POST":
        try:
            body = await request.json()
            alert_id = body.get("alert_id", alert_id)
            by = body.get("by", by)
            action = body.get("action", action)
        except Exception:
            pass
    if not alert_id:
        return JSONResponse({"ok": False, "error": "alert_id required"}, status_code=400)
    msg = {
        "type": "caregiver_ack",
        "ts": time.time(),
        "source": "cloud",
        "seq": 0,
        "payload": {"alert_id": alert_id, "by": by, "action": action},
    }
    await bus.publish(msg)
    # Friendly HTML for SMS link taps
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(
            f"<html><body style='font-family:system-ui;padding:2rem'>"
            f"<h1>Got it</h1><p>Alert <code>{alert_id}</code> acknowledged as {action}.</p>"
            f"</body></html>"
        )
    return {"ok": True, "alert_id": alert_id, "action": action}


@app.post("/api/onboarding/voice-clone")
async def onboarding_voice_clone(request: Request, name: str = Query("Lantern")):
    content_type = request.headers.get("content-type", "").split(";")[0]
    if content_type not in {"audio/webm", "audio/mp4", "audio/ogg", "audio/wav"}:
        return JSONResponse({"detail": "Unsupported recording format."}, status_code=415)
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > 10 * 1024 * 1024:
            return JSONResponse({"detail": "Recording too large. Keep the sample under a minute."}, status_code=413)
    if not audio:
        return JSONResponse({"detail": "Empty recording."}, status_code=400)

    from voice import providers

    voice_id = await providers.clone_voice(name.strip() or "Lantern", bytes(audio), content_type)
    payload = {"voice_id": voice_id, "consent_recorded_ts": time.time(), "attribution_name": name.strip() or "Lantern"}
    await bus.publish({
        "type": "config_update",
        "ts": time.time(),
        "source": "cloud",
        "seq": 0,
        "payload": {"voice": payload},
    })
    return {"voice_id": voice_id}


@app.post("/api/config")
async def api_config(body: dict[str, Any]):
    msg = {
        "type": "config_update",
        "ts": time.time(),
        "source": "cloud",
        "seq": 0,
        "payload": body,
    }
    await bus.publish(msg)
    return {"ok": True}


@app.post("/api/checkin")
async def api_checkin(body: dict[str, Any]):
    payload = {
        "checkin_id": body.get("checkin_id") or f"ck_{uuid.uuid4().hex[:8]}",
        "from_name": body.get("from_name", "Family"),
        "text": body.get("text", ""),
    }
    msg = {
        "type": "checkin",
        "ts": time.time(),
        "source": "cloud",
        "seq": 0,
        "payload": payload,
    }
    await bus.publish(msg)
    return {"ok": True, "payload": payload}


@app.post("/api/map-scan")
async def api_map_scan(body: dict[str, Any] | None = None):
    """Caregiver 'Scan home' — live mode asks E2; demo mode synthesizes map_ready."""
    import os

    body = body or {}
    request_id = body.get("request_id") or f"ms_{uuid.uuid4().hex[:8]}"
    mode = (body.get("mode") or os.getenv("MAP_SCAN_MODE", "demo")).strip().lower()

    req = {
        "type": "map_scan_request",
        "ts": time.time(),
        "source": "cloud",
        "seq": 0,
        "payload": {"request_id": request_id, "mode": "author_once"},
    }
    await bus.publish(req)

    if mode != "live":
        # Table fallback — same shape E2 should emit from DimOS
        map_ready_payload = dict(DEFAULT_MAP_READY)
        map_ready_payload["request_id"] = request_id
        ready = {
            "type": "map_ready",
            "ts": time.time(),
            "source": "mock",
            "seq": 0,
            "payload": map_ready_payload,
        }
        await bus.ingest(ready)
        return {"ok": True, "mode": "demo", "request_id": request_id, "map_ready": ready["payload"]}

    return {
        "ok": True,
        "mode": "live",
        "request_id": request_id,
        "hint": "Waiting for E2 map_ready on the bus (POST /api/ingest)",
    }


@app.get("/api/map-scan/status")
async def api_map_scan_status():
    return {
        "pending": store.projection.get("map_scan_pending"),
        "map_ready": store.projection.get("map_ready"),
        "mode": __import__("os").getenv("MAP_SCAN_MODE", "demo"),
    }


@app.post("/api/reset")
async def api_reset():
    escalation.cancel_all()
    store.reset()
    snap = store.snapshot()
    await hub.broadcast(snap)
    return {"ok": True, "snapshot": snap["payload"]}


async def _reset_live() -> None:
    """Clear live state between demo runs but keep the painted zones and patient setup."""
    escalation.cancel_all()
    store.reset(keep_setup=True)
    await hub.broadcast(store.snapshot())


@app.post("/api/demo/walk")
async def api_demo_walk():
    """Scripted walk: safe → warning → Don't-go → out of the house (no orchestrator needed)."""
    result = await demo.start(_reset_live)
    if not result["ok"]:
        return JSONResponse(result, status_code=409)
    return result


@app.post("/api/demo/stop")
async def api_demo_stop():
    await demo.stop(_reset_live)
    return {"ok": True}


@app.get("/api/contacts")
async def api_contacts():
    """Emergency contacts from the escalation ladder, with the numbers alerts already use."""
    rules = (store.projection.get("config") or {}).get("escalation") or []
    names: list[str] = []
    for rule in rules:
        name = rule.get("contact")
        if name and name not in names:
            names.append(name)
    roles = ["Primary contact", "Secondary contact"]
    return {
        "contacts": [
            {
                "name": name.capitalize(),
                "role": roles[i] if i < len(roles) else "Contact",
                "phone": notify._to_number(name),
            }
            for i, name in enumerate(names)
        ]
    }


@app.get("/api/report")
async def api_report():
    return build_morning_report()


@app.get("/api/snapshot")
async def api_snapshot():
    return store.snapshot()


@app.post("/api/ingest")
async def api_ingest(msg: dict[str, Any]):
    """Dev / bridge: push a bus message into the cloud (E4 can POST here)."""
    msg.setdefault("ts", time.time())
    msg.setdefault("source", msg.get("source", "mock"))
    await bus.ingest(msg)
    return {"ok": True}


@app.get("/api/outbound")
async def api_outbound():
    """E4 bridge fallback: drain cloud→bus publishes (ack/checkin/config)."""
    return {"messages": bus.drain_outbound_nowait()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

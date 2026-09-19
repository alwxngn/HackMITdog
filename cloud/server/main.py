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
from escalation import escalation
from report import build_morning_report
from schema import DEFAULT_CONFIG
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


async def on_bus_message(msg: dict[str, Any]) -> None:
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


@app.get("/")
async def root():
    return {
        "service": "lantern-cloud",
        "ws": "/ws",
        "docs": "/docs",
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
        ready = {
            "type": "map_ready",
            "ts": time.time(),
            "source": "mock",
            "seq": 0,
            "payload": {
                "request_id": request_id,
                "map_id": "demo_home_v1",
                "origin": {"x": 0.0, "y": 0.0},
                "width_m": 2.0,
                "height_m": 2.0,
                "outline": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]],
                "rooms": [
                    {
                        "id": "bedroom",
                        "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.2], [0.0, 1.2]],
                    },
                    {
                        "id": "hallway",
                        "polygon": [[1.0, 0.3], [1.8, 0.3], [1.8, 1.0], [1.0, 1.0]],
                    },
                    {
                        "id": "front_door",
                        "polygon": [[1.6, 0.0], [2.0, 0.0], [2.0, 0.5], [1.6, 0.5]],
                    },
                ],
            },
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

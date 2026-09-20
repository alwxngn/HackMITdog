"""HTTP/WebSocket hub so multi-process CLIs share one bus."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .core import Bus, get_bus

logger = logging.getLogger("lantern.bus.server")


class Hub:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus
        self.clients: set[WebSocket] = set()
        bus.subscribe(self._on_bus)

    async def _on_bus(self, msg: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)


def create_app(bus: Bus | None = None) -> FastAPI:
    bus = bus or get_bus()
    hub = Hub(bus)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        logger.info("bus hub up — log=%s", bus.log_path)
        yield

    app = FastAPI(title="Lantern Bus", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {
            "service": "lantern-bus",
            "publish": "POST /publish",
            "ws": "/ws",
            "log": str(bus.log_path),
        }

    @app.post("/publish")
    async def publish(msg: dict[str, Any]):
        msg.setdefault("ts", time.time())
        await bus.emit(msg)
        return {"ok": True, "seq": msg.get("seq")}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await hub.connect(ws)
        try:
            while True:
                data = await ws.receive_json()
                if data.get("type") == "ping":
                    await ws.send_json(
                        {
                            "type": "pong",
                            "ts": time.time(),
                            "source": "orchestrator",
                            "seq": 0,
                            "payload": {},
                        }
                    )
                    continue
                data.setdefault("ts", time.time())
                await bus.emit(data)
        except WebSocketDisconnect:
            hub.disconnect(ws)
        except Exception:
            hub.disconnect(ws)

    return app

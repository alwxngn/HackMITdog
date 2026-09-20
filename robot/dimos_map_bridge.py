"""Run DimOS room mapping when the Lantern portal requests a live scan.

This process runs beside DimOS and listens to the shared Lantern bus. It calls
the existing ``map_room`` MCP skill; the skill performs frontier exploration,
exports the PLY, and POSTs the frozen ``map_ready`` envelope to cloud.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any

import websockets

logger = logging.getLogger("lantern.robot.dimos_map_bridge")


class MapCommandBridge:
    def __init__(self, *, dimos_bin: str, cloud_base: str, artifact_dir: str, artifact_base: str) -> None:
        self.dimos_bin = dimos_bin
        self.cloud_base = cloud_base.rstrip("/")
        self.artifact_dir = artifact_dir
        self.artifact_base = artifact_base.rstrip("/")
        self._seen: set[str] = set()
        self._active_request_id: str | None = None

    async def handle(self, msg: dict[str, Any]) -> None:
        payload = msg.get("payload") or {}
        if msg.get("type") == "command":
            args = payload.get("args") or {}
            if (
                payload.get("action") == "stop"
                and args.get("operation") == "map_scan"
                and self._active_request_id
                and str(args.get("request_id") or "") == self._active_request_id
            ):
                logger.info("stopping DimOS map_room request=%s", self._active_request_id)
                try:
                    await self._call("end_exploration", {})
                except Exception:
                    logger.exception("could not stop DimOS map_room request=%s", self._active_request_id)
            return
        if msg.get("type") != "map_scan_request":
            return
        request_id = str(payload.get("request_id") or "")
        if not request_id or request_id in self._seen:
            return
        self._seen.add(request_id)
        map_id = f"home_{request_id}"
        args = {
            "room_id": "home",
            "duration_s": float(os.getenv("LANTERN_MAP_DURATION_S", "180")),
            "output_dir": self.artifact_dir,
            "request_id": request_id,
            "map_id": map_id,
            "cloud_ingest_url": f"{self.cloud_base}/api/ingest",
            "artifact_url": f"{self.artifact_base}/{map_id}.ply",
        }
        logger.info("starting DimOS map_room request=%s", request_id)
        self._active_request_id = request_id
        try:
            await self._call("map_room", args)
            logger.info("completed DimOS map_room request=%s", request_id)
        except Exception:
            logger.exception("map_room failed request=%s", request_id)
        finally:
            if self._active_request_id == request_id:
                self._active_request_id = None

    async def _call(self, tool: str, args: dict[str, Any]) -> None:
        process = await asyncio.create_subprocess_exec(
            self.dimos_bin,
            "mcp",
            "call",
            tool,
            "--timeout",
            str(int(float(os.getenv("LANTERN_MAP_MCP_TIMEOUT_S", "300")))),
            "--json-args",
            json.dumps(args),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode:
            detail = (stderr or stdout).decode(errors="replace").strip()
            raise RuntimeError(f"{tool} exited {process.returncode}: {detail[-500:]}")


async def run(bus_url: str, bridge: MapCommandBridge) -> None:
    while True:
        try:
            async with websockets.connect(bus_url) as ws:
                logger.info("connected to Lantern bus at %s", bus_url)
                async for raw in ws:
                    asyncio.create_task(bridge.handle(json.loads(raw)))
        except Exception as exc:
            logger.warning("bus connection failed: %s; retrying", exc)
            await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lantern map request → DimOS map_room")
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--cloud-base", default="http://127.0.0.1:8000")
    parser.add_argument("--artifact-dir", default="artifacts/maps")
    parser.add_argument("--artifact-base", default="http://127.0.0.1:8000/api/maps")
    parser.add_argument("--dimos-bin", default="dimos")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bridge = MapCommandBridge(
        dimos_bin=args.dimos_bin,
        cloud_base=args.cloud_base,
        artifact_dir=args.artifact_dir,
        artifact_base=args.artifact_base,
    )
    asyncio.run(run(args.bus_url, bridge))


if __name__ == "__main__":
    main()

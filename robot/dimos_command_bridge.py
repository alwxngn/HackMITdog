"""Translate frozen Lantern commands into direct DimOS MCP calls."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

import websockets

logger = logging.getLogger("lantern.robot.dimos_bridge")


class DimosCommandBridge:
    def __init__(self, *, dimos_bin: str = "dimos") -> None:
        self.dimos_bin = dimos_bin
        self._seen: set[str] = set()

    async def handle(self, msg: dict[str, Any], ws: Any) -> None:
        if msg.get("type") != "command":
            return
        payload = msg.get("payload") or {}
        command_id = str(payload.get("command_id") or "")
        if not command_id or command_id in self._seen:
            return
        self._seen.add(command_id)
        action = payload.get("action")
        args = payload.get("args") or {}
        await self._status(ws, command_id, "accepted", action)
        try:
            if action == "posture" and args.get("command_name"):
                await self._call("execute_sport_command", {"command_name": str(args["command_name"])})
            elif action == "stop":
                await self._call("stop", {})
            else:
                await self._status(ws, command_id, "failed", f"unsupported action: {action}")
                return
        except Exception as exc:
            await self._status(ws, command_id, "failed", str(exc))
            return
        await self._status(ws, command_id, "executing", action)

    async def _call(self, tool: str, args: dict[str, Any]) -> None:
        command = [self.dimos_bin, "mcp", "call", tool, "--json-args", json.dumps(args)]
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode:
            detail = (stderr or stdout).decode(errors="replace").strip()
            raise RuntimeError(f"{tool} exited {process.returncode}: {detail[-500:]}")

    @staticmethod
    async def _status(ws: Any, command_id: str, state: str, detail: Any) -> None:
        await ws.send(json.dumps({"type": "robot_status", "source": "robot", "payload": {"command_id": command_id, "state": state, "detail": detail}}))


async def run(bus_url: str, dimos_bin: str) -> None:
    bridge = DimosCommandBridge(dimos_bin=dimos_bin)
    while True:
        try:
            async with websockets.connect(bus_url) as ws:
                logger.info("connected to Lantern bus at %s", bus_url)
                async for raw in ws:
                    asyncio.create_task(bridge.handle(json.loads(raw), ws))
        except Exception as exc:
            logger.warning("bus connection failed: %s; retrying", exc)
            await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--dimos-bin", default="dimos")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(args.bus_url, args.dimos_bin))


if __name__ == "__main__":
    main()

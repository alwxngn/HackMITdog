"""Translate frozen Lantern bus commands into running DimOS MCP skills.

Run this beside ``dimos run hackmitdog.aegis-breadcrumb-agentic``. The bridge
does not import Unitree or DimOS; it uses the public ``dimos mcp call`` CLI so
the robot process remains the only hardware-facing component.
"""

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
            if action == "follow_person":
                await self._call("start_breadcrumb_recording", {"spacing_m": args.get("spacing_m", 0.5)})
                await self._call(
                    "follow_person",
                    {
                        "query": args.get("query", "the person nearby"),
                        "follow_distance_m": args.get("follow_distance_m", 1.5),
                    },
                )
            elif action == "guide_home":
                await self._call("stop_person_follow", {})
                await self._call("take_me_home", {})
            elif action == "stop":
                await self._call("stop_person_follow", {})
            else:
                await self._status(ws, command_id, "failed", f"unsupported action: {action}")
                return
        except Exception as exc:
            logger.exception("DimOS command failed: %s", action)
            await self._status(ws, command_id, "failed", str(exc))
            return
        await self._status(ws, command_id, "executing", action)

    async def _call(self, tool: str, args: dict[str, Any]) -> None:
        command = [self.dimos_bin, "mcp", "call", tool]
        if args:
            command.extend(["--json-args", json.dumps(args)])
        logger.info("calling DimOS tool %s", tool)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode:
            detail = (stderr or stdout).decode(errors="replace").strip()
            raise RuntimeError(f"{tool} exited {process.returncode}: {detail[-500:]}")

    @staticmethod
    async def _status(ws: Any, command_id: str, state: str, detail: Any) -> None:
        await ws.send(
            json.dumps(
                {
                    "type": "robot_status",
                    "source": "robot",
                    "payload": {
                        "command_id": command_id,
                        "state": state,
                        "detail": detail,
                    },
                }
            )
        )


async def run(bus_url: str, dimos_bin: str) -> None:
    bridge = DimosCommandBridge(dimos_bin=dimos_bin)
    while True:
        try:
            async with websockets.connect(bus_url) as ws:
                logger.info("connected to Lantern bus at %s", bus_url)
                async for raw in ws:
                    msg = json.loads(raw)
                    asyncio.create_task(bridge.handle(msg, ws))
        except Exception as exc:
            logger.warning("bus connection failed: %s; retrying", exc)
            await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lantern bus → DimOS command bridge")
    parser.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws")
    parser.add_argument("--dimos-bin", default="dimos")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run(args.bus_url, args.dimos_bin))


if __name__ == "__main__":
    main()

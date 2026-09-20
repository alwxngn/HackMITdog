"""Translate frozen Lantern commands into direct DimOS MCP calls."""
from __future__ import annotations
import argparse, asyncio, json, logging
from typing import Any
import websockets
logger = logging.getLogger("lantern.robot.dimos_bridge")
class DimosCommandBridge:
    def __init__(self, *, dimos_bin: str = "dimos") -> None: self.dimos_bin = dimos_bin; self._seen: set[str] = set()
    async def handle(self, msg: dict[str, Any], ws: Any) -> None:
        if msg.get("type") != "command": return
        p = msg.get("payload") or {}; cid = str(p.get("command_id") or "")
        if not cid or cid in self._seen: return
        self._seen.add(cid); action = p.get("action"); args = p.get("args") or {}; await self._status(ws, cid, "accepted", action)
        try:
            if action == "follow_person":
                await self._call("start_breadcrumb_recording", {"spacing_m": args.get("spacing_m", .5)}); await self._call("follow_person", {"query": args.get("query", "the person nearby"), "follow_distance_m": args.get("follow_distance_m", 1.5)})
            elif action == "guide_home": await self._call("stop_person_follow", {}); await self._call("take_me_home", {})
            elif action == "posture" and args.get("command_name"): await self._call("execute_sport_command", {"command_name": str(args["command_name"])})
            elif action == "stop": await self._call("stop_person_follow", {})
            else: await self._status(ws, cid, "failed", f"unsupported action: {action}"); return
        except Exception as exc: logger.exception("DimOS command failed: %s", action); await self._status(ws, cid, "failed", str(exc)); return
        await self._status(ws, cid, "executing", action)
    async def _call(self, tool: str, args: dict[str, Any]) -> None:
        cmd = [self.dimos_bin, "mcp", "call", tool];
        if args: cmd += ["--json-args", json.dumps(args)]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE); out, err = await proc.communicate()
        if proc.returncode: raise RuntimeError(f"{tool} exited {proc.returncode}: {(err or out).decode(errors='replace')[-500:]}")
    @staticmethod
    async def _status(ws: Any, cid: str, state: str, detail: Any) -> None: await ws.send(json.dumps({"type": "robot_status", "source": "robot", "payload": {"command_id": cid, "state": state, "detail": detail}}))
async def run(bus_url: str, dimos_bin: str) -> None:
    bridge = DimosCommandBridge(dimos_bin=dimos_bin)
    while True:
        try:
            async with websockets.connect(bus_url) as ws:
                logger.info("connected to Lantern bus at %s", bus_url)
                async for raw in ws: asyncio.create_task(bridge.handle(json.loads(raw), ws))
        except Exception as exc: logger.warning("bus connection failed: %s; retrying", exc); await asyncio.sleep(2)
def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--bus-url", default="ws://127.0.0.1:9000/ws"); p.add_argument("--dimos-bin", default="dimos"); a = p.parse_args(); logging.basicConfig(level=logging.INFO); asyncio.run(run(a.bus_url, a.dimos_bin))
if __name__ == "__main__": main()

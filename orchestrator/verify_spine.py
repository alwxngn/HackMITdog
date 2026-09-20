#!/usr/bin/env python3
"""Quick check: spine reaches ESCALATE + alert, then ack clears it."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx

CLOUD = "http://127.0.0.1:8000"


async def main() -> int:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "run_spine.py",
        "--scenario",
        "exit_seeking",
        "--hold",
        "15",
        "--hub-port",
        "0",
        cwd=str(Path(__file__).resolve().parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    states: list[str] = []
    alert_id: str | None = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        deadline = time.time() + 30
        while time.time() < deadline:
            await asyncio.sleep(0.4)
            snap = (await client.get(f"{CLOUD}/api/snapshot")).json()
            p = snap.get("payload", snap)
            st = (p.get("agent_state") or {}).get("state")
            if st and (not states or states[-1] != st):
                states.append(st)
                print("state", st)
            oa = p.get("open_alert")
            if oa and not alert_id:
                alert_id = oa["alert_id"]
                print("alert", alert_id, oa.get("headline"))
                await client.post(
                    f"{CLOUD}/api/ack",
                    params={"alert_id": alert_id, "by": "jenny", "action": "im_coming"},
                )
                await asyncio.sleep(0.8)
                snap2 = (await client.get(f"{CLOUD}/api/snapshot")).json()
                p2 = snap2.get("payload", snap2)
                if p2.get("open_alert"):
                    print("FAIL: alert still open after ack")
                    proc.kill()
                    return 1
                print("ack cleared open_alert")
                break
            if proc.returncode is not None:
                break
        out = (await proc.stdout.read()).decode()
        await proc.wait()
    print("--- spine log (state lines) ---")
    for line in out.splitlines():
        if "state " in line or "spine" in line:
            print(line)
    ok = "ESCALATE" in states and alert_id is not None
    print("states", states, "SPINE_OK" if ok else "SPINE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

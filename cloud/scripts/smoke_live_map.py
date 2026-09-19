#!/usr/bin/env python3
"""Smoke: MAP_SCAN_MODE=live path without a robot.

Proves E3's side of the E2 handoff:
  1. POST /api/map-scan?mode=live  → map_scan_request pending
  2. POST /api/ingest map_ready    → projection.map_ready set
  3. POST /api/ingest person_track → projection.person_track + trail
  4. Snapshot shows map bounds and pin coordinates

Usage (cloud API on :8000):
  cd cloud && source .venv/bin/activate
  python scripts/smoke_live_map.py
  python scripts/smoke_live_map.py --cloud http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "fixtures" / "sample_map_ready.json"


def main() -> int:
    p = argparse.ArgumentParser(description="Live map_ready + person_track smoke")
    p.add_argument("--cloud", default="http://127.0.0.1:8000")
    args = p.parse_args()
    base = args.cloud.rstrip("/")

    with httpx.Client(timeout=10.0) as client:
        # Fresh projection
        r = client.post(f"{base}/api/reset")
        r.raise_for_status()
        print("reset ok")

        # Live scan — do not synthesize map_ready
        r = client.post(f"{base}/api/map-scan", json={"mode": "live"})
        r.raise_for_status()
        data = r.json()
        if data.get("mode") != "live":
            print("FAIL: expected mode=live, got", data)
            return 1
        request_id = data.get("request_id")
        print("map-scan live pending", request_id)

        st = client.get(f"{base}/api/map-scan/status").json()
        if not st.get("pending"):
            print("FAIL: expected map_scan_pending after live scan", st)
            return 1
        if st.get("map_ready"):
            print("FAIL: map_ready should be empty until E2 posts", st)
            return 1

        # E2-shaped map_ready (curl equivalent)
        envelope = json.loads(SAMPLE.read_text())
        envelope["ts"] = time.time()
        envelope["payload"]["request_id"] = request_id
        r = client.post(f"{base}/api/ingest", json=envelope)
        r.raise_for_status()
        print("ingested map_ready", envelope["payload"]["map_id"])

        st = client.get(f"{base}/api/map-scan/status").json()
        mr = st.get("map_ready") or {}
        if mr.get("map_id") != "e2_home_v1":
            print("FAIL: map_ready missing after ingest", st)
            return 1
        if st.get("pending"):
            print("FAIL: pending should clear after map_ready", st)
            return 1
        print(
            "map_ready ok",
            f"{mr.get('width_m')}x{mr.get('height_m')} m",
            f"rooms={len(mr.get('rooms') or [])}",
        )

        # person_track in the same metre frame → Night Watch pin
        tracks = [
            (1.0, 1.0, "bedroom"),
            (2.4, 1.2, "hallway"),
            (3.5, 0.5, "front_door"),
        ]
        for i, (x, y, zone) in enumerate(tracks):
            msg = {
                "type": "person_track",
                "ts": time.time(),
                "source": "robot",
                "seq": 10 + i,
                "payload": {
                    "person_id": "p1",
                    "tracker": "overhead_cam",
                    "x": x,
                    "y": y,
                    "vx": 0.2,
                    "vy": 0.0,
                    "heading": 0.0,
                    "confidence": 0.9,
                    "posture": "standing",
                    "zone": zone,
                    "projected_zone": zone,
                    "ttz_s": None,
                    "lat": None,
                    "lon": None,
                },
            }
            r = client.post(f"{base}/api/ingest", json=msg)
            r.raise_for_status()

        snap = client.get(f"{base}/api/snapshot").json()
        payload = snap.get("payload", snap)
        pt = payload.get("person_track") or {}
        trail = payload.get("person_trail") or []
        if abs(float(pt.get("x", -1)) - 3.5) > 1e-6 or abs(float(pt.get("y", -1)) - 0.5) > 1e-6:
            print("FAIL: person_track pin wrong", pt)
            return 1
        if len(trail) < 3:
            print("FAIL: person_trail too short", trail)
            return 1
        print(
            "person_track ok",
            f"pin=({pt['x']},{pt['y']})",
            f"zone={pt.get('zone')}",
            f"trail={len(trail)}",
        )

        print("LIVE_MAP_SMOKE_OK")
        print("UI: open /onboarding (map should load) and /watch (pin near Don't-go).")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.ConnectError:
        print("FAIL: cloud API not reachable — start uvicorn on :8000 first", file=sys.stderr)
        raise SystemExit(2)

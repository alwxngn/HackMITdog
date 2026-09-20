"""Calibrated detector samples -> frozen Lantern person_track / zone_event.

Input samples are local JSONL, not new bus messages. No detector or motor control
is hidden here: callers must supply a stable actor ID and measured floor points.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
import time
from collections import deque
from pathlib import Path

LOG = logging.getLogger("lantern.tracking")


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite coordinate or timestamp")
    return value


def project(matrix, x, y):
    a, b, c = matrix
    divisor = c[0] * x + c[1] * y + c[2]
    if abs(divisor) < 1e-9:
        raise ValueError("point lies on calibration horizon")
    return (finite((a[0] * x + a[1] * y + a[2]) / divisor),
            finite((b[0] * x + b[1] * y + b[2]) / divisor))


def homography(pairs):
    """Fit four non-collinear source floor points to measured map metre points."""
    if len(pairs) != 4:
        raise ValueError("calibration needs exactly four source/map point pairs")
    rows = []
    for pair in pairs:
        x, y = map(finite, pair["source"])
        u, v = map(finite, pair["map"])
        rows.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y, u],
                     [0, 0, 0, x, y, 1, -v*x, -v*y, v]])
    for col in range(8):
        pivot = max(range(col, 8), key=lambda i: abs(rows[i][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        if abs(scale) < 1e-10:
            raise ValueError("degenerate calibration; use four distinct floor corners")
        rows[col] = [v / scale for v in rows[col]]
        for i in range(8):
            if i != col:
                scale = rows[i][col]
                rows[i] = [a - scale*b for a, b in zip(rows[i], rows[col])]
    h = [r[-1] for r in rows] + [1.0]
    return [h[:3], h[3:6], h[6:]]


def contains(point, polygon):
    """Boundary-inclusive ray casting; edges count as inside."""
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x-ax)*(by-ay) - (y-ay)*(bx-ax)
        if abs(cross) < 1e-9 and min(ax,bx)-1e-9 <= x <= max(ax,bx)+1e-9 and min(ay,by)-1e-9 <= y <= max(ay,by)+1e-9:
            return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def entry_time(point, velocity, polygon, horizon=3.0):
    """Earliest ray/edge intersection, including thin zones skipped by endpoints."""
    if contains(point, polygon):
        return 0.0
    x, y = point
    vx, vy = velocity
    times = []
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        ex, ey = bx-ax, by-ay
        det = vx*ey-vy*ex
        if abs(det) < 1e-10:
            continue
        t = ((ax-x)*ey-(ay-y)*ex)/det
        u = ((ax-x)*vy-(ay-y)*vx)/det
        if 0 <= t <= horizon and 0 <= u <= 1:
            times.append(t)
    return min(times) if times else None


class TrackingAdapter:
    def __init__(self, calibration, zones, *, actor_id, tracker="mock", confirmations=3):
        self.map_id = calibration["map_id"]
        self.frame = calibration["input_frame"]
        if not self.map_id or not self.frame or not actor_id:
            raise ValueError("map_id, input_frame and actor_id must be explicit")
        if tracker not in {"mock", "overhead_cam", "lidar_cluster", "onboard_fusion"}:
            raise ValueError("unknown tracker")
        self.matrix = homography(calibration["pairs"])
        self.actor_id, self.tracker = actor_id, tracker
        self.confirmations = max(1, confirmations)
        self.history = deque()
        self.last_ts = None
        self.members = set()
        self.pending = {}
        self.approaching = set()
        self.seq = 0
        self.set_zones(zones)

    def set_zones(self, zones):
        """Validate atomically. Empty list really clears zones; partial config doesn't."""
        if not isinstance(zones, list):
            raise ValueError("zones must be a list")
        checked = {}
        for zone in zones:
            zid = zone["id"]
            if not isinstance(zid, str) or not zid or zid in checked or zone["class"] not in {"safe", "watch", "exit"}:
                raise ValueError("invalid or duplicate zone")
            polygon = [list(map(finite, p)) for p in zone["polygon"]]
            if len(polygon) < 3 or any(len(p) != 2 for p in polygon):
                raise ValueError("zone needs at least three 2D vertices")
            area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon, polygon[1:]+polygon[:1]))
            if abs(area) < 1e-9:
                raise ValueError("degenerate polygon")
            checked[zid] = {**zone, "polygon": polygon}
        self.zones = checked
        # A map edit starts a new classification baseline; it is not a crossing.
        self.members.clear()
        self.pending.clear()
        self.approaching.clear()
        self.history.clear()

    def envelope(self, kind, payload, ts):
        self.seq += 1
        return {"type": kind, "payload": payload, "ts": ts,
                "source": "mock" if self.tracker == "mock" else "robot", "seq": self.seq}

    def process(self, sample, *, now=None):
        now = time.time() if now is None else now
        ts = finite(sample["ts"])
        confidence = finite(sample["confidence"])
        if sample["actor_id"] != self.actor_id:
            return []
        if sample["map_id"] != self.map_id or sample["frame"] != self.frame:
            raise ValueError("sample frame/map does not match calibration")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between zero and one")
        if not -0.1 <= now-ts <= 0.5 or (self.last_ts is not None and ts <= self.last_ts):
            LOG.warning("discarded stale, future or out-of-order actor sample")
            return []
        if confidence < 0.6:
            self.pending.clear()
            self.history.clear()
            LOG.warning("actor confidence below threshold; no position published")
            return []
        point = project(self.matrix, finite(sample["x"]), finite(sample["y"]))
        if self.last_ts is not None and ts-self.last_ts > 0.5:
            self.history.clear()
            self.pending.clear()
        self.last_ts = ts
        self.history.append((ts, point))
        while len(self.history) > 1 and ts-self.history[0][0] > 0.5:
            self.history.popleft()
        dt = ts-self.history[0][0]
        velocity = tuple((a-b)/dt for a,b in zip(point, self.history[0][1])) if dt >= 0.1 else (0.0, 0.0)
        events = []
        for zid, zone in self.zones.items():
            inside = contains(point, zone["polygon"])
            if inside == (zid in self.members):
                self.pending.pop(zid, None)
                continue
            count = self.pending.get(zid, 0) + 1
            self.pending[zid] = count
            if count >= self.confirmations:
                self.pending.pop(zid)
                (self.members.add if inside else self.members.discard)(zid)
                events.append({"person_id": self.actor_id, "zone_id": zid,
                               "zone_class": zone["class"], "event": "entered" if inside else "exited"})
        order = {"exit": 0, "watch": 1, "safe": 2}
        active = sorted(self.members, key=lambda z: (order[self.zones[z]["class"]], z))
        current = active[0] if active else None
        threats = []
        for zid, zone in self.zones.items():
            if zone["class"] != "exit":
                continue
            ttz = entry_time(point, velocity, zone["polygon"])
            # Do not let the raw track bypass entry debounce at a noisy boundary.
            if ttz is not None and (ttz > 0 or zid in self.members):
                threats.append((ttz, zid))
        threats.sort()
        predicted = threats[0][1] if threats else current
        ttz = threats[0][0] if threats else None
        upcoming = {z for t,z in threats if t > 0}
        for zid in sorted(upcoming-self.approaching):
            events.append({"person_id": self.actor_id, "zone_id": zid,
                           "zone_class": "exit", "event": "approaching"})
        self.approaching = upcoming
        posture = sample.get("posture", "unknown")
        if posture not in {"standing", "sitting", "lying", "unknown"}:
            raise ValueError("invalid posture")
        heading = math.atan2(velocity[1], velocity[0]) if math.hypot(*velocity) > 0.05 else None
        payload = dict(person_id=self.actor_id, tracker=self.tracker, x=point[0], y=point[1],
                       vx=velocity[0], vy=velocity[1], heading=heading, confidence=confidence,
                       posture=posture, zone=current, projected_zone=predicted, ttz_s=ttz)
        return [self.envelope("person_track", payload, ts)] + [self.envelope("zone_event", p, ts) for p in events]


async def run(args):
    calibration = json.loads(Path(args.calibration).read_text())
    config = json.loads(Path(args.zones).read_text())
    zones = config if isinstance(config, list) else config.get("payload", config)["zones"]
    adapter = TrackingAdapter(calibration, zones, actor_id=args.actor_id, tracker=args.tracker)
    async def consume(ws=None):
        stream = sys.stdin if args.input == "-" else open(args.input)
        try:
            for_line_ts = None
            replay_start = time.time()
            while True:
                line = await asyncio.to_thread(stream.readline)
                if not line:
                    break
                if not line.strip():
                    continue
                sample = json.loads(line)
                if args.replay:
                    original = finite(sample["ts"])
                    if for_line_ts is None:
                        for_line_ts = original
                    target = replay_start + original-for_line_ts
                    await asyncio.sleep(max(0, target-time.time()))
                    sample["ts"] = target
                for msg in adapter.process(sample):
                    print(json.dumps(msg, allow_nan=False), flush=True)
                    if ws is not None:
                        # Hub allocates a sequence shared with other robot publishers.
                        await ws.send(json.dumps({k:v for k,v in msg.items() if k != "seq"}))
        finally:
            if stream is not sys.stdin:
                stream.close()
    if not args.bus_url:
        await consume()
        return
    import websockets
    async with websockets.connect(args.bus_url) as ws:
        async def configs():
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "config_update" and "zones" in msg.get("payload", {}):
                    adapter.set_zones(msg["payload"]["zones"])
                    LOG.info("applied live zone update")
            raise ConnectionError("bus closed; tracking publication stopped")
        receiver = asyncio.create_task(configs())
        sender = asyncio.create_task(consume(ws))
        try:
            done, _ = await asyncio.wait([receiver, sender], return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            receiver.cancel()
            sender.cancel()
            await asyncio.gather(receiver, sender, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--zones", required=True, help="current config payload/envelope or zone list JSON")
    parser.add_argument("--actor-id", required=True, help="explicit upstream stable patient track ID")
    parser.add_argument("--tracker", choices=["mock", "overhead_cam", "lidar_cluster", "onboard_fusion"], default="mock")
    parser.add_argument("--input", default="-", help="local detector JSONL file or stdin")
    parser.add_argument("--replay", action="store_true", help="retime recorded samples; always labelled mock")
    parser.add_argument("--bus-url", help="optional ws://127.0.0.1:9000/ws; omitted = stdout only")
    args = parser.parse_args()
    if args.replay:
        args.tracker = "mock"
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

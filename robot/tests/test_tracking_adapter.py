import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracking_adapter import TrackingAdapter, contains, entry_time, homography, project

CAL = {"map_id": "test", "input_frame": "test_floor", "pairs": [
    {"source": [0, 0], "map": [0, 0]}, {"source": [10, 0], "map": [2, 0]},
    {"source": [10, 10], "map": [2, 2]}, {"source": [0, 10], "map": [0, 2]}]}
ZONES = [{"id": "front_door", "class": "exit", "polygon": [[1,0],[1.2,0],[1.2,1],[1,1]]},
         {"id": "bedroom", "class": "safe", "polygon": [[0,0],[2,0],[2,2],[0,2]]}]


def sample(t, x, **kw):
    return dict(ts=t, x=x, y=2, actor_id="p1", confidence=.9,
                map_id="test", frame="test_floor", **kw)


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.adapter = TrackingAdapter(CAL, ZONES, actor_id="p1")

    def feed(self, x, start=10):
        messages = []
        for i in range(3):
            t = start+i*.1
            messages.extend(self.adapter.process(sample(t, x), now=t))
        return messages

    def test_calibration_and_boundary(self):
        self.assertEqual(project(homography(CAL["pairs"]), 5, 5), (1,1))
        self.assertTrue(contains((1,.5), ZONES[0]["polygon"]))
        self.assertFalse(contains((.9,.5), ZONES[0]["polygon"]))
        with self.assertRaises(ValueError):
            homography([CAL["pairs"][0]]*4)

    def test_prediction_catches_thin_zone_between_endpoints(self):
        self.assertAlmostEqual(entry_time((.5,.5), (.5,0), ZONES[0]["polygon"]), 1)
        self.assertIsNone(entry_time((.5,.5), (-.5,0), ZONES[0]["polygon"]))

    def test_debounce_overlap_and_single_entry_exit(self):
        first = self.adapter.process(sample(10,5.5), now=10)
        self.assertIsNone(first[0]["payload"]["projected_zone"])
        msgs = self.feed(5.5, 10.1)
        events = [m["payload"] for m in msgs if m["type"] == "zone_event"]
        self.assertEqual(sum(e["zone_id"] == "front_door" and e["event"] == "entered" for e in events), 1)
        self.assertEqual(msgs[-1]["payload"]["zone"], "front_door")
        out = self.feed(8, 11)
        self.assertEqual(sum(m["type"] == "zone_event" and m["payload"]["event"] == "exited" for m in out), 1)
        self.assertEqual(out[-2]["payload"]["zone"], "bedroom")

    def test_stale_wrong_identity_frame_and_low_confidence(self):
        self.assertEqual(self.adapter.process(sample(1,5), now=10), [])
        s = sample(10,5)
        s["actor_id"] = "visitor"
        self.assertEqual(self.adapter.process(s, now=10), [])
        s["actor_id"], s["frame"] = "p1", "wrong"
        with self.assertRaises(ValueError):
            self.adapter.process(s, now=10)
        s = sample(10,5)
        s["confidence"] = .1
        self.assertEqual(self.adapter.process(s, now=10), [])

    def test_zone_edits_and_empty_clear(self):
        self.feed(5.5)
        changed = copy.deepcopy(ZONES)
        changed[0]["polygon"] = [[3,0],[4,0],[4,1],[3,1]]
        self.adapter.set_zones(changed)
        msgs = self.feed(5.5, 11)
        self.assertFalse(any(m["type"] == "zone_event" and m["payload"]["zone_id"] == "front_door" for m in msgs))
        self.adapter.set_zones([])
        self.assertIsNone(self.feed(5.5, 12)[-1]["payload"]["zone"])

    def test_gap_does_not_manufacture_velocity(self):
        self.feed(1)
        msg = self.adapter.process(sample(12,9), now=12)[0]
        self.assertEqual(msg["payload"]["vx"], 0)
        self.assertIsNone(msg["payload"]["heading"])


class AlertIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_geometry_drives_existing_machine_and_mock_robot(self):
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "bus"))
        sys.path.insert(0, str(root / "orchestrator"))
        from lantern_bus.core import Bus
        from lantern_orch.machine import StateMachine
        from mocks.mock_robot import MockRobot
        with tempfile.TemporaryDirectory() as directory:
            bus = Bus(Path(directory) / "events.jsonl")
            messages = []
            bus.subscribe(messages.append)
            machine = StateMachine(bus)
            await machine.start()
            # Subscribe the mock command consumer without its perpetual pose loop.
            robot = MockRobot(bus)
            bus.subscribe(robot._on_msg)
            await bus.publish("config_update", {"zones": ZONES}, source="cloud")
            adapter = TrackingAdapter(CAL, ZONES, actor_id="p1")
            for i in range(3):
                for msg in adapter.process(sample(10+i*.1,5.5), now=10+i*.1):
                    await bus.emit(msg)
            self.assertEqual(machine.state, "LEAD")
            self.assertTrue(any(m["type"] == "command" and m["payload"]["action"] == "lead_to" for m in messages))
            self.assertTrue(any(m["type"] == "robot_status" for m in messages))
            machine._lead_since = 0  # Advance timer without a real-time sleep.
            for msg in adapter.process(sample(10.4,5.5), now=10.4):
                await bus.emit(msg)
            self.assertEqual(machine.state, "ESCALATE")
            self.assertTrue(any(m["type"] == "alert" and m["payload"]["level"] == 2 for m in messages))


if __name__ == "__main__":
    unittest.main()

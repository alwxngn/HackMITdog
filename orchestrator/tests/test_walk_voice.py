import sys
import unittest

sys.path.insert(0, "bus")
sys.path.insert(0, "orchestrator")

from lantern_bus.core import Bus
from lantern_orch.machine import StateMachine


class WalkVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_walk_then_confirmed_home(self):
        bus = Bus(log_path="/tmp/lantern-walk-test.jsonl")
        messages = []
        bus.subscribe(lambda msg: messages.append(msg))
        machine = StateMachine(bus)
        await machine.start()

        await bus.publish(
            "transcript",
            {"text": "take me for a walk", "is_final": True, "speaker": "patient"},
            source="voice",
        )
        self.assertEqual(machine.state, "WALK")
        self.assertEqual(messages[-1]["type"], "say")
        self.assertTrue(any(m["type"] == "command" and m["payload"]["action"] == "follow_person" for m in messages))

        await bus.publish("pose", {"x": 0.6, "y": 0.5}, source="robot")
        await bus.publish("pose", {"x": 1.2, "y": 0.5}, source="robot")
        await bus.publish(
            "transcript",
            {"text": "take me home", "is_final": True, "speaker": "patient"},
            source="voice",
        )
        self.assertEqual(machine.state, "CONFIRM_HOME")

        await bus.publish(
            "transcript",
            {"text": "yes", "is_final": True, "speaker": "patient"},
            source="voice",
        )
        self.assertEqual(machine.state, "GUIDE_HOME")
        actions = [m["payload"]["action"] for m in messages if m["type"] == "command"]
        self.assertEqual(actions[-2:], ["stop", "guide_home"])


if __name__ == "__main__":
    unittest.main()

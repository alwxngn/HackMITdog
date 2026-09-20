import asyncio
import unittest

from dimos_command_bridge import DimosCommandBridge


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_walk_starts_breadcrumbs_before_follow(self):
        bridge = DimosCommandBridge(dimos_bin="unused")
        calls = []

        async def fake_call(tool, args):
            calls.append((tool, args))

        bridge._call = fake_call
        await bridge.handle(
            {"type": "command", "payload": {"command_id": "cmd-1", "action": "follow_person", "args": {}}},
            FakeWebSocket(),
        )
        self.assertEqual([tool for tool, _ in calls], ["start_breadcrumb_recording", "follow_person"])

    async def test_home_stops_follow_before_return(self):
        bridge = DimosCommandBridge(dimos_bin="unused")
        calls = []

        async def fake_call(tool, args):
            calls.append(tool)

        bridge._call = fake_call
        await bridge.handle(
            {"type": "command", "payload": {"command_id": "cmd-2", "action": "guide_home", "args": {}}},
            FakeWebSocket(),
        )
        self.assertEqual(calls, ["stop_person_follow", "take_me_home"])


if __name__ == "__main__":
    unittest.main()

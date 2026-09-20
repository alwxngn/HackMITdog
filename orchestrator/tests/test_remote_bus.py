import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bus"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lantern_orch.remote_bus import RemoteBus


class RemoteBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_dispatches_locally_and_sends_to_hub(self):
        bus = RemoteBus("ws://127.0.0.1:9000/ws")
        bus._ready.set()
        bus._ws = AsyncMock()
        received = []
        bus.subscribe(received.append)

        message = await bus.publish("command", {"action": "stop"}, source="orchestrator")

        self.assertEqual(received, [message])
        bus._ws.send.assert_awaited_once_with(json.dumps(message))

    async def test_hub_echo_of_our_message_is_deduplicated(self):
        bus = RemoteBus("ws://127.0.0.1:9000/ws")
        bus._ready.set()
        bus._ws = AsyncMock()
        received = []
        bus.subscribe(received.append)
        message = await bus.publish("command", {"action": "stop"})

        await bus._dispatch_if_new(message)
        self.assertEqual(received, [message])


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from dimos_map_bridge import MapCommandBridge


class MapBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_request_calls_map_room_with_cloud_and_artifact_urls(self):
        bridge = MapCommandBridge(
            dimos_bin="unused",
            cloud_base="http://cloud:8000",
            artifact_dir="artifacts/maps",
            artifact_base="http://cloud:8000/api/maps",
        )
        calls = []

        async def fake_call(tool, args):
            calls.append((tool, args))

        bridge._call = fake_call
        await bridge.handle({
            "type": "map_scan_request",
            "payload": {"request_id": "ms_123", "mode": "author_once"},
        })
        self.assertEqual(calls[0][0], "map_room")
        self.assertEqual(calls[0][1]["request_id"], "ms_123")
        self.assertEqual(calls[0][1]["cloud_ingest_url"], "http://cloud:8000/api/ingest")
        self.assertEqual(calls[0][1]["artifact_url"], "http://cloud:8000/api/maps/home_ms_123.ply")


if __name__ == "__main__":
    unittest.main()

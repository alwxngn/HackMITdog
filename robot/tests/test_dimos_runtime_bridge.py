import asyncio
import json
import unittest

from dimos_runtime_bridge import RuntimeBridge, _raise_for_dimos_failure


class DimosResultParsingTests(unittest.TestCase):
    def test_rejects_direct_skill_failure(self):
        with self.assertRaisesRegex(RuntimeError, "location unavailable"):
            _raise_for_dimos_failure(
                '{"success": false, "error_code": "NAV_FAILED", '
                '"message": "location unavailable"}'
            )

    def test_rejects_failure_inside_mcp_text_content(self):
        output = {
            "content": [
                {
                    "type": "text",
                    "text": '{"success": false, "message": "planner rejected route"}',
                }
            ]
        }
        with self.assertRaisesRegex(RuntimeError, "planner rejected route"):
            _raise_for_dimos_failure(json.dumps(output))

    def test_accepts_success_and_unstructured_cli_output(self):
        _raise_for_dimos_failure('{"success": true, "message": "arrived"}')
        _raise_for_dimos_failure("tool completed")


class FakeDimos:
    def __init__(self):
        self.calls = []
        self.navigation_release = asyncio.Event()
        self.block_navigation = False

    async def call(self, tool, args, *, timeout_s=120):
        self.calls.append((tool, args, timeout_s))
        if tool == "go_to_named_location" and self.block_navigation:
            await self.navigation_release.wait()
        return "ok"


class RuntimeBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dimos = FakeDimos()
        self.published = []

        async def publish(msg):
            self.published.append(msg)

        self.bridge = RuntimeBridge(dimos=self.dimos, publish=publish, motion_enabled=True)

    async def sync_zones(self):
        await self.bridge.handle(
            {
                "type": "config_update",
                "payload": {
                    "zones": [
                        {
                            "id": "bedroom",
                            "class": "safe",
                            "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]],
                        },
                        {
                            "id": "front_door",
                            "class": "exit",
                            "polygon": [[1.6, 0], [2, 0], [2, 0.5], [1.6, 0.5]],
                        },
                    ]
                },
            }
        )

    async def test_config_syncs_only_exit_polygons_to_dimos(self):
        await self.sync_zones()
        self.assertEqual(
            self.dimos.calls,
            [
                (
                    "create_danger_zone",
                    {
                        "name": "front_door",
                        "vertices": [[1.6, 0.0], [2.0, 0.0], [2.0, 0.5], [1.6, 0.5]],
                    },
                    30,
                )
            ],
        )

    async def test_changed_exit_polygon_is_deleted_then_recreated(self):
        await self.sync_zones()
        self.dimos.calls.clear()
        await self.bridge.handle(
            {
                "type": "config_update",
                "payload": {
                    "zones": [
                        {
                            "id": "front_door",
                            "class": "exit",
                            "polygon": [[1.5, 0], [2, 0], [2, 0.6], [1.5, 0.6]],
                        }
                    ]
                },
            }
        )
        self.assertEqual(self.dimos.calls[0][0], "delete_danger_zone")
        self.assertEqual(self.dimos.calls[1][0], "create_danger_zone")

    async def test_lead_to_safe_named_location_publishes_lifecycle(self):
        await self.sync_zones()
        self.dimos.calls.clear()
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {
                    "command_id": "cmd_1",
                    "action": "lead_to",
                    "args": {"zone_id": "bedroom", "speed_max": 0.3, "standoff_m": 1.5},
                },
            }
        )
        await self.bridge.wait_idle()
        self.assertEqual(self.dimos.calls[0][0], "go_to_named_location")
        self.assertEqual(self.dimos.calls[0][1], {"name": "bedroom"})
        self.assertEqual(
            [msg["payload"]["state"] for msg in self.published],
            ["accepted", "executing", "done"],
        )

    async def test_lead_to_exit_zone_is_rejected(self):
        await self.sync_zones()
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {
                    "command_id": "cmd_bad",
                    "action": "lead_to",
                    "args": {"zone_id": "front_door", "speed_max": 0.3},
                },
            }
        )
        await self.bridge.wait_idle()
        self.assertEqual(self.published[-1]["payload"]["state"], "failed")
        self.assertIn("not a safe zone", self.published[-1]["payload"]["detail"])

    async def test_motion_is_disabled_by_default(self):
        async def publish(msg):
            self.published.append(msg)

        bridge = RuntimeBridge(dimos=self.dimos, publish=publish)
        bridge.zones["bedroom"] = {"id": "bedroom", "class": "safe", "polygon": [[0, 0], [1, 0], [1, 1]]}
        await bridge.handle(
            {
                "type": "command",
                "payload": {
                    "command_id": "cmd_disabled",
                    "action": "lead_to",
                    "args": {"zone_id": "bedroom", "speed_max": 0.3},
                },
            }
        )
        await bridge.wait_idle()
        self.assertEqual(self.published[-1]["payload"]["state"], "failed")
        self.assertIn("motion disabled", self.published[-1]["payload"]["detail"])

    async def test_stop_cancels_active_navigation_status(self):
        await self.sync_zones()
        self.published.clear()
        self.dimos.calls.clear()
        self.dimos.block_navigation = True
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {
                    "command_id": "cmd_move",
                    "action": "lead_to",
                    "args": {"zone_id": "bedroom", "speed_max": 0.3},
                },
            }
        )
        await asyncio.sleep(0)
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {"command_id": "cmd_stop", "action": "stop", "args": {}},
            }
        )
        self.dimos.navigation_release.set()
        await self.bridge.wait_idle()
        calls = [tool for tool, _args, _timeout in self.dimos.calls]
        self.assertIn("stop_location_navigation", calls)
        states = [(m["payload"]["command_id"], m["payload"]["state"]) for m in self.published]
        self.assertIn(("cmd_move", "failed"), states)
        self.assertIn(("cmd_stop", "done"), states)

    async def test_yield_command_marks_active_navigation_yielded(self):
        await self.sync_zones()
        self.published.clear()
        self.dimos.calls.clear()
        self.dimos.block_navigation = True
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {
                    "command_id": "cmd_move",
                    "action": "lead_to",
                    "args": {"zone_id": "bedroom", "speed_max": 0.3},
                },
            }
        )
        await asyncio.sleep(0)
        await self.bridge.handle(
            {
                "type": "command",
                "payload": {"command_id": "cmd_yield", "action": "yield", "args": {}},
            }
        )
        self.dimos.navigation_release.set()
        await self.bridge.wait_idle()
        states = [(m["payload"]["command_id"], m["payload"]["state"]) for m in self.published]
        self.assertIn(("cmd_move", "yielded"), states)
        self.assertIn(("cmd_yield", "done"), states)


if __name__ == "__main__":
    unittest.main()

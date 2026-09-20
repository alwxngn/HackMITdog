"""Phone transcript -> real cloud adapter -> HTTP hub -> orchestrator -> mock robot."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cloud' / 'server'))
import voice_bridge
for folder in ('bus', 'orchestrator'):
    sys.path.insert(0, str(ROOT / folder))
from lantern_bus.core import Bus
from lantern_bus.server import create_app
from lantern_orch.machine import StateMachine
from mocks.mock_robot import MockRobot
from voice.app import Session, Profile, PhoneEvent, handle_phone


class RobotPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_walk_home_confirmation_and_stop_with_mock_robot(self):
        with tempfile.TemporaryDirectory() as directory:
            hub_bus = Bus(log_path=Path(directory) / 'events.jsonl')
            events = []
            hub_bus.subscribe(lambda event: events.append(event))
            machine = StateMachine(hub_bus)
            await machine.start()
            robot = MockRobot(hub_bus)
            # Exercise the real mock's command consumer without a background pose loop.
            hub_bus.subscribe(robot._on_msg)
            await hub_bus.publish('person_track', {'person_id':'p1', 'x':3, 'y':1, 'tracker':'mock', 'zone':'living_room'}, source='mock')
            app = create_app(hub_bus)
            client_type = httpx.AsyncClient
            forwarded = []
            def client(**kwargs):
                return client_type(transport=httpx.ASGITransport(app=app), **kwargs)
            async def echo(event):
                if event['type'] == 'transcript':
                    forwarded.append(event)
                    await voice_bridge.bus.ingest(event)
            hub_bus.subscribe(echo)
            session = Session('mock-phone', Profile(), ready=True, phone=AsyncMock(),
                              event_sink=voice_bridge.forward_voice_event)
            with patch.object(voice_bridge.bus, '_orch_url', 'http://mock-hub'), \
                 patch.object(voice_bridge.bus, '_handlers', []), \
                 patch('httpx.AsyncClient', side_effect=client):
                async def speak(text, turn):
                    await handle_phone(session, PhoneEvent(type='transcript', text=text, turn_id=turn))
                await speak("let's go on a walk", 'walk')
                self.assertEqual(machine.state, 'WALK')
                self.assertEqual(robot.mode, 'walking')
                self.assertEqual(len(forwarded), 1)
                self.assertTrue(any(e['type'] == 'robot_status' and e['payload']['state'] == 'executing' for e in events))
                await hub_bus.publish('pose', {'x':0.6, 'y':0.5}, source='mock')
                await hub_bus.publish('pose', {'x':2.0, 'y':0.5}, source='mock')
                await speak('take me home', 'home')
                self.assertEqual(machine.state, 'CONFIRM_HOME')
                self.assertFalse(any(e['type'] == 'command' and e['payload']['action'] == 'guide_home' for e in events))
                await speak('yes', 'confirm')
                self.assertEqual(machine.state, 'GUIDE_HOME')
                self.assertTrue(any(e['type'] == 'command' and e['payload']['action'] == 'guide_home' for e in events))
                await speak('stop', 'stop')
                self.assertEqual(machine.state, 'IDLE')
                self.assertEqual(robot.mode, 'standing')
                self.assertEqual(len(forwarded), 4)
                await speak("let's go on a walk", 'walk2')
                await speak('take me home', 'home2')
                self.assertEqual(machine.state, 'CONFIRM_HOME')
                await speak('stop', 'stop2')
                self.assertEqual(machine.state, 'IDLE')
                self.assertEqual(robot.mode, 'standing')

    async def test_http_rejection_is_not_silently_accepted(self):
        client_type = httpx.AsyncClient
        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(lambda request: httpx.Response(503)), **kwargs)
        with patch.object(voice_bridge.bus, '_orch_url', 'http://mock-hub'), patch('httpx.AsyncClient', side_effect=client):
            with self.assertRaisesRegex(RuntimeError, 'Could not deliver'):
                await voice_bridge.bus._forward_orch({'type':'transcript'}, required=True)


if __name__ == '__main__':
    unittest.main()

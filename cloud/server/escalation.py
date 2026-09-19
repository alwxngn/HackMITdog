"""Escalation ladder timers. Cancelled by caregiver_ack."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import notify
from bus import bus
from store import store

logger = logging.getLogger("lantern.escalation")

# Demo-friendly defaults; production values from blueprint §5
L3_AFTER_S = float(__import__("os").getenv("LADDER_L3_AFTER_S", "60"))
L4_AFTER_S = float(__import__("os").getenv("LADDER_L4_AFTER_S", "120"))


class EscalationManager:
    def __init__(self) -> None:
        self._tasks: dict[str, list[asyncio.Task]] = {}
        import os

        self.ack_base_url = os.getenv("ACK_BASE_URL", "http://127.0.0.1:8000")
        # Fast demo mode: compress 60/120s when LANTERN_FAST_LADDER=1
        if os.getenv("LANTERN_FAST_LADDER") == "1":
            global L3_AFTER_S, L4_AFTER_S
            L3_AFTER_S = 8.0
            L4_AFTER_S = 16.0

    def cancel(self, alert_id: str) -> None:
        for task in self._tasks.pop(alert_id, []):
            task.cancel()
        logger.info("ladder cancelled for %s", alert_id)

    def cancel_all(self) -> None:
        for alert_id in list(self._tasks):
            self.cancel(alert_id)

    async def on_alert(self, msg: dict[str, Any]) -> None:
        p = msg.get("payload") or {}
        alert_id = p.get("alert_id")
        if not alert_id:
            return
        level = int(p.get("level", 2))
        headline = p.get("headline", "Lantern alert")
        detail = p.get("detail", "")
        channels = p.get("channels") or ["sms"]
        context = p.get("context")

        self.cancel(alert_id)
        tasks: list[asyncio.Task] = []

        # Level 5 / dont_go breach: immediate voice urgency
        if level >= 5 or context == "night_breach" and p.get("live_tracking"):
            await self._fire_sms(headline, detail, alert_id)
            await self._fire_voice(headline, "jenny")
            self._tasks[alert_id] = tasks
            return

        if "sms" in channels or level >= 2:
            await self._fire_sms(headline, detail, alert_id)

        if level >= 3 or "voice_call" in channels:
            # Already at voice — fire now
            if level >= 3:
                await self._fire_voice(headline, "jenny")
            else:
                tasks.append(asyncio.create_task(self._delayed_voice(alert_id, headline, L3_AFTER_S)))
        else:
            tasks.append(asyncio.create_task(self._delayed_voice(alert_id, headline, L3_AFTER_S)))

        tasks.append(asyncio.create_task(self._delayed_secondary(alert_id, headline, L4_AFTER_S)))
        self._tasks[alert_id] = tasks

    async def _delayed_voice(self, alert_id: str, headline: str, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            if store.projection.get("open_alert", {}).get("alert_id") != alert_id:
                return
            await self._fire_voice(headline, "jenny")
            # Bump open alert channels for timeline visibility
            await bus.ingest(
                {
                    "type": "alert",
                    "ts": time.time(),
                    "source": "cloud",
                    "seq": 0,
                    "payload": {
                        **(store.projection.get("open_alert") or {}),
                        "alert_id": alert_id,
                        "level": 3,
                        "channels": ["sms", "voice_call"],
                        "headline": headline,
                    },
                }
            )
        except asyncio.CancelledError:
            return

    async def _delayed_secondary(self, alert_id: str, headline: str, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            if store.projection.get("open_alert", {}).get("alert_id") != alert_id:
                return
            await self._fire_voice(f"SECONDARY: {headline}", "mark")
            await bus.ingest(
                {
                    "type": "alert",
                    "ts": time.time(),
                    "source": "cloud",
                    "seq": 0,
                    "payload": {
                        **(store.projection.get("open_alert") or {}),
                        "alert_id": alert_id,
                        "level": 4,
                        "channels": ["voice_call"],
                        "headline": f"Secondary: {headline}",
                    },
                }
            )
        except asyncio.CancelledError:
            return

    async def _fire_sms(self, headline: str, detail: str, alert_id: str) -> None:
        notify.send_sms(headline, detail, alert_id, self.ack_base_url)

    async def _fire_voice(self, headline: str, contact: str) -> None:
        notify.place_voice_call(headline, contact)


escalation = EscalationManager()

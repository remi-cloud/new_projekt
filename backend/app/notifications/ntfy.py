"""Mobile push via ntfy.sh — no account required."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.notifications.alert_engine import AlertEvent
from app.notifications.ntfy_rate import send_ntfy_batch

logger = logging.getLogger(__name__)


async def send_ntfy_alerts(events: list[AlertEvent], topic: str) -> int:
    if not settings.notifications_enabled or not events or not topic:
        return 0

    messages: list[tuple[bytes, dict[str, str]]] = []
    for event in events:
        title = f"{event.action.upper()}: {event.symbol}"
        body = (
            f"{event.name}\n"
            f"Sygnał: {event.action.upper()} ({event.confidence:.0f}%)\n"
            f"Cena: {event.price}\n"
            f"{event.reason}\n"
            f"Handel manualny — sprawdź aplikację."
        )
        messages.append(
            (
                body.encode("utf-8"),
                {
                    "Title": title.encode("ascii", errors="replace").decode("ascii"),
                    "Priority": "high",
                    "Tags": "chart_with_upwards_trend,moneybag",
                },
            )
        )

    async with httpx.AsyncClient(timeout=15) as client:
        return await send_ntfy_batch(client, topic=topic, messages=messages)


async def send_ntfy_test(topic: str) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        from app.notifications.ntfy_rate import post_ntfy

        ok, _ = await post_ntfy(
            client,
            topic=topic,
            body="Test alertu Cyclical Academy - powiadomienia dzialaja!".encode("utf-8"),
            headers={"Title": "Cyclical Academy OK", "Priority": "default", "Tags": "white_check_mark"},
        )
        return ok

"""Mobile push via ntfy.sh — no account required."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.notifications.alert_engine import AlertEvent

logger = logging.getLogger(__name__)


async def send_ntfy_alerts(events: list[AlertEvent], topic: str) -> int:
    if not settings.notifications_enabled or not events or not topic:
        return 0

    sent = 0
    async with httpx.AsyncClient(timeout=15) as client:
        for event in events:
            title = f"{event.action.upper()}: {event.symbol}"
            body = (
                f"{event.name}\n"
                f"Sygnał: {event.action.upper()} ({event.confidence:.0f}%)\n"
                f"Cena: {event.price}\n"
                f"{event.reason}\n"
                f"Handel manualny — sprawdź aplikację."
            )
            try:
                resp = await client.post(
                    f"https://ntfy.sh/{topic}",
                    content=body.encode("utf-8"),
                    headers={
                        "Title": title.encode("ascii", errors="replace").decode("ascii"),
                        "Priority": "high",
                        "Tags": "chart_with_upwards_trend,moneybag",
                    },
                )
                if resp.is_success:
                    sent += 1
                else:
                    logger.warning("ntfy failed %s: %s", resp.status_code, resp.text[:120])
            except Exception as exc:
                logger.warning("ntfy error: %s", exc)
    return sent


async def send_ntfy_test(topic: str) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"https://ntfy.sh/{topic}",
                content="Test alertu Cyclical Trader - powiadomienia dzialaja!".encode("utf-8"),
                headers={"Title": "Cyclical Trader OK", "Priority": "default", "Tags": "white_check_mark"},
            )
            return resp.is_success
        except Exception as exc:
            logger.warning("ntfy test error: %s", exc)
            return False

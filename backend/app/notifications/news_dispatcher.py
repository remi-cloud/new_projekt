"""Dispatch macro news alerts to push + ntfy."""

from __future__ import annotations

import json
import logging

import httpx
from pywebpush import WebPushException, webpush

from app.config import settings
from app.db.database import get_alert_settings, get_push_subscriptions, log_notification, remove_push_subscription
from app.news.news_alerts import NewsAlertEvent
from app.notifications.push import vapid_configured
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)


async def send_push_news(events: list[NewsAlertEvent]) -> int:
    if not settings.notifications_enabled or not vapid_configured() or not events:
        return 0
    subs = await get_push_subscriptions()
    if not subs:
        return 0
    sent = 0
    for event in events:
        title = f"📰 Makro · {event.category.upper()}"
        body = f"{event.title[:120]}\n{event.source} · {event.reason}"
        payload = json.dumps({"title": title, "body": body, "url": event.url or ""})
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": settings.vapid_subject},
                )
                sent += 1
            except WebPushException as exc:
                status = exc.response.status_code if exc.response else None
                if status in (404, 410):
                    await remove_push_subscription(sub["endpoint"])
            except Exception as exc:
                logger.warning("News push error: %s", exc)
    return sent


async def send_ntfy_news(events: list[NewsAlertEvent], topic: str) -> int:
    if not settings.notifications_enabled or not events or not topic:
        return 0
    messages: list[tuple[bytes, dict[str, str]]] = []
    for event in events:
        title = f"MAKRO {event.category.upper()}"
        body = f"{event.title}\n{event.source} · {event.reason}"
        messages.append(
            (
                body.encode("utf-8"),
                {
                    "Title": title.encode("ascii", errors="replace").decode("ascii"),
                    "Priority": "high",
                    "Tags": "newspaper,warning",
                },
            )
        )
    from app.notifications.ntfy_rate import send_ntfy_batch

    async with httpx.AsyncClient(timeout=15) as client:
        return await send_ntfy_batch(client, topic=topic, messages=messages)


async def dispatch_news_alerts(events: list[NewsAlertEvent]) -> dict[str, int]:
    if not events:
        return {"push": 0, "ntfy": 0}

    alert_settings = await get_alert_settings()
    if not alert_settings.get("alert_on_macro_news", True):
        return {"push": 0, "ntfy": 0}

    push_sent = await send_push_news(events) if alert_settings.get("push_enabled") else 0
    ntfy_sent = 0
    if alert_settings.get("ntfy_enabled") and alert_settings.get("ntfy_topic"):
        ntfy_sent = await send_ntfy_news(events, alert_settings["ntfy_topic"])

    for event in events:
        await log_notification("news_push", event.category, event.title[:200], push_sent > 0)

    await broadcaster.publish(
        "macro_news",
        [
            {
                "id": e.news_id,
                "title": e.title,
                "category": e.category,
                "impact": e.impact,
                "source": e.source,
                "url": e.url,
                "reason": e.reason,
            }
            for e in events
        ],
    )

    logger.info("News alerts: %d events, push=%d ntfy=%d", len(events), push_sent, ntfy_sent)
    return {"push": push_sent, "ntfy": ntfy_sent}

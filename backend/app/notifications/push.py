"""Web Push notifications (VAPID)."""

from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush

from app.config import settings
from app.db.database import get_push_subscriptions, remove_push_subscription
from app.notifications.alert_engine import AlertEvent

logger = logging.getLogger(__name__)


def vapid_configured() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def get_vapid_public_key() -> str:
    return settings.vapid_public_key


async def send_push_alerts(events: list[AlertEvent]) -> int:
    if not settings.notifications_enabled or not vapid_configured() or not events:
        return 0

    subs = await get_push_subscriptions()
    if not subs:
        return 0

    sent = 0
    for event in events:
        title = f"Cyclical Trader — {event.action.upper()}"
        body = f"{event.name} ({event.symbol}): {event.reason} @ {event.price}"
        payload = json.dumps({"title": title, "body": body, "symbol": event.symbol})

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
                logger.warning("Push failed (%s): %s", status, exc)
                if status in (404, 410):
                    await remove_push_subscription(sub["endpoint"])
            except Exception as exc:
                logger.warning("Push error: %s", exc)
    return sent

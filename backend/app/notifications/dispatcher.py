"""Dispatch alerts to push + SMS + ntfy channels."""

from __future__ import annotations

import logging

from app.db.database import get_alert_settings, log_notification
from app.notifications.alert_engine import AlertEvent
from app.notifications.ntfy import send_ntfy_alerts
from app.notifications.push import send_push_alerts
from app.notifications.sms import send_sms_alerts
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)


async def dispatch_alerts(events: list[AlertEvent]) -> dict[str, int]:
    if not events:
        return {"push": 0, "sms": 0, "ntfy": 0}

    alert_settings = await get_alert_settings()
    push_sent = await send_push_alerts(events) if alert_settings.get("push_enabled") else 0
    sms_sent = await send_sms_alerts(events) if alert_settings.get("sms_enabled") else 0
    ntfy_sent = 0
    if alert_settings.get("ntfy_enabled") and alert_settings.get("ntfy_topic"):
        ntfy_sent = await send_ntfy_alerts(events, alert_settings["ntfy_topic"])

    for event in events:
        await log_notification("push", event.symbol, event.reason, push_sent > 0)
        await log_notification("sms", event.symbol, event.reason, sms_sent > 0)
        await log_notification("ntfy", event.symbol, event.reason, ntfy_sent > 0)

    await broadcaster.publish(
        "alerts",
        [
            {
                "symbol": e.symbol,
                "name": e.name,
                "action": e.action,
                "confidence": e.confidence,
                "price": e.price,
                "reason": e.reason,
            }
            for e in events
        ],
    )

    logger.info(
        "Alerts dispatched: %d events, push=%d sms=%d ntfy=%d",
        len(events), push_sent, sms_sent, ntfy_sent,
    )
    return {"push": push_sent, "sms": sms_sent, "ntfy": ntfy_sent}

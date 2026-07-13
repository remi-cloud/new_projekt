"""Dispatch alerts to push + SMS channels."""

from __future__ import annotations

import logging

from app.db.database import log_notification
from app.notifications.alert_engine import AlertEvent
from app.notifications.push import send_push_alerts
from app.notifications.sms import send_sms_alerts
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)


async def dispatch_alerts(events: list[AlertEvent]) -> dict[str, int]:
    if not events:
        return {"push": 0, "sms": 0}

    push_sent = await send_push_alerts(events)
    sms_sent = await send_sms_alerts(events)

    for event in events:
        await log_notification("push", event.symbol, event.reason, push_sent > 0)
        await log_notification("sms", event.symbol, event.reason, sms_sent > 0)

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

    logger.info("Alerts dispatched: %d events, push=%d sms=%d", len(events), push_sent, sms_sent)
    return {"push": push_sent, "sms": sms_sent}

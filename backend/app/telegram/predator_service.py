"""Poll Telegram for Predator relay messages and feed desk/alerts."""

from __future__ import annotations

import logging

from app.config import settings
from app.notifications.alert_engine import AlertEvent
from app.notifications.dispatcher import dispatch_alerts
from app.telegram import predator_client, predator_db
from app.telegram.predator_parser import parse_predator_message

logger = logging.getLogger(__name__)


async def poll_predator_feed(*, notify: bool = True) -> dict:
    """Fetch new Telegram updates, parse signals, store, optionally alert."""
    if not getattr(settings, "telegram_predator_enabled", True):
        return {"ok": False, "reason": "disabled", "new": 0, "updates": 0}
    if not predator_client.predator_configured():
        return {"ok": False, "reason": "no_token", "new": 0, "updates": 0}

    await predator_db.init_predator_db()
    offset = await predator_db.get_offset()
    updates = await predator_client.fetch_updates(offset=offset + 1 if offset else 0)
    new_signals = 0
    events: list[AlertEvent] = []
    max_update_id = offset

    for upd in updates:
        uid = int(upd.get("update_id") or 0)
        if uid > max_update_id:
            max_update_id = uid
        text, mid, chat_id = predator_client.extract_text_from_update(upd)
        if not text or not chat_id:
            continue
        if not predator_client.chat_allowed(chat_id):
            continue
        parsed = parse_predator_message(text)
        for sig in parsed:
            inserted = await predator_db.upsert_signal(
                tg_message_id=mid,
                chat_id=chat_id,
                symbol=sig.symbol,
                action=sig.action,
                confidence=sig.confidence,
                reason=sig.reason,
                raw_text=text,
            )
            if not inserted:
                continue
            new_signals += 1
            events.append(
                AlertEvent(
                    symbol=sig.symbol,
                    name=f"Predator {sig.raw_symbol}",
                    action=sig.action,
                    confidence=sig.confidence,
                    price=0.0,
                    reason=sig.reason,
                )
            )

    if max_update_id > offset:
        await predator_db.set_offset(max_update_id)

    notified = 0
    if notify and events and getattr(settings, "telegram_predator_notify", True):
        result = await dispatch_alerts(events)
        notified = sum(result.values())

    logger.info(
        "Predator Telegram poll: updates=%d new_signals=%d notified=%d",
        len(updates),
        new_signals,
        notified,
    )
    return {
        "ok": True,
        "updates": len(updates),
        "new": new_signals,
        "notified": notified,
        "offset": max_update_id,
    }


async def predator_status() -> dict:
    await predator_db.init_predator_db()
    me = await predator_client.get_me() if predator_client.predator_configured() else None
    signals = await predator_db.list_signals(limit=5)
    return {
        "enabled": bool(getattr(settings, "telegram_predator_enabled", True)),
        "configured": predator_client.predator_configured(),
        "notify": bool(getattr(settings, "telegram_predator_notify", True)),
        "chat_id_filter": (getattr(settings, "telegram_predator_chat_id", "") or "") or None,
        "bot": me,
        "free_setup": "BotFather token (free) + channel where you forward Predator posts",
        "recent": signals,
    }

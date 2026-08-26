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
    """Fetch new Telegram updates, parse signals, store, optionally alert.

    Shares one BotFather getUpdates stream with FOMO Family Telegram ingest.
    """
    predator_on = bool(getattr(settings, "telegram_predator_enabled", True))
    try:
        from app.fomo.telegram import fomo_telegram_enabled, ingest_fomo_telegram_text
    except Exception:
        fomo_telegram_enabled = lambda: False  # type: ignore[assignment]
        ingest_fomo_telegram_text = None  # type: ignore[assignment]

    fomo_tg_on = bool(fomo_telegram_enabled())
    if not predator_on and not fomo_tg_on:
        return {"ok": False, "reason": "disabled", "new": 0, "updates": 0}
    if not predator_client.predator_configured():
        return {"ok": False, "reason": "no_token", "new": 0, "updates": 0}

    await predator_db.init_predator_db()
    offset = await predator_db.get_offset()
    updates = await predator_client.fetch_updates(offset=offset + 1 if offset else 0)
    new_signals = 0
    events: list[AlertEvent] = []
    max_update_id = offset
    fomo_tg_new = 0

    for upd in updates:
        uid = int(upd.get("update_id") or 0)
        if uid > max_update_id:
            max_update_id = uid
        text, mid, chat_id = predator_client.extract_text_from_update(upd)
        if not text or not chat_id:
            continue

        # Shared getUpdates: also route FOMO Family / bag alerts (same bot token).
        if fomo_tg_on and ingest_fomo_telegram_text is not None:
            try:
                fomo_tg_new += await ingest_fomo_telegram_text(
                    text, message_id=mid, chat_id=chat_id
                )
            except Exception as exc:
                logger.debug("FOMO Telegram ingest skipped: %s", exc)

        if not predator_on:
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
        "Predator Telegram poll: updates=%d new_signals=%d fomo_tg=%d notified=%d",
        len(updates),
        new_signals,
        fomo_tg_new,
        notified,
    )
    return {
        "ok": True,
        "updates": len(updates),
        "new": new_signals,
        "fomo_telegram_new": fomo_tg_new,
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

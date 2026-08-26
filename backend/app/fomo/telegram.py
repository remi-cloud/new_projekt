"""Ingest FOMO Family Telegram channel posts into fomo_events."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.fomo import db as fomo_db
from app.fomo.telegram_parser import (
    looks_like_fomo_message,
    parse_fomo_telegram_message,
    signal_to_event,
)

logger = logging.getLogger(__name__)


def fomo_telegram_enabled() -> bool:
    return bool(getattr(settings, "fomo_telegram_enabled", True))


def fomo_telegram_chat_ids() -> set[str]:
    raw = (getattr(settings, "fomo_telegram_chat_ids", "") or "").strip()
    if not raw:
        return set()
    out: set[str] = set()
    for part in raw.replace(";", ",").split(","):
        c = part.strip()
        if c:
            out.add(c)
            out.add(c.lstrip("-"))
    return out


def chat_is_fomo(chat_id: str) -> bool:
    allowed = fomo_telegram_chat_ids()
    if not allowed:
        return False
    return chat_id in allowed or chat_id.lstrip("-") in allowed


async def ingest_fomo_telegram_text(
    text: str,
    *,
    message_id: int | None,
    chat_id: str,
    force: bool = False,
) -> int:
    """Parse and insert FOMO events. Returns number newly inserted."""
    if not fomo_telegram_enabled():
        return 0
    is_channel = chat_is_fomo(chat_id)
    if not force and not is_channel and not looks_like_fomo_message(text):
        return 0

    default_handle = None
    if is_channel:
        default_handle = f"tg_{chat_id.lstrip('-')[-10:]}"

    signals = parse_fomo_telegram_message(
        text,
        default_handle=default_handle if is_channel else None,
        chat_id=chat_id,
    )
    if not signals and is_channel and force:
        signals = parse_fomo_telegram_message(
            text,
            default_handle=default_handle,
            chat_id=chat_id,
        )

    await fomo_db.init_fomo_db()
    inserted = 0
    for sig in signals:
        ev = signal_to_event(sig, message_id=message_id, chat_id=chat_id)
        if await fomo_db.insert_event(ev):
            inserted += 1
    if inserted:
        logger.info(
            "FOMO Telegram: chat=%s inserted=%d msg=%s",
            chat_id,
            inserted,
            message_id,
        )
    return inserted


async def fomo_telegram_status() -> dict[str, Any]:
    chats = sorted(fomo_telegram_chat_ids())
    return {
        "enabled": fomo_telegram_enabled(),
        "configured_chats": chats,
        "listen_mode": "channel_filter" if chats else "heuristic_fomo_text",
        "shared_bot": bool(getattr(settings, "telegram_bot_token", "") or ""),
        "hint": (
            "Add bot as admin to FOMO Family forward channel; "
            "set CYCLICAL_FOMO_TELEGRAM_CHAT_IDS to that chat id"
        ),
    }

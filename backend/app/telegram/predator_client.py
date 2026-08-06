"""Free Telegram Bot API client for Predator signal relay.

BotFather token is free. The bot must be admin of a channel that receives
Predator forwards (Bot API cannot read arbitrary private bots).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def predator_configured() -> bool:
    return bool(getattr(settings, "telegram_bot_token", "") or "")


async def get_me() -> dict[str, Any] | None:
    token = getattr(settings, "telegram_bot_token", "") or ""
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            return data.get("result") if data.get("ok") else None
    except Exception as exc:
        logger.warning("Telegram getMe failed: %s", exc)
        return None


async def fetch_updates(offset: int = 0, timeout: int = 0) -> list[dict[str, Any]]:
    token = getattr(settings, "telegram_bot_token", "") or ""
    if not token:
        return []
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params: list[tuple[str, str | int]] = [
        ("offset", offset),
        ("timeout", timeout),
        ("allowed_updates", '["channel_post","message"]'),
    ]
    try:
        async with httpx.AsyncClient(timeout=max(25, timeout + 10)) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                logger.warning("Telegram getUpdates not ok: %s", data)
                return []
            return list(data.get("result") or [])
    except Exception as exc:
        logger.warning("Telegram getUpdates failed: %s", exc)
        return []


def extract_text_from_update(upd: dict[str, Any]) -> tuple[str, int | None, str]:
    """Return (text, message_id, chat_id)."""
    msg = upd.get("channel_post") or upd.get("message") or {}
    text = msg.get("text") or msg.get("caption") or ""
    mid = msg.get("message_id")
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id") or chat.get("username") or "")
    return str(text), int(mid) if mid is not None else None, chat_id


def chat_allowed(chat_id: str) -> bool:
    allowed = (getattr(settings, "telegram_predator_chat_id", "") or "").strip()
    if not allowed:
        return True  # accept all chats the bot can see
    return chat_id == allowed or chat_id.lstrip("-") == allowed.lstrip("-")

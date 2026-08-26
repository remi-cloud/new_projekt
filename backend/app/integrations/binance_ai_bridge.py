"""Binance AI BOT bridge — offline radar/whale data + optional external bot URL."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}
_CACHE_TTL = 300.0
_HTTP_TIMEOUT = 20.0


async def _offline_context() -> dict[str, Any]:
    from app.data.whale_flows import fetch_whale_snapshot
    from app.launch_scout.client_binance_radar import fetch_binance_radar

    radar = await fetch_binance_radar(limit=12)
    whale = await fetch_whale_snapshot(["BTC", "ETH", "SOL"])
    return {
        "mode": "offline",
        "source": "binance_radar+whale_flows",
        "radar_headlines": [
            {"title": r.get("title"), "tags": r.get("tags"), "url": r.get("url")}
            for r in radar[:8]
        ],
        "whale_bias": {
            sym: {
                "bias": (whale.get(sym) or {}).get("bias"),
                "source": (whale.get(sym) or {}).get("source"),
            }
            for sym in ("BTC", "ETH", "SOL")
            if whale.get(sym)
        },
    }


async def _remote_context() -> dict[str, Any] | None:
    url = (getattr(settings, "binance_ai_bot_url", "") or "").strip()
    if not url:
        return None
    key = (getattr(settings, "binance_ai_bot_key", "") or "").strip()
    headers = {"User-Agent": "CyclicalTrader-BinanceBridge/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return {"mode": "remote", "source": url, "remote": data}
    except Exception as exc:
        logger.warning("Binance AI BOT remote fetch failed: %s", exc)
    return None


async def get_binance_ai_context(*, force: bool = False) -> dict[str, Any]:
    """Read-only context for Finance Agent + coordinator."""
    now = time.monotonic()
    if not force and _CACHE["payload"] and now - float(_CACHE["at"]) < _CACHE_TTL:
        return _CACHE["payload"]

    offline = await _offline_context()
    remote = await _remote_context()
    payload: dict[str, Any] = {
        "ok": True,
        "mode": offline["mode"],
        "source": offline["source"],
        **offline,
    }
    if remote:
        payload["mode"] = "hybrid"
        payload["source"] = f"{offline['source']}+{remote['source']}"
        payload["remote"] = remote.get("remote")

    _CACHE["at"] = now
    _CACHE["payload"] = payload
    return payload

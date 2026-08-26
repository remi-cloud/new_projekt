"""Binance Spot API — signed account reads (read-only by default)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_ACCOUNT_URLS = (
    "https://api.binance.com/api/v3/account",
    "https://data-api.binance.vision/api/v3/account",
)
_HTTP_TIMEOUT = 20.0
_UA = "CyclicalTrader-BinanceSpot/1.0"


def binance_configured() -> bool:
    return bool(
        (getattr(settings, "binance_api_key", "") or "").strip()
        and (getattr(settings, "binance_api_secret", "") or "").strip()
    )


def _sign(query: str, secret: str) -> str:
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


async def fetch_spot_balances() -> list[dict[str, Any]]:
    """Return non-zero spot balances [{asset, free, locked, total}]."""
    api_key = (getattr(settings, "binance_api_key", "") or "").strip()
    api_secret = (getattr(settings, "binance_api_secret", "") or "").strip()
    if not api_key or not api_secret:
        return []

    ts = int(time.time() * 1000)
    query = urlencode({"timestamp": ts, "recvWindow": 5000})
    signature = _sign(query, api_secret)
    headers = {"X-MBX-APIKEY": api_key, "User-Agent": _UA}

    last_err: str | None = None
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        for base in _ACCOUNT_URLS:
            url = f"{base}?{query}&signature={signature}"
            try:
                r = await client.get(url, headers=headers)
                if r.status_code >= 400:
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    continue
                data = r.json()
                balances = data.get("balances") if isinstance(data, dict) else None
                if not isinstance(balances, list):
                    return []
                out: list[dict[str, Any]] = []
                for row in balances:
                    if not isinstance(row, dict):
                        continue
                    asset = str(row.get("asset") or "").upper()
                    free = float(row.get("free") or 0)
                    locked = float(row.get("locked") or 0)
                    total = free + locked
                    if total <= 0:
                        continue
                    out.append({"asset": asset, "free": free, "locked": locked, "total": total})
                return out
            except Exception as exc:
                last_err = str(exc)
                logger.debug("Binance account %s failed: %s", base, exc)

    if last_err:
        logger.warning("Binance spot balances failed: %s", last_err)
    return []


def binance_trade_url(binance_symbol: str) -> str:
    sym = binance_symbol.upper().replace("-", "")
    if sym.endswith("USDT"):
        pair = sym
    else:
        pair = f"{sym}USDT"
    return f"https://www.binance.com/en/trade/{pair}?type=spot"

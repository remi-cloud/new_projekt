"""Cached ROI showcase presets for home page (multi-asset backtest)."""

from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

from app.roi.calculator import calculate_roi

SHOWCASE_PRESETS: list[dict[str, Any]] = [
    {"id": "btc", "symbol": "BTC-USD", "strategy": "cycle", "featured": True},
    {"id": "sp500", "symbol": "^GSPC", "strategy": "cycle", "featured": False},
    {"id": "gold", "symbol": "GC=F", "strategy": "cycle", "featured": False},
]

_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}
_CACHE_TTL_SEC = 3600


async def get_showcase(*, years: int = 10, amount: float = 10_000.0) -> dict:
    years = max(1, min(years, 40))
    amount = max(100.0, min(amount, 100_000_000.0))
    cache_key = f"{years}:{amount}"
    now = time.time()
    cached = _CACHE.get("payload")
    if cached and _CACHE.get("key") == cache_key and now < _CACHE.get("expires_at", 0):
        return cached

    end = date.today()
    start = end - timedelta(days=int(years * 365.25))

    cards: list[dict] = []
    for preset in SHOWCASE_PRESETS:
        result = await calculate_roi(
            symbol=preset["symbol"],
            amount=amount,
            strategy=preset["strategy"],
            start=start,
            end=end,
            compare_buy_hold=True,
        )
        cards.append(
            {
                "id": preset["id"],
                "featured": preset["featured"],
                "symbol": result["symbol"],
                "name": result["name"],
                "strategy": result["strategy"],
                "amount": result["amount"],
                "invested": result["invested"],
                "final_value": result["final_value"],
                "profit": result["profit"],
                "roi_pct": result["roi_pct"],
                "cagr_pct": result["cagr_pct"],
                "years": result["years"],
                "data_start": result["data_start"],
                "data_end": result["data_end"],
                "buy_hold": result.get("buy_hold"),
            }
        )

    payload = {
        "amount": amount,
        "years": years,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "strategy": "cycle",
        "cards": cards,
        "disclaimer": "Educational simulation — not investment advice.",
    }
    _CACHE["key"] = cache_key
    _CACHE["payload"] = payload
    _CACHE["expires_at"] = now + _CACHE_TTL_SEC
    return payload

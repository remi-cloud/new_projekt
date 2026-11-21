"""ROI showcase presets for the home page (multi-asset 10y backtest).

Every number comes from a fresh Yahoo Finance download (daily closes, the last bar
is the live price). Results are cached for ``_CACHE_TTL_SEC`` only. When a refresh
fails we never invent values: a card keeps its last *real* result flagged
``stale`` with the time it was computed, or reports ``brak danych``.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.roi.calculator import calculate_roi

logger = logging.getLogger(__name__)

SHOWCASE_PRESETS: list[dict[str, Any]] = [
    {"id": "btc", "symbol": "BTC-USD", "strategy": "cycle", "featured": True},
    {"id": "sp500", "symbol": "^GSPC", "strategy": "cycle", "featured": False},
    {"id": "gold", "symbol": "GC=F", "strategy": "cycle", "featured": False},
]

_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}
_CACHE_TTL_SEC = 600  # 10 min
# Last successful card per (preset id, years, amount) — real data only.
_LAST_GOOD: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _card_from_result(preset: dict, result: dict) -> dict:
    return {
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
        "start_price": result.get("start_price"),
        "end_price": result.get("end_price"),
        "last_bar_time": result.get("last_bar_time"),
        "trades_count": len(result.get("trades") or []),
        "strategy_rules": result.get("strategy_rules"),
        "source": result.get("source") or "Yahoo Finance",
        "updated_at": result.get("computed_at") or _now_iso(),
        "buy_hold": {
            k: v
            for k, v in (result.get("buy_hold") or {}).items()
            if k in ("final_value", "roi_pct", "cagr_pct", "max_drawdown_pct")
        }
        or None,
        "stale": False,
        "available": True,
    }


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
    any_fresh = False
    for preset in SHOWCASE_PRESETS:
        good_key = f"{preset['id']}:{cache_key}"
        try:
            result = await calculate_roi(
                symbol=preset["symbol"],
                amount=amount,
                strategy=preset["strategy"],
                start=start,
                end=end,
                compare_buy_hold=True,
            )
            card = _card_from_result(preset, result)
            _LAST_GOOD[good_key] = card
            any_fresh = True
        except Exception as exc:  # network / provider failure → never invent numbers
            logger.warning("Showcase %s refresh failed: %s", preset["symbol"], exc)
            last = _LAST_GOOD.get(good_key)
            if last:
                card = {**last, "stale": True, "error": "refresh_failed"}
            else:
                card = {
                    "id": preset["id"],
                    "featured": preset["featured"],
                    "symbol": preset["symbol"],
                    "name": preset["symbol"],
                    "strategy": preset["strategy"],
                    "available": False,
                    "stale": True,
                    "error": "brak danych",
                    "updated_at": None,
                    "source": "Yahoo Finance",
                }
        cards.append(card)

    payload = {
        "amount": amount,
        "years": years,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "strategy": "cycle",
        "cards": cards,
        "source": "Yahoo Finance (dzienne ceny zamknięcia; ostatnia świeca = cena bieżąca)",
        "updated_at": _now_iso(),
        "refresh_seconds": _CACHE_TTL_SEC,
        "disclaimer": "Educational simulation — not investment advice.",
    }
    _CACHE["key"] = cache_key
    _CACHE["payload"] = payload
    # Retry quickly when nothing could be refreshed.
    _CACHE["expires_at"] = now + (_CACHE_TTL_SEC if any_fresh else 60)
    return payload

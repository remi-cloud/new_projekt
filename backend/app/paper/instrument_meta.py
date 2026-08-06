"""Resolve tradable instrument metadata (monitored + pearls + open positions)."""

from __future__ import annotations

from app.data.assets import MONITORED_ASSETS
from app.paper.currency import native_currency

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}


async def resolve_instrument_meta(symbol: str) -> dict:
    """Return {symbol, name, asset_class, region} for any tradable ticker.

    Monitored universe first, then pearl finds, then open paper position,
    finally a safe generic stock fallback (Yahoo-tradable symbols).
    """
    known = ASSET_MAP.get(symbol)
    if known:
        return {
            "symbol": symbol,
            "name": known["name"],
            "asset_class": known["asset_class"],
            "region": known.get("region", "global"),
        }

    try:
        from app.ai.pearl_hunter.db import get_find_by_symbol

        pearl = await get_find_by_symbol(symbol)
        if pearl:
            return {
                "symbol": symbol,
                "name": pearl.get("name") or symbol,
                "asset_class": pearl.get("asset_class") or "stock",
                "region": pearl.get("region") or "global",
            }
    except Exception:
        pass

    try:
        from app.paper import paper_db

        pos = await paper_db.get_position(symbol)
        if pos:
            return {
                "symbol": symbol,
                "name": pos.get("name") or symbol,
                "asset_class": pos.get("asset_class") or "stock",
                "region": "global",
            }
    except Exception:
        pass

    # Allow paper trades on any Yahoo-resolvable symbol (pearls / ad-hoc).
    return {
        "symbol": symbol,
        "name": symbol,
        "asset_class": "stock" if not symbol.endswith("-USD") else "crypto",
        "region": "global",
        "currency_hint": native_currency(symbol),
    }

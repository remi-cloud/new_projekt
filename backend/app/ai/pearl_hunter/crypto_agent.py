"""Crypto pearl agent — CoinGecko movers outside core universe."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.ai.pearl_hunter.db import record_run, upsert_find
from app.ai.pearl_hunter.scoring import score_crypto_mover
from app.ai.pearl_hunter.universe import is_monitored
from app.config import settings
from app.data.broker_map import resolve_broker_info

logger = logging.getLogger(__name__)

AGENT_ID = "pearl_crypto"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CyclicalPearl/1.0)"}


async def run_crypto_agent() -> list[dict]:
    if not getattr(settings, "pearl_hunter_enabled", True):
        return []

    min_score = float(getattr(settings, "pearl_min_score", 55.0))
    max_store = int(getattr(settings, "pearl_max_store_per_run", 15))
    finds: list[dict] = []
    error = ""

    try:
        url = f"{settings.coingecko_base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "price_change_percentage_24h_desc",
            "per_page": 80,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            markets = resp.json()

        for coin in markets:
            symbol_base = (coin.get("symbol") or "").upper()
            if not symbol_base:
                continue
            yahoo_sym = f"{symbol_base}-USD"
            if is_monitored(yahoo_sym) or symbol_base in ("BTC", "ETH", "USDT", "USDC", "DAI"):
                continue

            chg = coin.get("price_change_percentage_24h")
            if chg is None:
                chg = coin.get("price_change_percentage_24h_in_currency")
            rank = coin.get("market_cap_rank")
            vol = coin.get("total_volume")
            price = float(coin.get("current_price") or 0)
            name = coin.get("name") or symbol_base

            score, confidence, action, rationale = score_crypto_mover(
                change_pct_24h=float(chg) if chg is not None else None,
                market_cap_rank=int(rank) if rank else None,
                volume_usd=float(vol) if vol else None,
            )
            if score < min_score:
                continue

            find = {
                "agent_id": AGENT_ID,
                "symbol": yahoo_sym,
                "name": name,
                "asset_class": "crypto",
                "region": "global",
                "price": price,
                "change_pct_24h": round(float(chg), 2) if chg is not None else None,
                "score": score,
                "confidence": confidence,
                "action": action,
                "rationale": rationale,
                "source": "coingecko_markets",
                "found_at": datetime.now(timezone.utc).isoformat(),
                "broker_info": resolve_broker_info(yahoo_sym, "crypto", "global"),
            }
            await upsert_find(find)
            finds.append(find)

        finds.sort(key=lambda x: x["score"], reverse=True)
        finds = finds[:max_store]
    except Exception as exc:
        error = str(exc)
        logger.exception("Crypto pearl agent failed: %s", exc)

    await record_run(AGENT_ID, len(finds), error)
    return finds

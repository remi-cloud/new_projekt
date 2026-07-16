"""Equity pearl agent — Yahoo chart scan outside core universe."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import quote as url_quote

import httpx

from app.ai.pearl_hunter.db import record_run, upsert_find
from app.ai.pearl_hunter.scoring import score_equity_momentum
from app.ai.pearl_hunter.universe import equity_candidates
from app.config import settings
from app.data.broker_map import resolve_broker_info

logger = logging.getLogger(__name__)

AGENT_ID = "pearl_equity"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CyclicalPearl/1.0)"}
_SEMAPHORE = asyncio.Semaphore(6)


async def run_equity_agent() -> list[dict]:
    if not getattr(settings, "pearl_hunter_enabled", True):
        return []

    limit = int(getattr(settings, "pearl_equity_candidates", 36))
    min_score = float(getattr(settings, "pearl_min_score", 55.0))
    candidates = equity_candidates(limit=limit)
    finds: list[dict] = []
    error = ""

    try:
        async with httpx.AsyncClient(timeout=22, headers=YAHOO_HEADERS) as client:
            tasks = [_scan_symbol(client, asset) for asset in candidates]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for asset, result in zip(candidates, results):
            if isinstance(result, Exception):
                logger.debug("Pearl equity skip %s: %s", asset["symbol"], result)
                continue
            if not result:
                continue
            if result["score"] < min_score:
                continue
            result["broker_info"] = resolve_broker_info(
                result["symbol"], result["asset_class"], result.get("region")
            )
            await upsert_find(result)
            finds.append(result)

        finds.sort(key=lambda x: x["score"], reverse=True)
        finds = finds[: int(getattr(settings, "pearl_max_store_per_run", 15))]
    except Exception as exc:
        error = str(exc)
        logger.exception("Equity pearl agent failed: %s", exc)

    await record_run(AGENT_ID, len(finds), error)
    return finds


async def _scan_symbol(client: httpx.AsyncClient, asset: dict) -> dict | None:
    symbol = asset["symbol"]
    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    params = {"range": "1y", "interval": "1d"}

    async with _SEMAPHORE:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        payload = resp.json()

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return None
    meta = result[0].get("meta") or {}
    closes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    closes = [c for c in closes if c is not None]
    if len(closes) < 20:
        return None

    price = float(meta.get("regularMarketPrice") or closes[-1])
    prev = closes[-2] if len(closes) >= 2 else closes[-1]
    change_pct = ((price - prev) / prev * 100.0) if prev else 0.0
    low_52 = min(closes)
    high_52 = max(closes)
    dist_low = ((price - low_52) / low_52 * 100.0) if low_52 else None
    dist_high = ((high_52 - price) / high_52 * 100.0) if high_52 else None

    score, confidence, action, rationale = score_equity_momentum(
        change_pct=change_pct,
        dist_from_low_pct=dist_low,
        dist_from_high_pct=dist_high,
    )

    return {
        "agent_id": AGENT_ID,
        "symbol": symbol,
        "name": asset["name"],
        "asset_class": asset["asset_class"],
        "region": asset.get("region", "us"),
        "price": round(price, 4),
        "change_pct_24h": round(change_pct, 2),
        "score": score,
        "confidence": confidence,
        "action": action,
        "rationale": rationale,
        "source": "yahoo_chart_1y",
        "found_at": datetime.now(timezone.utc).isoformat(),
    }

"""Lightweight batch price fetch for real-time ticker (Yahoo v7 quote API)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import quote as url_quote

import httpx

from app.data.assets import MONITORED_ASSETS
from app.data.investing_com import fetch_investing_quote, uses_investing
from app.models.schemas import AssetClass, AssetQuote

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
BATCH_SIZE = 45
FETCH_SEMAPHORE = asyncio.Semaphore(8)
INVESTING_SEMAPHORE = asyncio.Semaphore(2)

ASSET_BY_SYMBOL = {a["symbol"]: a for a in MONITORED_ASSETS}


async def fetch_fast_quotes(
    symbols: list[str] | None = None,
) -> dict[str, AssetQuote]:
    """Return latest prices for symbols (default: all monitored)."""
    now = datetime.now(timezone.utc)
    target = symbols or [a["symbol"] for a in MONITORED_ASSETS]

    yahoo_symbols: list[str] = []
    investing_symbols: list[str] = []

    for sym in target:
        meta = ASSET_BY_SYMBOL.get(sym)
        if not meta:
            continue
        if uses_investing(sym, meta.get("region")):
            investing_symbols.append(sym)
        else:
            yahoo_symbols.append(sym)

    quotes: dict[str, AssetQuote] = {}

    async with httpx.AsyncClient(timeout=20, headers=YAHOO_HEADERS) as client:
        yahoo_tasks = [
            _fetch_yahoo_batch(client, batch, now)
            for batch in _chunks(yahoo_symbols, BATCH_SIZE)
        ]
        investing_tasks = [_fetch_investing_fast(sym, now) for sym in investing_symbols]

        for batch_result in await asyncio.gather(*yahoo_tasks, return_exceptions=True):
            if isinstance(batch_result, dict):
                quotes.update(batch_result)

        # Yahoo v7 quote API often returns 401 — fallback to v8 chart spot
        missing_yahoo = [s for s in yahoo_symbols if s not in quotes]
        if missing_yahoo:
            v8_tasks = [_fetch_yahoo_v8_spot(client, sym, now) for sym in missing_yahoo]
            v8_results = await asyncio.gather(*v8_tasks, return_exceptions=True)
            for sym, result in zip(missing_yahoo, v8_results):
                if isinstance(result, AssetQuote):
                    quotes[sym] = result

        inv_results = await asyncio.gather(*investing_tasks, return_exceptions=True)
        for sym, result in zip(investing_symbols, inv_results):
            if isinstance(result, AssetQuote):
                quotes[sym] = result

    return quotes


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _fetch_yahoo_batch(
    client: httpx.AsyncClient,
    symbols: list[str],
    now: datetime,
) -> dict[str, AssetQuote]:
    if not symbols:
        return {}

    async with FETCH_SEMAPHORE:
        encoded = ",".join(url_quote(s, safe="") for s in symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            results = resp.json().get("quoteResponse", {}).get("result", [])
        except Exception as exc:
            logger.warning("Yahoo batch quote failed: %s", exc)
            return {}

    out: dict[str, AssetQuote] = {}
    for item in results:
        sym = item.get("symbol")
        meta = ASSET_BY_SYMBOL.get(sym)
        if not meta:
            continue
        price = item.get("regularMarketPrice")
        if price is None:
            continue
        change_pct = item.get("regularMarketChangePercent")
        out[sym] = AssetQuote(
            symbol=sym,
            name=meta["name"],
            asset_class=AssetClass(meta["asset_class"]),
            price=round(float(price), 4),
            change_pct_24h=round(float(change_pct), 2) if change_pct is not None else None,
            updated_at=now,
        )
    return out


async def _fetch_yahoo_v8_spot(
    client: httpx.AsyncClient,
    symbol: str,
    now: datetime,
) -> AssetQuote | None:
    """Spot price via Yahoo v8 chart API (works when v7 quote returns 401)."""
    meta = ASSET_BY_SYMBOL.get(symbol)
    if not meta:
        return None

    async with FETCH_SEMAPHORE:
        encoded = url_quote(symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        try:
            resp = await client.get(url, params={"range": "1d", "interval": "1m"})
            resp.raise_for_status()
            result = resp.json().get("chart", {}).get("result")
            if not result:
                return None
            r = result[0]
            ymeta = r.get("meta") or {}
            price = ymeta.get("regularMarketPrice")
            if price is None:
                q = (r.get("indicators") or {}).get("quote", [{}])[0]
                closes = [c for c in (q.get("close") or []) if c is not None]
                if not closes:
                    return None
                price = closes[-1]
            prev = ymeta.get("chartPreviousClose") or ymeta.get("previousClose") or price
            change_pct = None
            if prev and float(prev) != 0:
                change_pct = round((float(price) - float(prev)) / float(prev) * 100, 2)
            return AssetQuote(
                symbol=symbol,
                name=meta["name"],
                asset_class=AssetClass(meta["asset_class"]),
                price=round(float(price), 4),
                change_pct_24h=change_pct,
                updated_at=now,
            )
        except Exception as exc:
            logger.debug("Yahoo v8 spot failed for %s: %s", symbol, exc)
            return None


async def _fetch_investing_fast(symbol: str, now: datetime) -> AssetQuote | None:
    meta = ASSET_BY_SYMBOL.get(symbol)
    if not meta:
        return None
    async with INVESTING_SEMAPHORE:
        quote, _ = await fetch_investing_quote(meta, now)
        return quote

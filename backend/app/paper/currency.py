"""Currency conversion for paper trading (account in PLN)."""

from __future__ import annotations

import logging
import time

import httpx

from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

DEFAULT_USD_PLN = 3.95
_CACHE_TTL_SEC = 300
_rate_cache: dict[str, float] = {"expires_at": 0.0, "value": DEFAULT_USD_PLN}

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def native_currency(symbol: str) -> str:
    if symbol.endswith(".WA"):
        return "PLN"
    return "USD"


def _from_scanner_quotes() -> float | None:
    for q in scanner.quotes:
        if q.symbol in ("USDPLN=X", "PLN=X"):
            return float(q.price)
    return None


async def _fetch_v8_chart(client: httpx.AsyncClient, symbol: str) -> float | None:
    resp = await client.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d",
        headers=YAHOO_HEADERS,
    )
    if resp.status_code != 200:
        return None
    result = resp.json().get("chart", {}).get("result", [])
    if not result:
        return None
    meta = result[0].get("meta", {})
    price = meta.get("regularMarketPrice")
    return float(price) if price else None


async def _fetch_v7_quote(client: httpx.AsyncClient, symbol: str) -> float | None:
    resp = await client.get(
        f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}",
        headers=YAHOO_HEADERS,
    )
    if resp.status_code != 200:
        return None
    results = resp.json().get("quoteResponse", {}).get("result", [])
    if results and results[0].get("regularMarketPrice"):
        return float(results[0]["regularMarketPrice"])
    return None


async def get_usd_pln_rate(*, allow_network: bool = True) -> float:
    from_quote = _from_scanner_quotes()
    if from_quote and from_quote > 0:
        _rate_cache["value"] = from_quote
        _rate_cache["expires_at"] = time.time() + _CACHE_TTL_SEC
        return from_quote

    now = time.time()
    if now < _rate_cache.get("expires_at", 0):
        return float(_rate_cache["value"])

    if not allow_network:
        return float(_rate_cache.get("value") or DEFAULT_USD_PLN)

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            rate = await _fetch_v8_chart(client, "USDPLN=X")
            if not rate or rate <= 0:
                rate = await _fetch_v7_quote(client, "USDPLN%3DX")
            if not rate or rate <= 0:
                pln_x = await _fetch_v8_chart(client, "PLN=X")
                if pln_x and pln_x > 0:
                    rate = 1.0 / pln_x
            if rate and rate > 0:
                _rate_cache["value"] = float(rate)
                _rate_cache["expires_at"] = now + _CACHE_TTL_SEC
                return float(rate)
    except Exception as exc:
        logger.warning("USD/PLN fetch failed: %s", exc)

    cached = float(_rate_cache.get("value") or DEFAULT_USD_PLN)
    logger.info("USD/PLN using fallback rate: %.4f", cached)
    return cached


def to_pln(price_native: float, currency: str, usd_pln: float) -> float:
    if currency == "PLN":
        return price_native
    return price_native * usd_pln


def from_pln(amount_pln: float, currency: str, usd_pln: float) -> float:
    if currency == "PLN":
        return amount_pln
    return amount_pln / usd_pln if usd_pln > 0 else amount_pln

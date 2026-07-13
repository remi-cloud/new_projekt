"""Currency conversion for paper trading (account in PLN)."""

from __future__ import annotations

import logging

import httpx

from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

DEFAULT_USD_PLN = 3.95


def native_currency(symbol: str) -> str:
    if symbol.endswith(".WA"):
        return "PLN"
    return "USD"


async def get_usd_pln_rate() -> float:
    for q in scanner.quotes:
        if q.symbol in ("USDPLN=X", "PLN=X"):
            return float(q.price)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://query1.finance.yahoo.com/v7/finance/quote?symbols=USDPLN%3DX",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            results = resp.json().get("quoteResponse", {}).get("result", [])
            if results and results[0].get("regularMarketPrice"):
                return float(results[0]["regularMarketPrice"])
    except Exception as exc:
        logger.warning("USD/PLN fetch failed: %s", exc)
    return DEFAULT_USD_PLN


def to_pln(price_native: float, currency: str, usd_pln: float) -> float:
    if currency == "PLN":
        return price_native
    return price_native * usd_pln


def from_pln(amount_pln: float, currency: str, usd_pln: float) -> float:
    if currency == "PLN":
        return amount_pln
    return amount_pln / usd_pln if usd_pln > 0 else amount_pln

"""Live price lookup for paper trading."""

from __future__ import annotations

import logging

from app.data.assets import MONITORED_ASSETS
from app.data.fast_quotes import fetch_fast_quotes
from app.data.market_data import _quote_price_round
from app.models.schemas import AssetQuote
from app.paper.currency import native_currency
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)


class PaperTradeError(Exception):
    def __init__(self, message: str, code: str = "trade_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def merge_fast_quotes(fast: dict[str, AssetQuote]) -> None:
    """Merge batch quotes into scanner cache (used by price tick + portfolio marks)."""
    if not fast:
        return
    quote_map = {q.symbol: q for q in scanner.quotes}
    for sym, q in fast.items():
        existing = quote_map.get(sym)
        if existing:
            existing.price = q.price
            existing.change_pct_24h = q.change_pct_24h or existing.change_pct_24h
            existing.updated_at = q.updated_at
        else:
            scanner.quotes.append(q)
            quote_map[sym] = q


async def refresh_quotes_for_symbols(symbols: list[str]) -> int:
    """Fetch fresh prices for open positions / mark-to-market."""
    if not symbols:
        return 0
    unique = list(dict.fromkeys(symbols))
    fast = await fetch_fast_quotes(unique)
    merge_fast_quotes(fast)
    if len(fast) < len(unique):
        missing = set(unique) - set(fast.keys())
        logger.debug("Portfolio quote refresh missing symbols: %s", sorted(missing)[:8])
    return len(fast)


def get_live_price(symbol: str) -> tuple[float, str]:
    """Sync lookup from scanner cache (order execution hot path)."""
    for q in scanner.quotes:
        if q.symbol == symbol:
            # Stale rounded-to-zero cache for micro-cap crypto — force refresh path.
            if q.price == 0 and symbol.endswith("-USD"):
                break
            return q.price, native_currency(symbol)
    raise PaperTradeError(f"Brak ceny na żywo dla {symbol}", "no_price")


async def get_live_price_async(symbol: str) -> tuple[float, str]:
    """Mark-to-market — on-demand fetch when cache miss."""
    try:
        return get_live_price(symbol)
    except PaperTradeError:
        pass

    fast = await fetch_fast_quotes([symbol])
    merge_fast_quotes(fast)
    if symbol in fast:
        return fast[symbol].price, native_currency(symbol)

    # Yahoo chart last close — works for pearls / non-monitored symbols
    from datetime import datetime, timezone

    from app.data.chart_data import fetch_chart
    from app.models.schemas import AssetClass, AssetQuote

    chart = await fetch_chart(symbol, "1D")
    if chart and chart.candles:
        price = float(chart.candles[-1].close)
        currency = native_currency(symbol)
        meta = next((a for a in MONITORED_ASSETS if a["symbol"] == symbol), None)
        asset_class = AssetClass(meta["asset_class"]) if meta else (
            AssetClass.CRYPTO if symbol.endswith("-USD") else AssetClass.STOCK
        )
        name = meta["name"] if meta else symbol
        merge_fast_quotes(
            {
                symbol: AssetQuote(
                    symbol=symbol,
                    name=name,
                    asset_class=asset_class,
                    price=_quote_price_round(price),
                    change_pct_24h=None,
                    updated_at=datetime.now(timezone.utc),
                )
            }
        )
        return price, currency

    meta = next((a for a in MONITORED_ASSETS if a["symbol"] == symbol), None)
    if meta:
        logger.warning("Live price unavailable for portfolio symbol %s", symbol)
    raise PaperTradeError(f"Brak ceny na żywo dla {symbol}", "no_price")

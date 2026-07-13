"""Live price lookup for paper trading."""

from __future__ import annotations

from app.data.assets import MONITORED_ASSETS
from app.paper.currency import native_currency
from app.scanners.opportunity_scanner import scanner


class PaperTradeError(Exception):
    def __init__(self, message: str, code: str = "trade_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def get_live_price(symbol: str) -> tuple[float, str]:
    for q in scanner.quotes:
        if q.symbol == symbol:
            return q.price, native_currency(symbol)
    raise PaperTradeError(f"Brak ceny na żywo dla {symbol}", "no_price")

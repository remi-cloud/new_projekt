"""Tests for asset analyzer with regional macro routing."""

from datetime import datetime, timezone

from app.models.schemas import AssetClass, AssetQuote, SignalAction
from app.scanners.asset_analyzer import AssetAnalyzer


def _quote(symbol: str, region: str, asset_class: AssetClass, price: float, change_7d=None):
    return AssetQuote(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        price=price,
        change_pct_24h=0.0,
        change_pct_7d=change_7d,
        updated_at=datetime.now(timezone.utc),
    )


def test_pl_stock_at_highs_not_always_buy():
    analyzer = AssetAnalyzer()
    quote = _quote("PKO.WA", "pl", AssetClass.STOCK, 100.0)
    stats = {"high_52w": 101.0, "low_52w": 70.0}  # near ATH → price SELL

    result = analyzer._assess_traditional(quote, "pl", stats, datetime.now(timezone.utc))
    assert result.macro_cycle == "polish_cycle"
    assert result.signal in (SignalAction.WATCH, SignalAction.HOLD, SignalAction.SELL)


def test_us_stock_uses_presidential():
    analyzer = AssetAnalyzer()
    quote = _quote("AAPL", "us", AssetClass.STOCK, 200.0)
    stats = {"high_52w": 220.0, "low_52w": 150.0}

    result = analyzer._assess_traditional(quote, "us", stats, datetime.now(timezone.utc))
    assert result.macro_cycle == "presidential_cycle"

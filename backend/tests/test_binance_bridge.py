"""Binance portfolio bridge tests (no network)."""

from app.integrations.binance_spot import binance_trade_url
from app.integrations.portfolio_binance_bridge import _catalog_symbol


def test_binance_trade_url():
    assert "BTCUSDT" in binance_trade_url("BTCUSDT")
    assert binance_trade_url("ETH").endswith("ETHUSDT?type=spot")


def test_catalog_symbol_reverse():
    assert _catalog_symbol("BTCUSDT") == "BTC-USD"
    assert _catalog_symbol("SOLUSDT") == "SOL-USD"

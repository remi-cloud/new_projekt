"""Tests for execution router."""

from app.data.broker_map import resolve_execution_brokers
from app.execution.router import route_broker
from app.execution.models import SignalCandidate


def test_crypto_routes_to_kraken():
    primary, fallback = resolve_execution_brokers("BTC-USD", "crypto", "global")
    assert primary == "kraken"
    assert fallback == "nexo"


def test_equity_routes_to_ibkr():
    primary, fallback = resolve_execution_brokers("AAPL", "stock", "us")
    assert primary == "ibkr"
    assert fallback == "etoro"


def test_route_broker_candidate():
    c = SignalCandidate(
        symbol="ETH-USD",
        name="Ethereum",
        asset_class="crypto",
        source="pearl",
        confidence=80,
    )
    primary, fallback = route_broker(c)
    assert primary == "kraken"


def test_binance_adapter_resolves():
    from app.execution.brokers import get_broker_adapter

    adapter = get_broker_adapter("binance")
    assert adapter.broker_id == "binance"

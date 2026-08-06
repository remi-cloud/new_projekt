"""Tokenized xStocks + crypto ETF catalog wiring."""

from app.agents.universes import default_universes
from app.data.assets import MONITORED_ASSETS, lookup_asset
from app.data.broker_map import resolve_broker_info, resolve_execution_brokers
from app.data.tokenized_universe import CRYPTO_ETF_UNIVERSE, TOKENIZED_UNIVERSE
from app.models.schemas import AssetClass


def test_asset_class_has_tokenized():
    assert AssetClass.TOKENIZED.value == "tokenized"


def test_tokenized_symbols_in_catalog():
    assert lookup_asset("AAPLX-USD") is not None
    assert lookup_asset("AAPLX-USD")["asset_class"] == "tokenized"
    assert lookup_asset("SPYX-USD")["asset_class"] == "tokenized"
    assert lookup_asset("IBIT")["asset_class"] == "etf"
    assert lookup_asset("FBTC")["asset_class"] == "etf"


def test_tokenized_universe_size():
    assert len(TOKENIZED_UNIVERSE) >= 20
    assert len(CRYPTO_ETF_UNIVERSE) >= 5
    tok = [a for a in MONITORED_ASSETS if a["asset_class"] == "tokenized"]
    assert len(tok) == len(TOKENIZED_UNIVERSE)


def test_tokenized_broker_prefers_kraken():
    info = resolve_broker_info("AAPLX-USD", "tokenized", "us")
    assert info["primary_exchange"].startswith("xStock")
    ids = [b["id"] for b in info["brokers"]]
    assert ids[0] == "kraken"
    primary, fallback = resolve_execution_brokers("AAPLX-USD", "tokenized", "us")
    assert primary == "kraken"
    assert fallback == "etoro"


def test_crypto_scout_includes_tokenized():
    u = default_universes()
    assert "AAPLX-USD" in u["crypto"].symbols
    assert AssetClass.TOKENIZED in u["crypto"].asset_classes
    assert "IBIT" in u["us_equity"].symbols

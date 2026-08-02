"""Region catalog + markets merge helpers."""

from app.data.assets import (
    DEFAULT_ASSETS,
    GLOBAL_MARKET_REGIONS,
    RETIRED_SYMBOLS,
    enrich_asset,
    is_global_market,
    resolve_region,
)
from app.data.market_data import stub_quote
from app.models.schemas import AssetQuote


def test_global_regions_cover_asia_russia_brazil():
    by_sym = {a["symbol"].upper(): enrich_asset(a) for a in DEFAULT_ASSETS}
    assert by_sym["^N225"]["region"] == "asia"
    assert by_sym["^HSI"]["region"] == "asia"
    assert by_sym["^BVSP"]["region"] == "americas"
    assert by_sym["EWZ"]["region"] == "americas"
    assert by_sym["IMOEX.ME"]["region"] == "russia"
    assert by_sym["RTSI.ME"]["region"] == "russia"
    assert by_sym["^GDAXI"]["region"] == "europe"
    assert by_sym["EEM"]["region"] == "world"
    assert by_sym["^GSPC"]["region"] == "usa"
    assert by_sym["AAPL"]["region"] == "usa"
    assert "^J203.JO" in by_sym
    assert "JN0U.JO" not in by_sym


def test_global_market_helper():
    assert is_global_market({"symbol": "^BVSP", "asset_class": "index"})
    assert is_global_market({"symbol": "^N225", "asset_class": "index"})
    assert not is_global_market({"symbol": "^GSPC", "asset_class": "index"})
    assert not is_global_market({"symbol": "AAPL", "asset_class": "stock"})


def test_retired_symbols_set():
    assert "JN0U.JO" in RETIRED_SYMBOLS


def test_stub_quote_has_region():
    asset = enrich_asset(DEFAULT_ASSETS[0])
    q = stub_quote(asset)
    assert isinstance(q, AssetQuote)
    assert q.live is False
    assert q.region
    assert q.region_label


def test_catalog_global_count():
    globals_ = [a for a in DEFAULT_ASSETS if resolve_region(a) in GLOBAL_MARKET_REGIONS]
    assert len(globals_) >= 50

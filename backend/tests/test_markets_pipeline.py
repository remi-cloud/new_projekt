"""Markets pipeline: every catalog symbol must resolve to a live sourced quote."""

from __future__ import annotations

import pytest

from app.data.assets import DEFAULT_ASSETS
from app.data.market_data import fetch_quotes, probe_market_providers
from app.data.tradingview import TV_SYMBOL_MAP, tv_ticker_for
from app.models.schemas import AssetClass, AssetQuote


@pytest.mark.asyncio
async def test_fetch_quotes_covers_full_catalog(monkeypatch):
    """Even if TV is partial, Yahoo fill must cover the whole book."""

    async def fake_tv(client, symbols):
        return {
            "AAPL": {
                "close": 100.0,
                "change_pct": 1.0,
                "name": "AAPL",
                "tv_symbol": "NASDAQ:AAPL",
                "source": "tradingview",
            }
        }

    async def fake_single(client, asset, now):
        return AssetQuote(
            symbol=asset["symbol"],
            name=asset["name"],
            asset_class=AssetClass(asset["asset_class"]),
            price=10.0,
            change_pct_24h=0.5,
            change_pct_7d=1.0,
            updated_at=now,
            region="usa",
            region_label="USA",
            live=True,
            quote_source="yahoo",
        )

    monkeypatch.setattr("app.data.tradingview.fetch_tradingview_quotes", fake_tv)
    monkeypatch.setattr("app.data.market_data._fetch_yahoo_quote", fake_single)
    monkeypatch.setattr("app.data.market_data._fetch_coingecko_quote", fake_single)

    quotes = await fetch_quotes(DEFAULT_ASSETS)
    assert len(quotes) == len(DEFAULT_ASSETS)
    assert all(q.price > 0 and q.live for q in quotes)
    sources = {q.quote_source for q in quotes}
    assert "tradingview" in sources
    assert "yahoo" in sources


def test_tv_map_covers_majority_of_catalog():
    mapped = sum(1 for a in DEFAULT_ASSETS if tv_ticker_for(a["symbol"]))
    assert mapped >= 80
    assert tv_ticker_for("BTC-USD") == "BITSTAMP:BTCUSD"
    assert tv_ticker_for("^IBEX") == "TVC:IBEX35"
    assert "^IBEX" in TV_SYMBOL_MAP


@pytest.mark.asyncio
async def test_probe_market_providers_shape(monkeypatch):
    async def fake_probe(client):
        return {"ok": True, "sample": {"close": 1.0}}

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "chart": {"result": [{"meta": {"regularMarketPrice": 1.0}}]},
                "bitcoin": {"usd": 1},
            }

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr("app.data.tradingview.probe_tradingview", fake_probe)
    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    import app.data.market_data as md

    md._PROBE_CACHE = None
    status = await probe_market_providers(force=True)
    assert status["connected"] is True
    assert status["tradingview"]["ok"] is True

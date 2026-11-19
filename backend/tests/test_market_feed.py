"""Fallback quotes name the source. Mocked HTTP only."""

import pytest

from app.data.market_feed import (
    clear_feed_cache,
    load_fallback_candles,
    market_overview,
    parse_stooq_daily,
    search_symbols,
)
from app.models.schemas import ChartCandle


class _Resp:
    def __init__(self, code: int, payload=None, text: str = ""):
        self.status_code = code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class _Http:
    def __init__(self, routes):
        self.routes = routes
        self.calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, headers=None):
        self.calls.append(url)
        for needle, response in self.routes:
            if needle in url:
                return response
        return _Resp(404, {})


def test_search_maps_the_board():
    hits = {row["symbol"] for row in search_symbols("złoto")}
    assert "GC=F" in hits
    assert search_symbols("us10y")[0]["symbol"] == "^TNX"
    assert search_symbols("wig20")[0]["symbol"] == "WIG20.WA"
    assert any(row["symbol"] == "ETH-USD" for row in search_symbols("ethereum"))


def test_stooq_daily_parser():
    text = "Date,Open,High,Low,Close,Volume\n2024-01-02,10,12,9,11,100\n2024-01-03,11,13,10,12,80\n"
    candles = parse_stooq_daily(text, 10)
    assert len(candles) == 2
    assert candles[-1].close == 12


@pytest.mark.asyncio
async def test_crypto_falls_through_binance_to_coingecko(monkeypatch):
    clear_feed_cache()
    routes = [
        ("binance.com", _Resp(500, {})),
        (
            "coingecko.com",
            _Resp(200, [[1_700_000_000_000, 100, 110, 90, 105]]),
        ),
    ]
    monkeypatch.setattr("app.data.market_feed.httpx.AsyncClient", lambda *args, **kwargs: _Http(routes))
    candles, source, errors = await load_fallback_candles("ETH-USD", "3M")
    assert source == "coingecko"
    assert candles[-1].close == 105
    assert any(item.startswith("binance:") for item in errors)
    assert "coincap" not in source


@pytest.mark.asyncio
async def test_equity_uses_stooq_when_asked(monkeypatch):
    clear_feed_cache()
    csv = "Date,Open,High,Low,Close,Volume\n2024-06-01,180,190,179,188,1000\n"
    monkeypatch.setattr(
        "app.data.market_feed.httpx.AsyncClient",
        lambda *args, **kwargs: _Http([("stooq.com", _Resp(200, text=csv))]),
    )
    candles, source, errors = await load_fallback_candles("AAPL", "3M")
    assert source == "stooq"
    assert candles[-1].close == 188
    assert errors == []


@pytest.mark.asyncio
async def test_overview_names_a_failed_source(monkeypatch):
    clear_feed_cache()

    class _Boom:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return _Resp(503, {}, text="no")

    monkeypatch.setattr("app.data.market_feed.httpx.AsyncClient", _Boom)
    payload = await market_overview()
    assert payload["source_errors"]
    assert all("api_key" not in item.lower() for item in payload["source_errors"])
    assert payload["crypto"]["coins"] == []


@pytest.mark.asyncio
async def test_chart_uses_fallback_when_yahoo_is_empty(monkeypatch):
    from app.data.chart_data import fetch_chart

    async def empty(*_args, **_kwargs):
        return [], None

    async def fallback(symbol, preset, client=None):
        return [ChartCandle(time=1, open=1, high=2, low=0.5, close=1.5)], "binance", ["yahoo: empty chart"]

    monkeypatch.setattr("app.data.chart_data._fetch_yahoo_candles", empty)
    monkeypatch.setattr("app.data.chart_data.load_fallback_candles", fallback)
    chart = await fetch_chart("ETH-USD", "3M")
    assert chart is not None
    assert chart.source == "binance"
    assert chart.candles[-1].close == 1.5
    assert "yahoo: empty chart" in chart.source_errors

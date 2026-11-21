"""Bid/ask must come from a real order book — never an invented spread."""

import asyncio

from app.data import orderbook


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload, *_a, **_kw):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def get(self, *_a, **_kw):
        return _Resp(self._payload)


def _patch_client(monkeypatch, payload):
    monkeypatch.setattr(orderbook.httpx, "AsyncClient", lambda *a, **kw: _Client(payload))


def test_yahoo_without_published_bbo_is_brak_danych(monkeypatch):
    _patch_client(monkeypatch, {"chart": {"result": [{"meta": {"regularMarketPrice": 100.0}}]}})
    assert asyncio.run(orderbook.fetch_yahoo_bid_ask("SPY")) is None


def test_yahoo_with_real_bbo(monkeypatch):
    _patch_client(monkeypatch, {"chart": {"result": [{"meta": {"bid": 99.9, "ask": 100.1}}]}})
    book = asyncio.run(orderbook.fetch_yahoo_bid_ask("SPY"))
    assert book["source"] == "yahoo"
    assert book["bid"] == 99.9 and book["ask"] == 100.1


def test_crypto_falls_back_to_coinbase_when_binance_blocked(monkeypatch):
    async def no_binance(_s):
        return None

    async def no_yahoo(_s):
        raise AssertionError("Yahoo should not be needed when Coinbase answers")

    monkeypatch.setattr(orderbook, "fetch_binance_book", no_binance)
    monkeypatch.setattr(orderbook, "fetch_yahoo_bid_ask", no_yahoo)
    _patch_client(monkeypatch, {"bid": "55800.10", "ask": "55800.50", "price": "55800.3"})
    book = asyncio.run(orderbook.fetch_bid_ask("BTC-USD", "crypto"))
    assert book["source"] == "coinbase"
    assert book["bid"] == 55800.10 and book["ask"] == 55800.50

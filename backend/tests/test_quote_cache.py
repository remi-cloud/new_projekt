"""Quote cache always returns full catalog with TTL refresh."""

import pytest

from app.data.assets import DEFAULT_ASSETS
from app.data.quote_cache import QuoteCache
from app.models.schemas import AssetClass, AssetQuote
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_quote_cache_returns_full_catalog(monkeypatch):
    cache = QuoteCache()

    async def fake_fetch(assets):
        now = datetime.now(timezone.utc)
        return [
            AssetQuote(
                symbol=a["symbol"],
                name=a["name"],
                asset_class=AssetClass(a["asset_class"]),
                price=100.0,
                change_pct_24h=1.0,
                change_pct_7d=2.0,
                updated_at=now,
                live=True,
                quote_source="yahoo",
            )
            for a in assets
        ]

    monkeypatch.setattr("app.data.quote_cache.fetch_quotes", fake_fetch)
    quotes = await cache.get_catalog_quotes(force=True)
    assert len(quotes) == len(DEFAULT_ASSETS)
    assert all(q.live and q.price > 0 for q in quotes)


@pytest.mark.asyncio
async def test_quote_cache_refreshes_stale(monkeypatch):
    cache = QuoteCache()
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    cache._quotes["AAPL"] = AssetQuote(
        symbol="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        price=1.0,
        updated_at=old,
        live=True,
        quote_source="yahoo",
    )
    calls = {"n": 0}

    async def fake_fetch(assets):
        calls["n"] += 1
        now = datetime.now(timezone.utc)
        return [
            AssetQuote(
                symbol=a["symbol"],
                name=a["name"],
                asset_class=AssetClass(a["asset_class"]),
                price=200.0,
                updated_at=now,
                live=True,
                quote_source="yahoo",
            )
            for a in assets
        ]

    monkeypatch.setattr("app.data.quote_cache.fetch_quotes", fake_fetch)
    quotes = await cache.get_catalog_quotes(force=False)
    aapl = next(q for q in quotes if q.symbol == "AAPL")
    assert aapl.price == 200.0
    assert calls["n"] >= 1

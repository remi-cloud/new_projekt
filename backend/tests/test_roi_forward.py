"""Unit tests for forward projection."""

import asyncio

import pytest

from app.roi.forward import _crypto_phase_at, _sentiment_from_momentum, project_forward


def test_crypto_phases_cover_cycle():
    assert _crypto_phase_at(10)[0] == "bear"
    assert _crypto_phase_at(300)[0] == "accumulation"
    assert _crypto_phase_at(500)[0] == "bull"
    assert _crypto_phase_at(1300)[0] == "distribution"


def test_sentiment_mapping():
    mult, label = _sentiment_from_momentum(80)
    assert mult > 1.0
    assert label == "bullish"
    mult2, label2 = _sentiment_from_momentum(20)
    assert mult2 < 1.0
    assert label2 == "bearish"


@pytest.mark.asyncio
async def test_project_forward_btc_smoke(monkeypatch):
    from app.models.schemas import ChartCandle
    from datetime import datetime, timezone

    candles = []
    base = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp())
    price = 5000.0
    for i in range(260):
        price *= 1.01 if i % 7 else 0.995
        candles.append(
            ChartCandle(
                time=base + i * 7 * 86400,
                open=price,
                high=price * 1.02,
                low=price * 0.98,
                close=price,
            )
        )

    async def fake_hist(symbol, start=None, end=None):
        return candles, datetime(2018, 1, 1, tzinfo=timezone.utc).date(), datetime(2023, 1, 1, tzinfo=timezone.utc).date()

    async def fake_ath():
        return datetime(2021, 11, 10, tzinfo=timezone.utc).date(), 69000.0, price

    monkeypatch.setattr("app.roi.forward.fetch_long_history", fake_hist)
    monkeypatch.setattr("app.roi.forward.fetch_bitcoin_ath", fake_ath)

    result = await project_forward("BTC-USD", 10000, years=10, strategy="buy_hold")
    assert result["mode"] == "forward"
    assert result["years"] == 10
    assert result["final_value"] > 0
    assert result["final_optimistic"] >= result["final_pessimistic"]
    assert len(result["milestones"]) == 10
    assert "sentiment" in result
    assert "current_cycle" in result

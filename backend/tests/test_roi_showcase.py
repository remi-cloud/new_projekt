"""Tests for ROI showcase presets."""

from datetime import date

import pytest

from app.roi.showcase import get_showcase


@pytest.mark.asyncio
async def test_showcase_returns_three_cards(monkeypatch):
    async def fake_calculate_roi(**kwargs):
        return {
            "symbol": kwargs["symbol"],
            "name": kwargs["symbol"],
            "strategy": kwargs["strategy"],
            "amount": kwargs["amount"],
            "invested": kwargs["amount"],
            "final_value": kwargs["amount"] * 2,
            "profit": kwargs["amount"],
            "roi_pct": 100.0,
            "cagr_pct": 7.2,
            "years": 10.0,
            "data_start": "2016-01-01",
            "data_end": date.today().isoformat(),
            "buy_hold": {"roi_pct": 80.0, "cagr_pct": 6.0, "final_value": kwargs["amount"] * 1.8},
        }

    monkeypatch.setattr("app.roi.showcase.calculate_roi", fake_calculate_roi)

    result = await get_showcase(years=10, amount=10000)
    assert result["amount"] == 10000
    assert result["years"] == 10
    assert len(result["cards"]) == 3
    assert result["cards"][0]["featured"] is True
    assert result["cards"][0]["id"] == "btc"
    symbols = {c["symbol"] for c in result["cards"]}
    assert "BTC-USD" in symbols
    assert "^GSPC" in symbols
    assert "GC=F" in symbols

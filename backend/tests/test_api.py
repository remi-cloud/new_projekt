"""Integration tests for FastAPI endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.models.schemas import AssetClass, AssetCycleAssessment, SignalAction


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "scanner_running" in data


def test_chart_presets(client: TestClient):
    r = client.get("/api/markets/chart-presets")
    assert r.status_code == 200
    presets = r.json()
    assert isinstance(presets, list)
    assert "3M" in presets


def test_notifications_status(client: TestClient):
    r = client.get("/api/notifications/status")
    assert r.status_code == 200
    data = r.json()
    assert "settings" in data
    assert "phone" in data["settings"]


def test_ai_status(client: TestClient):
    r = client.get("/api/ai/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "features" in data


def test_macro_news(client: TestClient):
    r = client.get("/api/news/macro?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_news_image_not_found(client: TestClient):
    r = client.get("/api/news/images/nonexistent-id-xyz")
    assert r.status_code == 404


def test_macro_calendar_invalid_month(client: TestClient):
    r = client.get("/api/news/calendar?month=13")
    assert r.status_code == 400


def test_paper_portfolio(client: TestClient):
    r = client.get("/api/paper/portfolio")
    assert r.status_code == 200
    data = r.json()
    assert "cash_pln" in data
    assert "total_equity_pln" in data


def test_dashboard_or_service_unavailable(client: TestClient):
    r = client.get("/api/dashboard")
    assert r.status_code in (200, 503)


def test_scan_trigger(client: TestClient):
    r = client.post("/api/scan")
    assert r.status_code == 200
    data = r.json()
    assert "opportunities_count" in data


def test_roi_showcase(client: TestClient):
    """Mock Yahoo history — live showcase is flaky behind proxies/CI."""
    fake = {
        "amount": 10000,
        "years": 10,
        "cards": [
            {"id": "btc", "symbol": "BTC-USD", "label": "Bitcoin"},
            {"id": "spx", "symbol": "^GSPC", "label": "S&P 500"},
            {"id": "gold", "symbol": "GC=F", "label": "Gold"},
        ],
    }
    with patch("app.roi.showcase.get_showcase", new_callable=AsyncMock, return_value=fake):
        r = client.get("/api/roi/showcase?years=10&amount=10000")
    assert r.status_code == 200
    data = r.json()
    assert data["amount"] == 10000
    assert len(data["cards"]) == 3
    assert data["cards"][0]["id"] == "btc"


def test_market_assessment_known_symbol(client: TestClient):
    """Seed scanner cache — avoid live CoinGecko/Yahoo in unit CI."""
    from app.scanners.opportunity_scanner import scanner

    seeded = AssetCycleAssessment(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        region="global",
        price=50000.0,
        change_pct_24h=1.0,
        change_pct_7d=2.0,
        macro_cycle="bitcoin",
        macro_phase="accumulation",
        price_phase="accumulation",
        drawdown_from_high_pct=20.0,
        signal=SignalAction.BUY,
        confidence=70.0,
        rationale="test seed",
        updated_at=datetime.now(timezone.utc),
    )
    prev = list(scanner.market_assessments)
    scanner.market_assessments = [seeded]
    try:
        r = client.get("/api/markets/assessment/BTC-USD")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "BTC-USD"
        assert data["name"]
    finally:
        scanner.market_assessments = prev


def test_market_assessment_unknown_symbol(client: TestClient):
    with patch("app.api.markets.get_find_by_symbol", new_callable=AsyncMock, return_value=None):
        r = client.get("/api/markets/assessment/NOT-A-REAL-SYMBOL")
    assert r.status_code == 404

"""Integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient


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
    r = client.get("/api/roi/showcase?years=10&amount=10000")
    assert r.status_code == 200
    data = r.json()
    assert data["amount"] == 10000
    assert len(data["cards"]) == 3
    assert data["cards"][0]["id"] == "btc"


def test_market_assessment_known_symbol(client: TestClient):
    r = client.get("/api/markets/assessment/BTC-USD")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "BTC-USD"
    assert data["name"]


def test_market_assessment_unknown_symbol(client: TestClient):
    r = client.get("/api/markets/assessment/NOT-A-REAL-SYMBOL")
    assert r.status_code == 404

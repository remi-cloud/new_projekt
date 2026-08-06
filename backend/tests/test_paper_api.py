"""HTTP paper trading — reset / order / close (isolated tmp DB via conftest)."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.models.schemas import AssetClass, AssetQuote
from app.paper.paper_db import INITIAL_CASH_PLN


def _quote(symbol: str = "AAPL", price: float = 150.0) -> AssetQuote:
    return AssetQuote(
        symbol=symbol,
        name="Apple",
        asset_class=AssetClass.STOCK,
        price=price,
        change_pct_24h=0.0,
        change_pct_7d=0.0,
        currency="USD",
        updated_at=datetime.now(timezone.utc),
    )


def test_paper_portfolio_get(client):
    r = client.get("/api/paper/portfolio")
    assert r.status_code == 200
    data = r.json()
    assert "cash_pln" in data
    assert "total_equity_pln" in data
    assert "positions" in data


def test_paper_reset_to_one_million(client):
    r = client.post("/api/paper/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["cash_pln"] == INITIAL_CASH_PLN
    assert data["initial_cash_pln"] == INITIAL_CASH_PLN
    assert data["positions_count"] == 0
    assert data["positions"] == []


def test_paper_order_then_close(client):
    client.post("/api/paper/reset")
    quote = _quote()

    with patch("app.paper.pricing.scanner") as mock_scanner, patch(
        "app.paper.executor.get_usd_pln_rate", return_value=4.0
    ), patch("app.paper.portfolio_service.get_usd_pln_rate", return_value=4.0):
        mock_scanner.quotes = [quote]
        # Also used by build_portfolio mark-to-market
        mock_scanner.get_quote = lambda sym: quote if sym == "AAPL" else None

        buy = client.post(
            "/api/paper/order",
            json={"symbol": "AAPL", "side": "buy", "quantity": 2.0, "order_type": "market"},
        )
        assert buy.status_code == 200, buy.text
        body = buy.json()
        assert body["status"] == "filled"
        assert body["portfolio"]["positions_count"] == 1
        assert body["portfolio"]["cash_pln"] < INITIAL_CASH_PLN

        port = client.get("/api/paper/portfolio").json()
        assert port["positions_count"] == 1
        assert port["positions"][0]["symbol"] == "AAPL"

        close = client.post("/api/paper/close/AAPL", json={"percent": 100})
        assert close.status_code == 200, close.text
        after = close.json()["portfolio"]
        assert after["positions_count"] == 0


def test_ai_chat_empty_rejected(client):
    r = client.post("/api/ai/chat", json={"message": "   "})
    assert r.status_code == 400

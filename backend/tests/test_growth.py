"""Growth funnel API smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_growth_packages(client: TestClient):
    packages = client.get("/api/growth/packages")
    assert packages.status_code == 200
    pkgs = packages.json()
    assert isinstance(pkgs, list) and len(pkgs) >= 1


def test_newsletter_and_watchlist_vote(client: TestClient):
    sub = client.post(
        "/api/growth/newsletter",
        json={"email": "growth-test@example.com", "locale": "en", "source": "pytest"},
    )
    assert sub.status_code == 200
    assert sub.json().get("ok") is True

    vote = client.post(
        "/api/growth/watchlist/vote",
        json={"symbol": "ETH-USD", "name": "Ethereum"},
    )
    assert vote.status_code == 200
    assert vote.json().get("ok") is True
    assert vote.json().get("votes", 0) >= 1


def test_public_live_digest(client: TestClient):
    res = client.get("/api/public/live", params={"lang": "en"})
    assert res.status_code == 200
    data = res.json()
    assert "fetched_at" in data
    assert "watchlist" in data
    assert "news" in data

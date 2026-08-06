"""Superokazje API — mocked scanners (no Yahoo / network)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


def test_super_opportunities_list_mocked(client):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": 0,
        "super_count": 0,
        "long_count": 0,
        "short_count": 0,
        "items": [],
        "supers": [],
        "scanner_last_scan_at": None,
    }
    with patch(
        "app.api.super_opportunities.build_super_opportunities",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        r = client.get("/api/super-opportunities?min_score=0")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_super_opportunity_unknown_symbol(client):
    with patch(
        "app.api.super_opportunities.resolve_opportunity_for_symbol",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = client.get("/api/super-opportunities/NOT_A_REAL_SYM_XYZ")
    assert r.status_code == 404


def test_whale_flows_mocked(client):
    with patch(
        "app.api.super_opportunities.fetch_whale_snapshot",
        new_callable=AsyncMock,
        return_value={},
    ):
        r = client.get("/api/whale-flows")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["items"] == []

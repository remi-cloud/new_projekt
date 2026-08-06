"""API smoke tests for execution endpoints."""

from unittest.mock import AsyncMock, patch


def test_execution_status(client):
    res = client.get("/api/execution/status")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "brokers" in data
    assert len(data["brokers"]) == 4


def test_execution_proposals(client):
    res = client.get("/api/execution/proposals")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_execution_brokers(client):
    res = client.get("/api/execution/brokers")
    assert res.status_code == 200
    ids = {b["broker_id"] for b in res.json()}
    assert ids == {"ibkr", "etoro", "kraken", "nexo"}


def test_purge_agent_positions_only_for_agent_symbols(client):
    with patch(
        "app.paper.cleanup.purge_execution_agent_positions",
        new=AsyncMock(
            return_value={
                "status": "ok",
                "purged": ["BTC-USD"],
                "skipped": [],
                "failed": [],
                "proposal_symbols": ["BTC-USD"],
            }
        ),
    ), patch(
        "app.api.paper.build_portfolio",
        new=AsyncMock(return_value={"positions": [], "cash_pln": 1_000_000.0}),
    ):
        res = client.post("/api/paper/purge-agent-positions")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["purged"] == ["BTC-USD"]
    assert data["skipped"] == []

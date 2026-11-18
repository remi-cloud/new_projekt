"""Forced public refreshes stay cached for a minute."""

from fastapi.testclient import TestClient

from app.read_guard import reset_read_guard


def test_singularity_refresh_is_cached_for_a_minute(client: TestClient, monkeypatch):
    from app.agents.orchestrator import orchestrator

    reset_read_guard()
    calls = {"n": 0}

    async def run():
        calls["n"] += 1
        orchestrator.last_result = {"ready": True}

    monkeypatch.setattr(orchestrator, "run_pipeline", run)
    monkeypatch.setattr(orchestrator, "agent_report", lambda: {"ready": True, "runs": calls["n"]})
    monkeypatch.setattr(orchestrator, "last_result", None)
    first = client.get("/api/singularity", params={"refresh": "true"})
    second = client.get("/api/singularity", params={"refresh": "true"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert second.json().get("refresh_cached") is True
    reset_read_guard()


def test_whale_force_is_cached_for_a_minute(client: TestClient, monkeypatch):
    reset_read_guard()
    calls: list[bool] = []

    async def snap(symbols=None, *, force: bool = False):
        del symbols
        calls.append(force)
        return {"BTC-USD": {"bias": "neutral"}}

    monkeypatch.setattr("app.api.super_opportunities.fetch_whale_snapshot", snap)
    first = client.get("/api/whale-flows", params={"force": "true"})
    second = client.get("/api/whale-flows", params={"force": "true"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls == [True, False]
    assert second.json()["refresh_cached"] is True
    reset_read_guard()


def test_empty_market_scan_is_not_repeated_within_a_minute(client: TestClient, monkeypatch):
    from app.scanners.opportunity_scanner import scanner

    reset_read_guard()
    previous = scanner.market_assessments
    calls = {"n": 0}

    async def scan():
        calls["n"] += 1
        return []

    monkeypatch.setattr(scanner, "scan", scan)
    monkeypatch.setattr(scanner, "market_assessments", [])
    try:
        first = client.get("/api/markets/assessments")
        second = client.get("/api/markets/assessments")
    finally:
        scanner.market_assessments = previous
        reset_read_guard()
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1

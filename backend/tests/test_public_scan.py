"""Guests can refresh the read-only market snapshot; the desk scan stays locked."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_desk_scan_stays_locked_for_guests(client: TestClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    # No desk token -> the state-changing scan is refused.
    assert client.post("/api/scan", headers={"X-Desk-Token": ""}).status_code == 401


def test_public_scan_open_to_guests_returns_fresh_when_recent(client: TestClient, monkeypatch):
    from app.config import settings
    from app.scanners.opportunity_scanner import scanner

    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    # Fresh snapshot -> no background scan scheduled, so no network in tests.
    monkeypatch.setattr(scanner, "last_scan_at", datetime.now(timezone.utc))
    monkeypatch.setattr(scanner, "scan_in_progress", False)

    r = client.post("/api/scan/public", headers={"X-Desk-Token": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["scanned"] is False
    assert body["reason"] == "fresh"
    assert "opportunities_count" in body


def test_public_scan_schedules_when_stale(client: TestClient, monkeypatch):
    from app.config import settings
    from app.scanners.opportunity_scanner import scanner
    import app.api.dashboard as dash

    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    monkeypatch.setattr(scanner, "last_scan_at", datetime.now(timezone.utc) - timedelta(hours=1))
    monkeypatch.setattr(scanner, "scan_in_progress", False)
    monkeypatch.setattr(dash, "_last_public_scan_mono", 0.0)

    scan_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(scanner, "scan", scan_mock)
    monkeypatch.setattr(dash, "save_opportunities", AsyncMock())

    r = client.post("/api/scan/public", headers={"X-Desk-Token": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["scanned"] is True
    assert body["reason"] == "scheduled"
    scan_mock.assert_awaited()


def test_public_scan_respects_cooldown(client: TestClient, monkeypatch):
    from app.config import settings
    from app.scanners.opportunity_scanner import scanner
    import app.api.dashboard as dash
    import time as _time

    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    monkeypatch.setattr(scanner, "last_scan_at", datetime.now(timezone.utc) - timedelta(hours=1))
    monkeypatch.setattr(scanner, "scan_in_progress", False)
    # A public scan just ran -> within cooldown -> no new scan.
    monkeypatch.setattr(dash, "_last_public_scan_mono", _time.monotonic())

    r = client.post("/api/scan/public", headers={"X-Desk-Token": ""})
    assert r.status_code == 200
    assert r.json()["scanned"] is False
    assert r.json()["reason"] == "cooldown"

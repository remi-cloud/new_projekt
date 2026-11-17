"""Desk token closes every state-changing route. Reads stay public."""

from fastapi.testclient import TestClient

from app.config import settings


def test_reads_stay_open_and_writes_need_the_desk_token(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/desk/status").json()["configured"] is True
    assert client.get("/api/social/published").status_code == 200

    missing = client.post("/api/social/posts/1/publish", headers={"X-Desk-Token": ""})
    assert missing.status_code == 401
    wrong = client.post("/api/social/posts/1/publish", headers={"X-Desk-Token": "nie-ten"})
    assert wrong.status_code == 401
    opened = client.post(
        "/api/social/posts/1/publish",
        headers={"X-Desk-Token": "pytest-desk"},
    )
    assert opened.status_code == 409


def test_empty_desk_token_closes_writes(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "desk_token", "")
    assert client.get("/api/desk/status").json()["configured"] is False
    closed = client.post(
        "/api/paper/reset",
        headers={"X-Desk-Token": "pytest-desk"},
    )
    assert closed.status_code == 403
    assert "zamknięte" in closed.json()["detail"].lower()


def test_login_checks_the_token_without_changing_state(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    bad = client.post("/api/desk/login", json={"token": "nie-ten"}, headers={"X-Desk-Token": ""})
    assert bad.status_code == 401
    good = client.post("/api/desk/login", json={"token": "pytest-desk"}, headers={"X-Desk-Token": ""})
    assert good.status_code == 200
    assert good.json()["ok"] is True
    monkeypatch.setattr(settings, "desk_token", "  ")
    shut = client.post("/api/desk/login", json={"token": "pytest-desk"}, headers={"X-Desk-Token": ""})
    assert shut.status_code == 403

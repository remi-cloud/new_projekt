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
    assert "zaloguj" in missing.json()["detail"].lower()
    wrong = client.post("/api/social/posts/1/publish", headers={"X-Desk-Token": "nie-ten"})
    assert wrong.status_code == 401
    assert "zły token" in wrong.json()["detail"].lower()
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
    assert "pytest-desk" not in good.text
    cookie = good.headers.get("set-cookie", "")
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()
    client.cookies.clear()
    monkeypatch.setattr(settings, "desk_token", "  ")
    shut = client.post("/api/desk/login", json={"token": "pytest-desk"}, headers={"X-Desk-Token": ""})
    assert shut.status_code == 403


def test_cookie_session_authorizes_a_write_without_a_header(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    client.cookies.clear()
    login = client.post("/api/desk/login", json={"token": "pytest-desk"}, headers={"X-Desk-Token": ""})
    assert login.status_code == 200
    opened = client.post("/api/social/posts/1/publish", headers={"X-Desk-Token": ""})
    assert opened.status_code == 409
    foreign = client.post(
        "/api/social/posts/1/publish",
        headers={"X-Desk-Token": "pytest-desk", "Origin": "https://evil.example"},
    )
    assert foreign.status_code == 403
    client.cookies.clear()


def test_wrong_token_on_a_write_locks_the_client(client: TestClient, monkeypatch):
    from app.desk_auth import reset_login_guard
    from app.http_guard import _HITS

    reset_login_guard()
    _HITS.clear()
    monkeypatch.setattr(settings, "desk_token", "prawidlowy-token")
    quiet = [
        client.post("/api/paper/reset", headers={"X-Desk-Token": ""}).status_code
        for _ in range(6)
    ]
    assert quiet == [401, 401, 401, 401, 401, 401]
    codes = [
        client.post("/api/paper/reset", headers={"X-Desk-Token": "zly"}).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401, 401, 401, 401, 401]
    assert codes[5] == 429
    opened = client.post("/api/paper/reset", headers={"X-Desk-Token": "prawidlowy-token"})
    assert opened.status_code not in (401, 429)
    reset_login_guard()
    _HITS.clear()

"""Public edge: headers, closed docs, CORS, POST limit."""

from fastapi.testclient import TestClient

from app.config import settings
from app.http_guard import _HITS


def test_security_headers_and_hsts_when_https(client: TestClient):
    response = client.get("/api/health", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "unsafe-inline" not in policy.split("style-src-attr")[0]
    assert "max-age=" in response.headers["strict-transport-security"]


def test_docs_closed_outside_dev(client: TestClient):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_rejects_foreign_origin(client: TestClient):
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.headers.get("access-control-allow-origin") in (None, "")


def test_post_rate_limit(client: TestClient, monkeypatch):
    _HITS.clear()
    monkeypatch.setattr(settings, "post_rate_limit", 2)
    monkeypatch.setattr(settings, "post_rate_window_seconds", 60)
    first = client.post("/api/social/posts/1/publish")
    second = client.post("/api/social/posts/1/publish")
    third = client.post("/api/social/posts/1/publish")
    assert first.status_code == 409
    assert second.status_code == 409
    assert third.status_code == 429
    _HITS.clear()

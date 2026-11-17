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
    assert "sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY=" in policy
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
    monkeypatch.setattr(settings, "trusted_proxies", "")
    first = client.post("/api/social/posts/1/publish")
    second = client.post("/api/social/posts/1/publish")
    third = client.post("/api/social/posts/1/publish")
    assert first.status_code == 409
    assert second.status_code == 409
    assert third.status_code == 429
    _HITS.clear()


def test_forwarded_for_is_ignored_unless_peer_is_trusted(client: TestClient, monkeypatch):
    _HITS.clear()
    monkeypatch.setattr(settings, "post_rate_limit", 2)
    monkeypatch.setattr(settings, "post_rate_window_seconds", 60)
    monkeypatch.setattr(settings, "trusted_proxies", "")
    codes = []
    for spoofed in ("203.0.113.10", "203.0.113.11", "198.51.100.8"):
        response = client.post(
            "/api/social/posts/1/publish",
            headers={"X-Forwarded-For": spoofed},
        )
        codes.append(response.status_code)
    assert codes == [409, 409, 429]
    _HITS.clear()


def test_trusted_proxy_uses_the_rightmost_untrusted_hop(client: TestClient, monkeypatch):
    _HITS.clear()
    monkeypatch.setattr(settings, "post_rate_limit", 2)
    monkeypatch.setattr(settings, "post_rate_window_seconds", 60)
    monkeypatch.setattr(settings, "trusted_proxies", "testclient")
    spoofed_left = []
    for _ in range(3):
        response = client.post(
            "/api/social/posts/1/publish",
            headers={"X-Forwarded-For": "203.0.113.77, 198.51.100.20"},
        )
        spoofed_left.append(response.status_code)
    other = client.post(
        "/api/social/posts/1/publish",
        headers={"X-Forwarded-For": "203.0.113.77, 198.51.100.21"},
    )
    assert spoofed_left == [409, 409, 429]
    assert other.status_code == 409
    _HITS.clear()

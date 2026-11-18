"""Public edge: headers, closed docs, CORS, POST limit."""

from fastapi.testclient import TestClient

from app.config import settings
from app.http_guard import _HITS


def test_security_headers_and_hsts_when_https(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxies", "testclient")
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


def test_spoofed_proto_does_not_enable_hsts(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxies", "")
    response = client.get("/api/health", headers={"X-Forwarded-Proto": "https"})
    assert "strict-transport-security" not in response.headers


def test_https_flag_follows_a_trusted_proxy_only(monkeypatch):
    from starlette.requests import Request

    from app.http_guard import request_is_https

    def make(host: str, proto: str | None, scheme: str = "http") -> Request:
        headers = []
        if proto is not None:
            headers.append((b"x-forwarded-proto", proto.encode()))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": scheme,
            "path": "/api/health",
            "raw_path": b"/api/health",
            "query_string": b"",
            "headers": headers,
            "client": (host, 1234),
            "server": ("test", 80),
        }
        return Request(scope)

    monkeypatch.setattr(settings, "trusted_proxies", "172.16.0.0/12,10.0.0.0/8")
    assert request_is_https(make("172.18.0.4", "https")) is True
    assert request_is_https(make("172.18.0.4", "http")) is False
    assert request_is_https(make("203.0.113.9", "https")) is False
    assert request_is_https(make("203.0.113.9", None, scheme="https")) is True


def test_docs_closed_outside_dev(client: TestClient):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_rejects_foreign_origin(client: TestClient):
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.headers.get("access-control-allow-origin") in (None, "")


def test_put_is_rate_limited(client: TestClient, monkeypatch):
    _HITS.clear()
    monkeypatch.setattr(settings, "post_rate_limit", 2)
    monkeypatch.setattr(settings, "post_rate_window_seconds", 60)
    body = {"phone": "", "sms_enabled": False, "ntfy_enabled": False, "ntfy_topic": ""}
    codes = [client.put("/api/notifications/settings", json=body).status_code for _ in range(3)]
    assert codes[0] != 429
    assert codes[1] != 429
    assert codes[2] == 429
    _HITS.clear()


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

"""Outbound fetches must not reach loopback, private nets, or link-local metadata."""

from urllib.parse import urlparse

import httpx
import pytest

from app.net_guard import public_url_ok, safe_get


def test_private_and_tunnel_urls_are_blocked():
    assert public_url_ok("http://127.0.0.1/latest") is False
    assert public_url_ok("http://169.254.169.254/latest/meta-data") is False
    assert public_url_ok("http://10.1.2.3/") is False
    assert public_url_ok("http://2130706433/") is False
    assert public_url_ok("http://[::1]/") is False
    assert public_url_ok("javascript:alert(1)") is False
    assert public_url_ok("https://user:pass@reuters.com/a") is False
    assert public_url_ok("https://localhost/a") is False
    assert public_url_ok("https://demo.trycloudflare.com/a") is False


@pytest.mark.asyncio
async def test_redirect_to_metadata_is_not_followed(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "news.example":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest"})
        raise AssertionError(str(request.url))

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    def allow(url: str) -> bool:
        return (urlparse(url).hostname or "") == "news.example"

    monkeypatch.setattr("app.net_guard.public_url_ok", allow)
    monkeypatch.setattr("app.net_guard.httpx.AsyncClient", factory)
    assert await safe_get("https://news.example/story", timeout=5) is None


@pytest.mark.asyncio
async def test_image_helper_refuses_metadata():
    from app.news.image_sources import download_image

    assert await download_image("http://169.254.169.254/latest/meta-data") is None

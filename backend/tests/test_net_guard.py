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
async def test_rss_fetch_does_not_call_a_link_local_url():
    from app.news.macro_news import _fetch_one_feed

    class Client:
        async def get(self, url, **kwargs):
            raise AssertionError(url)

    rows = await _fetch_one_feed(Client(), "http://169.254.169.254/rss", "meta", "global")
    assert rows == []


@pytest.mark.asyncio
async def test_post_to_x_does_not_cut_the_source_line(monkeypatch):
    from app.notifications.social_clients import post_to_x

    seen: dict[str, str] = {}

    class Response:
        status_code = 201
        text = ""

        def json(self):
            return {"data": {"id": "77"}}

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers=None, json=None):
            del url, headers
            seen["text"] = json["text"]
            return Response()

    body = (
        "Federal Reserve interest rate decision. " + ("rynek " * 40)
        + "\nŹródło: Reuters\nhttps://www.reuters.com/markets/fed\n— @robi44610 | Kar Digital"
    )
    assert len(body) > 280
    monkeypatch.setattr("app.notifications.social_clients.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.notifications.social_clients.settings.x_api_key", "key")
    monkeypatch.setattr("app.notifications.social_clients.settings.x_api_secret", "secret")
    monkeypatch.setattr("app.notifications.social_clients.settings.x_access_token", "token")
    monkeypatch.setattr("app.notifications.social_clients.settings.x_access_token_secret", "token-secret")
    await post_to_x(body)
    assert seen["text"] == body
    assert "Źródło: Reuters" in seen["text"]


@pytest.mark.asyncio
async def test_image_helper_refuses_metadata():
    from app.news.image_sources import download_image

    assert await download_image("http://169.254.169.254/latest/meta-data") is None

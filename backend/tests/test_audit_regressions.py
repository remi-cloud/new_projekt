"""Regression checks for the Kar Digital audit fixes."""

from __future__ import annotations

import socket
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.desk_auth import reset_login_guard
from app.http_guard import _HITS
from app.http_safety import UnsafeUrlError, assert_public_http_url, guarded_get
from app.query_bounds import bounded_limit


def _item(**kwargs):
    from app.models.schemas import MacroNewsItem

    base = dict(
        id="audit-1",
        title="Fed holds rates as inflation stays sticky",
        summary="The Federal Reserve left interest rates unchanged.",
        url="https://www.reuters.com/markets/fed-holds",
        source="Reuters",
        category="fed",
        impact="high",
        published_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    base.update(kwargs)
    return MacroNewsItem(**base)


def test_negative_limit_is_clamped():
    assert bounded_limit(-1, 100) == 1
    assert bounded_limit(0, 50) == 1
    assert bounded_limit(9, 50) == 9
    assert bounded_limit(500, 100) == 100


@pytest.mark.asyncio
async def test_history_query_does_not_drop_the_sqlite_limit():
    from app.db.database import get_recent_opportunities, init_db
    from app.db.sqlite import db_session

    await init_db()
    async with db_session() as db:
        for index in range(3):
            await db.execute(
                """INSERT INTO opportunities
                   (symbol, name, asset_class, action, confidence, cycle_source,
                    phase, price, rationale, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"AUD{index}",
                    "Audit",
                    "stock",
                    "hold",
                    50,
                    "test",
                    "neutral",
                    1,
                    "audit",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        await db.commit()
    rows = await get_recent_opportunities(-1)
    assert len(rows) == 1


def test_private_and_link_local_urls_are_blocked():
    for url in (
        "http://127.0.0.1/latest/meta-data",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://10.1.1.1/",
        "http://192.168.0.5/",
        "file:///etc/passwd",
    ):
        with pytest.raises(UnsafeUrlError):
            assert_public_http_url(url)


@pytest.mark.asyncio
async def test_redirect_hop_to_loopback_is_blocked(monkeypatch):
    def _public(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _public)

    class _Response:
        def __init__(self, code: int, location: str | None = None):
            self.status_code = code
            self.headers = {"location": location} if location else {}
            self.content = b""

    class _Client:
        def __init__(self):
            self.urls: list[str] = []

        async def get(self, url, follow_redirects=False, **_kwargs):
            assert follow_redirects is False
            self.urls.append(url)
            if len(self.urls) == 1:
                return _Response(302, "http://127.0.0.1/secret")
            return _Response(200)

    client = _Client()
    with pytest.raises(UnsafeUrlError):
        await guarded_get(client, "https://news.example/rss")
    assert client.urls == ["https://news.example/rss"]


@pytest.mark.asyncio
async def test_dry_run_blocks_auto_x_when_domain_and_keys_are_set():
    from app.news.social_db import init_social_db
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as post,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_auto_post", True),
        patch.object(sd.settings, "social_dry_run", True),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
    ):
        result = await sd.run_auto_x([_item()])
    assert result["published"] == 0
    post.assert_not_called()


def test_clip_keeps_source_then_rechecks():
    from app.news.x_auto import assert_post_has_source
    from app.notifications.social_clients import clip_x_text

    long_body = (
        "📰 " + ("Fed holds rates and markets wait for the next sentence. " * 12)
        + "\nŹródło: Reuters\nhttps://www.reuters.com/markets/fed-holds\n— @robi44610 | Kar Digital"
    )
    clipped = clip_x_text(
        long_body,
        "Reuters",
        "https://www.reuters.com/markets/fed-holds",
        280,
    )
    assert len(clipped) <= 280
    assert_post_has_source(clipped, "Reuters", "https://www.reuters.com/markets/fed-holds")
    broken = clip_x_text("x" * 400, "", "", 280)
    with pytest.raises(RuntimeError):
        assert_post_has_source(broken, "Reuters", "https://www.reuters.com/markets/fed-holds")


@pytest.mark.asyncio
async def test_manual_publish_uses_whitelist_and_hourly_cap():
    from app.news.social_db import init_social_db, insert_post
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    body = (
        "Źródło: Reuters\nhttps://www.reuters.com/markets/fed-holds\n"
        "Fed holds\n— @robi44610 | Kar Digital"
    )
    outside_body = (
        "Źródło: Reuters\nhttps://evil.example/story\n"
        "Fed holds\n— @robi44610 | Kar Digital"
    )
    outside = await insert_post(
        platform="x",
        news_id="audit-outside",
        url="https://evil.example/story",
        title="T",
        body=outside_body,
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd, "post_to_x", new_callable=AsyncMock, return_value={"external_id": "1"}),
    ):
        with pytest.raises(RuntimeError, match="białą listą"):
            await sd.publish_post(outside, force=True)
        queued = await insert_post(
            platform="x",
            news_id="audit-third",
            url="https://www.reuters.com/markets/fed-holds",
            title="T",
            body=body,
            source_name="Reuters",
            media_path=None,
            status="ready",
        )
        with (
            patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=2),
            pytest.raises(sd.PublishRateLimited),
        ):
            await sd.publish_post(queued, force=True)


def test_refresh_and_balances_need_the_desk(client: TestClient):
    refresh = client.post("/api/news/macro/refresh", headers={"X-Desk-Token": ""})
    assert refresh.status_code == 401
    balances = client.get("/api/portfolio/binance-sync", headers={"X-Desk-Token": ""})
    assert balances.status_code == 401
    opened = client.get("/api/portfolio/binance-sync", headers={"X-Desk-Token": "pytest-desk"})
    assert opened.status_code == 200


def test_cookie_session_and_correct_login_after_bad_guesses(client: TestClient, monkeypatch):
    reset_login_guard()
    _HITS.clear()
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    codes = [
        client.post("/api/desk/login", json={"token": "zly"}, headers={"X-Desk-Token": ""}).status_code
        for _ in range(5)
    ]
    assert codes == [401, 401, 401, 401, 401]
    good = client.post("/api/desk/login", json={"token": "pytest-desk"}, headers={"X-Desk-Token": ""})
    assert good.status_code == 200
    cookie = good.headers.get("set-cookie", "")
    assert "cyclical_desk_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "pytest-desk" not in cookie
    sent = client.post("/api/social/posts/999999/publish", headers={"X-Desk-Token": ""})
    assert sent.status_code != 401
    reset_login_guard()
    _HITS.clear()


def test_old_external_ai_flag_is_an_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("CYCLICAL_AI_EXTERNAL_ENABLED", raising=False)
    monkeypatch.delenv("CYCLICAL_AI_EXTERNAL", raising=False)
    env = tmp_path / ".env"
    env.write_text("CYCLICAL_AI_EXTERNAL=true\n", encoding="utf-8")
    assert Settings(_env_file=env).ai_external_enabled is True
    env.write_text(
        "CYCLICAL_AI_EXTERNAL=true\nCYCLICAL_AI_EXTERNAL_ENABLED=false\n",
        encoding="utf-8",
    )
    assert Settings(_env_file=env).ai_external_enabled is False


@pytest.mark.asyncio
async def test_ollama_gets_no_bearer_and_status_needs_a_live_probe(client, monkeypatch):
    from app.ai.llm import LlmTarget, _post_once, llm_reachable

    seen: dict = {}

    class _Client:
        async def post(self, url, headers=None, json=None, timeout=None):
            seen["headers"] = headers

            class _Resp:
                status_code = 200

            return _Resp()

    await _post_once(
        _Client(),
        LlmTarget("http://127.0.0.1:11434/v1", "llama3.2", "ollama", "ollama"),
        {"model": "llama3.2"},
        httpx.Timeout(1),
    )
    assert "Authorization" not in seen["headers"]

    class _Down:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            raise httpx.ConnectError("down")

    monkeypatch.setattr("app.ai.llm.httpx.AsyncClient", _Down)
    monkeypatch.setattr(settings, "ai_provider", "xai")
    monkeypatch.setattr(settings, "xai_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    assert await llm_reachable(LlmTarget("http://127.0.0.1:11434/v1", "llama", None, "ollama")) is False
    status = client.get("/api/ai/status")
    assert status.status_code == 200
    assert status.json()["llm_configured"] is False


def test_singularity_refresh_and_whale_force_need_auth_and_throttle(client, monkeypatch):
    from app.agents.orchestrator import orchestrator
    import app.api.singularity as singularity
    import app.api.super_opportunities as whales

    pipeline = AsyncMock()
    monkeypatch.setattr(orchestrator, "run_pipeline", pipeline)
    orchestrator.last_result = None
    singularity._last_refresh = time.monotonic()
    denied = client.get("/api/singularity?refresh=true", headers={"X-Desk-Token": ""})
    assert denied.status_code == 401
    throttled = client.get("/api/singularity?refresh=true", headers={"X-Desk-Token": "pytest-desk"})
    assert throttled.status_code == 429
    pipeline.assert_not_called()

    whale = AsyncMock(return_value={})
    monkeypatch.setattr(whales, "fetch_whale_snapshot", whale)
    whales._last_forced = time.monotonic()
    guest = client.get("/api/whale-flows?force=true", headers={"X-Desk-Token": ""})
    assert guest.status_code == 401
    again = client.get("/api/whale-flows?force=true", headers={"X-Desk-Token": "pytest-desk"})
    assert again.status_code == 429
    assert all(call.kwargs.get("force") is False for call in whale.await_args_list)
    open_read = client.get("/api/whale-flows")
    assert open_read.status_code == 200


@pytest.mark.asyncio
async def test_blocked_launchpads_stay_empty_with_a_clear_status(monkeypatch):
    from app.launch_scout import client_4meme, client_pumpfun

    class _Response:
        status_code = 403

        def json(self):
            return {}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Response()

        async def post(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(client_pumpfun.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(client_4meme.httpx, "AsyncClient", _Client)
    assert await client_pumpfun.fetch_recent_coins() == []
    assert client_pumpfun.source_status()["http"] == 403
    assert "403" in client_pumpfun.source_status()["detail"]
    assert await client_4meme.fetch_recent_tokens() == []
    assert client_4meme.source_status()["http"] == 403
    assert "403" in client_4meme.source_status()["detail"]


def test_neutral_us_weight_is_not_a_high_conviction_read():
    from datetime import date

    from app.cycles.regional_macro import analyze_regional_macro, analyze_us_macro

    us = analyze_us_macro(date(2026, 7, 13))
    forex = analyze_regional_macro("global", "forex", "EURUSD=X", date(2026, 7, 13))
    assert us.phase == "neutral"
    assert us.buy_weight == 0.5
    assert us.base_confidence == 50
    assert forex.buy_weight == 0.5
    assert forex.base_confidence == 50


def test_deploy_auto_x_defaults_match():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    backend = (root / "backend" / "Dockerfile").read_text(encoding="utf-8")
    image = (root / "Dockerfile").read_text(encoding="utf-8")
    example = (root / ".env.example").read_text(encoding="utf-8")
    assert "CYCLICAL_SOCIAL_AUTO_POST:-true" in compose or 'CYCLICAL_SOCIAL_AUTO_POST: "${CYCLICAL_SOCIAL_AUTO_POST:-true}"' in compose
    assert "CYCLICAL_SOCIAL_AUTO_POST=true" in backend
    assert "CYCLICAL_SOCIAL_AUTO_POST=true" in image
    assert "CYCLICAL_SOCIAL_DRY_RUN=true" in example
    assert "CYCLICAL_SOCIAL_AUTO_POST=true" in example
    assert "CYCLICAL_AI_EXTERNAL_ENABLED=false" in example
    assert "httpx2" not in (root / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert "cryptography>=50" in (root / "backend" / "requirements.txt").read_text(encoding="utf-8")

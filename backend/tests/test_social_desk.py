"""Social desk — composer + dry-run API (no external network)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import MacroNewsItem
from app.news.social_composer import compose_linkedin, compose_x
from app.news.social_db import content_key, init_social_db, insert_post


def _item(**kwargs) -> MacroNewsItem:
    base = dict(
        id="news-test-1",
        title="Fed holds rates amid stagflation fears",
        summary="Markets watch Powell for guidance on cuts.",
        url="https://example.com/fed",
        source="TestWire",
        category="fed",
        impact="high",
        published_at=datetime.now(timezone.utc),
        is_curated=False,
    )
    base.update(kwargs)
    return MacroNewsItem(**base)


def test_compose_x_includes_source_within_limit():
    body = compose_x(_item()).body
    assert len(body) <= 500
    assert "Źródło: TestWire" in body
    assert "https://example.com/fed" in body
    assert body.endswith("— @robi44610 | Kar Digital")


def test_compose_linkedin_has_disclaimer():
    li = compose_linkedin(_item()).body
    assert "KAR Digital" in li
    assert len(li) <= 1300


def test_content_key_stable():
    a = content_key("x", "id1", "https://a.com")
    b = content_key("x", "id1", "https://a.com")
    c = content_key("linkedin", "id1", "https://a.com")
    assert a == b
    assert a != c


def test_social_status_shape(client):
    r = client.get("/api/social/status")
    assert r.status_code == 200
    data = r.json()
    for key in ("enabled", "dry_run", "auto_post", "x_configured", "linkedin_configured"):
        assert key in data


def test_desk_session_can_read_decisions(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "internal_api_token", "")
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    denied = client.get("/api/social/decisions")
    assert denied.status_code == 403
    opened = client.get("/api/social/decisions", headers={"X-Desk-Token": "pytest-desk"})
    assert opened.status_code == 200
    assert "decisions" in opened.json()


def test_social_posts_list_is_internal(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "internal_api_token", "desk-test")
    denied = client.get("/api/social/posts?limit=5")
    assert denied.status_code == 403
    opened = client.get("/api/social/posts?limit=5", headers={"X-Internal-Token": "desk-test"})
    assert opened.status_code == 200
    data = opened.json()
    assert "posts" in data
    assert "status" in data
    public = client.get("/api/social/published")
    assert public.status_code == 200


@pytest.mark.asyncio
async def test_pipeline_dry_run_marks_posts_and_does_not_raise():
    """Scheduler queue and auto-pipeline stay soft in dry-run; only the button is hard."""
    from app.news.social_db import init_social_db, list_posts
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    queued_item = _item(id="n-pipe-dry-1")
    auto_item = _item(
        id="n-pipe-auto-1",
        title="Fed holds rates as inflation stays sticky",
        url="https://www.reuters.com/markets/fed-holds-dry",
        source="Reuters",
    )
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as px,
        patch.object(sd, "post_to_linkedin", new_callable=AsyncMock) as pl,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_enabled", True),
        patch.object(sd.settings, "social_dry_run", True),
        patch.object(sd.settings, "social_auto_post", True),
        patch.object(sd.settings, "social_max_per_cycle", 2),
        patch.object(sd.settings, "social_platforms", "x"),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
    ):
        queued = await sd.queue_social_from_news_items([queued_item])
        auto = await sd.run_auto_x([auto_item])
        rows = await list_posts(40)
        queued_rows = [row for row in rows if row["news_id"] == "n-pipe-dry-1"]
        auto_rows = [row for row in rows if row["news_id"] == "n-pipe-auto-1"]
        assert queued_rows
        saved = await sd.publish_post(queued_rows[0]["id"], force=False)
        assert queued["posted"] == 0
    assert queued["queued"] >= 1
    assert auto["published"] == 0
    assert all(row["status"] == "dry_run" for row in queued_rows)
    assert auto_rows == []
    assert saved.get("dry_run") is True
    assert saved["status"] == "dry_run"
    px.assert_not_called()
    pl.assert_not_called()


@pytest.mark.asyncio
async def test_queue_dry_run_no_network():
    from app.notifications import social_dispatcher as sd

    items = [
        _item(id="n-dry-1"),
        _item(id="n-dry-2", title="Curated desk brief", is_curated=True, impact="medium"),
    ]
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as px,
        patch.object(sd, "post_to_linkedin", new_callable=AsyncMock) as pl,
        patch.object(sd.settings, "social_enabled", True),
        patch.object(sd.settings, "social_dry_run", True),
        patch.object(sd.settings, "social_auto_post", False),
        patch.object(sd.settings, "social_max_per_cycle", 2),
    ):
        result = await sd.queue_social_from_news_items(items)
    assert result["queued"] >= 1
    assert result["posted"] == 0
    px.assert_not_called()
    pl.assert_not_called()


@pytest.mark.asyncio
async def test_queue_x_ready_does_not_send():
    from app.news.social_db import list_posts
    from app.notifications import social_dispatcher as sd

    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as px,
        patch.object(sd, "post_to_linkedin", new_callable=AsyncMock) as pl,
        patch.object(sd.settings, "social_enabled", True),
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "social_auto_post", False),
        patch.object(sd.settings, "social_platforms", "x"),
        patch.object(sd.settings, "social_max_per_cycle", 2),
    ):
        result = await sd.queue_social_from_news_items([_item(id="n-ready-x")])
    assert result["posted"] == 0
    assert result["queued"] >= 1
    px.assert_not_called()
    pl.assert_not_called()
    rows = await list_posts(20)
    mine = [row for row in rows if row["news_id"] == "n-ready-x"]
    assert mine
    assert {row["platform"] for row in mine} == {"x"}
    assert all(row["status"] == "ready" for row in mine)


@pytest.mark.asyncio
async def test_publish_dry_run_does_not_call_x(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-uniq-1",
        url="https://www.reuters.com/markets/fed",
        title="T",
        body=(
            "Źródło: Reuters\nhttps://www.reuters.com/markets/fed\n"
            "Fed holds rates\n— @robi44610 | Kar Digital"
        ),
        source_name="Reuters",
        media_path=None,
        status="dry_run",
    )
    with (
        patch.object(sd.settings, "social_dry_run", True),
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as px,
        patch("app.notifications.social_dispatcher.x_configured", return_value=True),
    ):
        r = client.post(f"/api/social/posts/{post_id}/publish")
        with pytest.raises(sd.DryRunPublicationBlocked):
            await sd.publish_post(post_id, force=True)
    assert r.status_code == 409
    assert "próbny" in r.json()["detail"].lower() or "dry-run" in r.json()["detail"].lower()
    px.assert_not_called()


@pytest.mark.asyncio
async def test_publish_force_without_tokens(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-uniq-live",
        url="https://www.reuters.com/markets/fed",
        title="T",
        body=(
            "Źródło: Reuters\nhttps://www.reuters.com/markets/fed\n"
            "Fed holds rates\n— @robi44610 | Kar Digital"
        ),
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch("app.notifications.social_dispatcher.x_configured", return_value=False),
    ):
        r = client.post(f"/api/social/posts/{post_id}/publish")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_publish_rejects_post_without_source(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-no-source",
        url="https://www.reuters.com/markets/fed",
        title="T",
        body="Fed holds rates with no attribution",
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch("app.notifications.social_dispatcher.x_configured", return_value=True),
    ):
        r = client.post(f"/api/social/posts/{post_id}/publish")
    assert r.status_code == 400
    assert "źródł" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_publish_rejects_post_without_author_handle(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-no-handle",
        url="https://www.reuters.com/markets/fed",
        title="T",
        body="Źródło: Reuters\nhttps://www.reuters.com/markets/fed\nFed holds rates",
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch("app.notifications.social_dispatcher.x_configured", return_value=True),
    ):
        r = client.post(f"/api/social/posts/{post_id}/publish")
    assert r.status_code == 400
    assert "robi44610" in r.json()["detail"]


@pytest.mark.asyncio
async def test_published_feed_lists_a_sent_post(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-listed",
        url="https://www.reuters.com/markets/fed",
        title="Federal Reserve interest rate decision",
        body=(
            "Źródło: Reuters\nhttps://www.reuters.com/markets/fed\n"
            "Fed holds rates\n— @robi44610 | Kar Digital"
        ),
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch("app.notifications.social_dispatcher.x_configured", return_value=True),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
        patch.object(sd.social_db, "posted_topic_keys", new_callable=AsyncMock, return_value=set()),
        patch(
            "app.notifications.social_dispatcher.post_to_x",
            new_callable=AsyncMock,
            return_value={"external_id": "1842001"},
        ),
    ):
        sent = client.post(f"/api/social/posts/{post_id}/publish")
    assert sent.status_code == 200
    listed = client.get("/api/social/published").json()["posts"]
    match = next(row for row in listed if row["id"] == post_id)
    assert match["x_post_id"] == "1842001"
    assert match["x_url"] == "https://x.com/i/status/1842001"
    assert "@robi44610" in match["body"]
    assert match["source_name"] == "Reuters"
    assert match["source_url"] == "https://www.reuters.com/markets/fed"
    assert match["published_at"]


@pytest.mark.asyncio
async def test_manual_publish_rejects_a_cold_topic(client):
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-cold",
        url="https://www.reuters.com/markets/quiet",
        title="Quiet session drifts",
        body=(
            "Źródło: Reuters\nhttps://www.reuters.com/markets/quiet\n"
            "Quiet session drifts\n— @robi44610 | Kar Digital"
        ),
        source_name="Reuters",
        media_path=None,
        status="ready",
    )
    with (
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch("app.notifications.social_dispatcher.x_configured", return_value=True),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
        patch.object(sd.social_db, "posted_topic_keys", new_callable=AsyncMock, return_value=set()),
        patch("app.notifications.social_dispatcher.post_to_x", new_callable=AsyncMock) as post,
    ):
        response = client.post(f"/api/social/posts/{post_id}/publish")
    assert response.status_code == 400
    assert "progu" in response.json()["detail"]
    post.assert_not_called()


@pytest.mark.asyncio
async def test_auto_x_does_not_repost_the_same_topic_or_key():
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    now = datetime.now(timezone.utc)
    first = _item(
        id="dup-topic-1",
        title="Federal Reserve interest rate decision",
        summary="The Federal Reserve left interest rates unchanged.",
        url="https://www.reuters.com/markets/fed-1",
        source="Reuters",
        published_at=now,
    )
    second = first.model_copy(update={"id": "dup-topic-2", "url": "https://www.reuters.com/markets/fed-2"})
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock, return_value={"external_id": "9"}) as post,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
        patch.object(sd.social_db, "posted_topic_keys", new_callable=AsyncMock, return_value=set()),
    ):
        result = await sd.run_auto_x([first, second])
    assert result["published"] == 1
    assert post.await_count == 1

    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as again,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
        patch.object(sd.social_db, "posted_topic_keys", new_callable=AsyncMock, return_value=set()),
    ):
        repeat = await sd.run_auto_x([first])
    assert repeat["published"] == 0
    again.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_blocks_auto_x_even_with_domain_and_keys():
    from app.news.social_db import init_social_db
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as post,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_dry_run", True),
        patch.object(sd.settings, "social_auto_post", True),
        patch.object(sd.settings, "public_base_url", "https://kardigital.example"),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
    ):
        result = await sd.run_auto_x(
            [
                _item(
                    id="dry-domain-1",
                    url="https://www.reuters.com/markets/fed-holds-live",
                    source="Reuters",
                )
            ]
        )
    assert result["published"] == 0
    post.assert_not_called()


def test_published_endpoint_has_no_secrets(client):
    r = client.get("/api/social/published")
    assert r.status_code == 200
    body = r.json()
    assert "posts" in body
    assert "webhook" not in r.text.lower()
    assert "api_key" not in r.text.lower()

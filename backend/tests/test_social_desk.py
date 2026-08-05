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


def test_compose_x_under_280():
    body = compose_x(_item()).body
    assert len(body) <= 280
    assert "📰" in body


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


def test_social_posts_list(client):
    r = client.get("/api/social/posts?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "posts" in data
    assert "status" in data


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
async def test_publish_force_without_tokens(client):
    await init_social_db()
    post_id = await insert_post(
        platform="x",
        news_id="force-uniq-1",
        url="https://example.com/force-x",
        title="T",
        body="Dry run body for X publish test",
        media_path=None,
        status="dry_run",
    )
    with patch("app.notifications.social_dispatcher.x_configured", return_value=False):
        r = client.post(f"/api/social/posts/{post_id}/publish")
    assert r.status_code == 400

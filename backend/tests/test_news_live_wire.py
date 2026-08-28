"""Live wire: curated desk essays must not appear in the public news feed."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.models.schemas import MacroNewsItem
from app.news import macro_news as mn


@pytest.mark.asyncio
async def test_refresh_does_not_inject_desk_ideology(monkeypatch):
    monkeypatch.setattr(settings, "news_ideology_boost", False)
    monkeypatch.setattr(settings, "news_pool_limit", 50)
    monkeypatch.setattr(settings, "news_feed_limit", 20)
    monkeypatch.setattr(settings, "news_fresh_hours", 2)
    monkeypatch.setattr(settings, "news_display_max_hours", 1)

    now = datetime.now(timezone.utc)
    sample = [
        {
            "title": "Elon Musk announces Robotaxi timeline",
            "link": "https://example.com/musk-1",
            "summary": "Breaking",
            "source_image_url": None,
            "source": "Elon Musk",
            "default_category": "musk",
            "published_at": now,
        }
    ]

    async def fake_fetch_one(client, url, source, default_category):
        return list(sample) if source == "Elon Musk" else []

    with (
        patch.object(mn, "_fetch_one_feed", side_effect=fake_fetch_one),
        patch.object(mn, "resolve_item_urls", new=AsyncMock(side_effect=lambda items: items)),
        patch.object(mn, "enrich_items", side_effect=lambda items: items),
        patch.object(mn, "enrich_calendar_events", new=AsyncMock(return_value=[])),
        patch.object(mn, "get_upcoming_calendar", return_value=[]),
    ):
        feed, pool = await mn.refresh_macro_news()

    assert all(not (i.title or "").startswith("Desk:") for i in feed.items)
    assert all(not (i.id or "").startswith("desk-ideology-") for i in pool)
    assert all(not i.is_curated for i in feed.items)

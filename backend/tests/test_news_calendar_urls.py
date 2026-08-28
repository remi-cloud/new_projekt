import pytest
from datetime import datetime, timezone

from app.models.schemas import MacroNewsItem
from app.news.google_news_urls import is_unsafe_news_url, resolve_item_urls


@pytest.mark.asyncio
async def test_resolve_item_urls_strips_google_wrappers():
    items = [
        MacroNewsItem(
            id="abc",
            title="Bitcoin hits new high",
            url="https://news.google.com/rss/articles/CBMiabc?oc=5",
            source="Test",
            category="crypto",
            impact="medium",
            published_at=datetime.now(timezone.utc),
            is_curated=False,
        )
    ]
    out = await resolve_item_urls(items)
    assert len(out) == 1
    assert not is_unsafe_news_url(out[0].url)
    assert out[0].url != items[0].url

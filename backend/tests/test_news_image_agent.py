"""Tests for news image agent and sources."""

from datetime import datetime, timezone

import pytest

from app.models.schemas import MacroNewsItem
from app.news import image_agent
from app.news.image_sources import extract_image_from_html, stable_seed


@pytest.fixture
def sample_item() -> MacroNewsItem:
    return MacroNewsItem(
        id="testnews12345678",
        title="Fed holds rates steady as inflation cools",
        summary="The Federal Reserve kept interest rates unchanged at its latest meeting.",
        url="https://example.com/fed",
        source="Test Wire",
        category="fed",
        impact="high",
        published_at=datetime.now(timezone.utc),
        is_curated=False,
        age_minutes=5,
    )


def test_extract_og_image_from_html():
    html = '<html><head><meta property="og:image" content="https://cdn.example.com/photo.jpg"></head></html>'
    assert extract_image_from_html(html) == "https://cdn.example.com/photo.jpg"


def test_render_abstract_hero_no_crash(sample_item: MacroNewsItem):
    raw = image_agent._render_abstract_hero(sample_item)
    assert isinstance(raw, bytes)
    assert len(raw) > 1000


@pytest.mark.asyncio
async def test_generate_for_item_abstract(sample_item: MacroNewsItem, monkeypatch):
    monkeypatch.setattr(image_agent.settings, "news_images_use_dalle", False)

    async def _no_photo(item):
        return None, ""

    monkeypatch.setattr("app.news.image_agent.resolve_photo_bytes", _no_photo)

    path = image_agent.image_file_path(sample_item.id)
    meta = image_agent._meta_path(sample_item.id)
    for p in (path, meta):
        if p.exists():
            p.unlink()

    url = await image_agent.generate_for_item(sample_item)
    assert url == f"/api/news/images/{sample_item.id}"
    assert path.is_file()
    meta_data = image_agent._read_meta(sample_item.id)
    assert meta_data["source"] == "abstract"

    path.unlink()
    meta.unlink()


def test_stable_seed_deterministic():
    assert stable_seed("abc") == stable_seed("abc")
    assert stable_seed("abc") != stable_seed("xyz")

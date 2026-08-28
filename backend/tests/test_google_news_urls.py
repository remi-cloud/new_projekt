import pytest

from app.news.google_news_urls import (
    _normalize_publisher,
    ensure_clickable_url,
    is_google_news_url,
    is_unsafe_news_url,
    search_url_for_title,
)


def test_detect_google_news_wrapper():
    assert is_google_news_url(
        "https://news.google.com/rss/articles/CBMiabc?oc=5"
    )
    assert is_unsafe_news_url(
        "https://news.google.com/rss/articles/CBMiabc?oc=5"
    )
    assert not is_google_news_url("https://www.teslarati.com/foo/")
    assert not is_google_news_url(None)


def test_search_fallback():
    url = search_url_for_title("Trump tariffs stagflation")
    assert url.startswith("https://news.google.com/search?q=")
    assert "Trump" in url or "tariffs" in url


def test_huffpost_amp_path_stripped():
    amp = (
        "https://www.huffpost.com/entry/judge-dismisses-lawsuit-by-elon-musks-x"
        "-challenging-new-york-hate-speech-law_n_6a8f966ae4b0a9d5e57cabac/amp"
    )
    fixed = _normalize_publisher(amp)
    assert fixed.endswith("6a8f966ae4b0a9d5e57cabac")
    assert not fixed.endswith("/amp")
    assert "/amp" not in fixed.split("?")[0]


@pytest.mark.asyncio
async def test_wrapper_without_title_returns_search_not_raw():
    wrapper = "https://news.google.com/rss/articles/CBMiabc?oc=5"
    url = await ensure_clickable_url(wrapper, "")
    assert not is_unsafe_news_url(url)
    assert "news.google.com/search" in url

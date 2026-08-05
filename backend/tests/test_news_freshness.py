from datetime import datetime, timedelta, timezone

from app.news.macro_news import _article_date_from_url, _is_stale_article


def test_url_date_rejects_march_resurfaced():
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    fresh_pub = now - timedelta(minutes=20)
    assert _is_stale_article(
        fresh_pub,
        "https://energynow.com/2026/03/15/old-oil-story/",
        now,
    )
    assert _is_stale_article(
        fresh_pub,
        "https://energynow.com/2026/04/saudi-arabia-february/",
        now,
    )
    assert not _is_stale_article(
        fresh_pub,
        "https://nypost.com/2026/08/03/us-news/trump-deal/",
        now,
    )


def test_missing_pubdate_is_stale():
    now = datetime.now(timezone.utc)
    assert _is_stale_article(None, "https://example.com/x", now)


def test_article_date_from_url():
    assert _article_date_from_url("https://x.com/2026/03/15/foo").isoformat() == "2026-03-15"
    assert _article_date_from_url("https://x.com/2026/04/foo").isoformat() == "2026-04-01"

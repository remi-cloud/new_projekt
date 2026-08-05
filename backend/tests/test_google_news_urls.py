from app.news.google_news_urls import is_google_news_url, search_url_for_title


def test_detect_google_news_wrapper():
    assert is_google_news_url(
        "https://news.google.com/rss/articles/CBMiabc?oc=5"
    )
    assert not is_google_news_url("https://www.teslarati.com/foo/")
    assert not is_google_news_url(None)


def test_search_fallback():
    url = search_url_for_title("Trump tariffs stagflation")
    assert url.startswith("https://news.google.com/search?q=")
    assert "Trump" in url or "tariffs" in url

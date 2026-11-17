from app.news.public_urls import public_site_base, strip_loopback_origin


def test_strip_loopback_news_links():
    assert strip_loopback_origin("http://127.0.0.1:8080/api/news/out/abc") == "/api/news/out/abc"
    assert strip_loopback_origin("http://localhost:8080/news") == "/news"
    assert strip_loopback_origin("https://127.0.0.1:8080") == ""
    assert strip_loopback_origin("https://news.example/a") == "https://news.example/a"
    assert strip_loopback_origin("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/v1"


def test_public_site_base_ignores_loopback(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "public_base_url", "http://127.0.0.1:8080")
    assert public_site_base() == ""
    monkeypatch.setattr(settings, "public_base_url", "https://kardigital.example")
    assert public_site_base() == "https://kardigital.example"

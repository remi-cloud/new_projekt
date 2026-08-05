"""Resolve Google News RSS wrappers to real publisher URLs."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_CACHE: dict[str, str] = {}
_CACHE_MISS = "__MISS__"
_MAX_CACHE = 2000
_SEM = asyncio.Semaphore(6)


def is_google_news_url(url: str | None) -> bool:
    if not url:
        return False
    return "news.google.com/" in url and "/articles/" in url


def search_url_for_title(title: str) -> str:
    q = quote_plus((title or "").strip()[:180] or "markets")
    return f"https://news.google.com/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _normalize_publisher(url: str) -> str:
    # Prefer desktop article over AMP stubs when decoder returns /amp/
    if url.endswith("/amp/") or url.endswith("/amp"):
        return url.rstrip("/").removesuffix("/amp")
    return url


def _decode_sync(url: str) -> str | None:
    try:
        from googlenewsdecoder import new_decoderv1
    except ImportError:
        logger.warning("googlenewsdecoder not installed — cannot unwrap Google News links")
        return None
    try:
        result = new_decoderv1(url)
    except Exception as exc:
        logger.debug("Google News decode failed: %s", exc)
        return None
    if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
        return _normalize_publisher(str(result["decoded_url"]))
    if isinstance(result, str) and result.startswith("http"):
        return _normalize_publisher(result)
    return None


async def resolve_article_url(url: str | None, title: str = "") -> str | None:
    """Return a clickable publisher (or search) URL."""
    if not url:
        return search_url_for_title(title) if title else None
    if not is_google_news_url(url):
        return url

    cached = _CACHE.get(url)
    if cached == _CACHE_MISS:
        return search_url_for_title(title) if title else url
    if cached:
        return cached

    async with _SEM:
        # Double-check after waiting for a slot
        cached = _CACHE.get(url)
        if cached == _CACHE_MISS:
            return search_url_for_title(title) if title else url
        if cached:
            return cached
        decoded = await asyncio.to_thread(_decode_sync, url)

    if decoded:
        _CACHE[url] = decoded
        if len(_CACHE) > _MAX_CACHE:
            for key in list(_CACHE.keys())[:400]:
                _CACHE.pop(key, None)
        return decoded

    _CACHE[url] = _CACHE_MISS
    return search_url_for_title(title) if title else url


async def resolve_item_urls(items: list) -> list:
    """Mutate MacroNewsItem list in place with resolved urls."""
    if not items:
        return items

    async def _one(item):
        resolved = await resolve_article_url(item.url, item.title)
        if resolved and resolved != item.url:
            return item.model_copy(update={"url": resolved})
        if item.url is None and resolved:
            return item.model_copy(update={"url": resolved})
        return item

    return list(await asyncio.gather(*[_one(it) for it in items]))

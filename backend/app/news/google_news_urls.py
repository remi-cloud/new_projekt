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


def is_unsafe_news_url(url: str | None) -> bool:
    """True when URL must not be sent to the browser (RSS wrapper)."""
    return is_google_news_url(url)


def search_url_for_title(title: str) -> str:
    q = quote_plus((title or "").strip()[:180] or "markets")
    return f"https://news.google.com/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _normalize_publisher(url: str) -> str:
    from urllib.parse import urlparse, urlunparse

    if url.endswith("/amp/") or url.endswith("/amp"):
        url = url.rstrip("/").removesuffix("/amp")
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if parts and parts[-1].lower() == "amp":
        parts = parts[:-1]
        url = urlunparse(parsed._replace(path="/" + "/".join(parts)))
    return url


def _looks_like_amp_only(url: str) -> bool:
    lower = url.lower()
    return lower.endswith("/amp") or lower.endswith("/amp/") or "/amp/" in lower


def _search_fallback(title: str = "") -> str:
    return search_url_for_title(title or "markets")


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


async def ensure_clickable_url(url: str | None, title: str = "") -> str:
    """Return a browser-safe URL — never a raw Google RSS wrapper."""
    if not url:
        return _search_fallback(title)

    if not is_google_news_url(url):
        normalized = _normalize_publisher(url)
        if _looks_like_amp_only(normalized):
            return _search_fallback(title)
        return normalized

    cached = _CACHE.get(url)
    if cached == _CACHE_MISS:
        return _search_fallback(title)
    if cached:
        return cached

    async with _SEM:
        cached = _CACHE.get(url)
        if cached == _CACHE_MISS:
            return _search_fallback(title)
        if cached:
            return cached
        decoded = await asyncio.to_thread(_decode_sync, url)

    if decoded:
        decoded = _normalize_publisher(decoded)
        if _looks_like_amp_only(decoded) or is_unsafe_news_url(decoded):
            _CACHE[url] = _CACHE_MISS
            return _search_fallback(title)
        _CACHE[url] = decoded
        if len(_CACHE) > _MAX_CACHE:
            for key in list(_CACHE.keys())[:400]:
                _CACHE.pop(key, None)
        return decoded

    _CACHE[url] = _CACHE_MISS
    return _search_fallback(title)


async def resolve_article_url(url: str | None, title: str = "") -> str | None:
    """Return a clickable publisher (or search) URL."""
    return await ensure_clickable_url(url, title)


async def resolve_item_urls(items: list) -> list:
    """Resolve MacroNewsItem list — never leave Google RSS wrappers on items."""
    if not items:
        return items

    async def _one(item):
        resolved = await ensure_clickable_url(item.url, item.title)
        if resolved != (item.url or ""):
            return item.model_copy(update={"url": resolved})
        if is_unsafe_news_url(item.url):
            return item.model_copy(update={"url": _search_fallback(item.title)})
        return item

    return list(await asyncio.gather(*[_one(it) for it in items]))

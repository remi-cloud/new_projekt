"""Fetch real photos for news items — RSS, og:image, Wikimedia, stock APIs."""

from __future__ import annotations

import hashlib
import logging
import re
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from app.config import settings
from app.models.schemas import MacroNewsCategory, MacroNewsItem

logger = logging.getLogger(__name__)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CyclicalTrader/1.4; +news-images)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_IMAGE_CT = re.compile(r"^image/(jpeg|jpg|png|webp|gif|avif)", re.I)
_OG_IMAGE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_IMAGE_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\']',
    re.I,
)
_IMG_SRC = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)

_CATEGORY_SEARCH: dict[MacroNewsCategory, str] = {
    "fed": "federal reserve building economy",
    "usa": "white house capitol washington politics",
    "macro": "stock market trading floor finance",
    "global": "world economy globe geopolitics",
}


def _is_image_url(url: str) -> bool:
    lower = url.lower()
    if any(ext in lower for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")):
        return True
    return "image" in lower or "photo" in lower or "thumb" in lower


def extract_image_from_html(html: str, base_url: str = "") -> str | None:
    for pat in (_OG_IMAGE, _OG_IMAGE_REV):
        m = pat.search(html)
        if m:
            url = unescape(m.group(1).strip())
            if url.startswith("//"):
                url = "https:" + url
            elif base_url and not url.startswith("http"):
                url = urljoin(base_url, url)
            if url.startswith("http"):
                return url
    for m in _IMG_SRC.finditer(html):
        url = unescape(m.group(1).strip())
        if not url or url.startswith("data:"):
            continue
        if base_url and not url.startswith("http"):
            url = urljoin(base_url, url)
        if url.startswith("http") and _is_image_url(url):
            return url
    return None


def extract_image_from_rss_description(description: str, base_url: str = "") -> str | None:
    if not description:
        return None
    return extract_image_from_html(description, base_url)


async def download_image(url: str, *, max_bytes: int = 6_000_000) -> bytes | None:
    if not url or not url.startswith("http"):
        return None
    try:
        async with httpx.AsyncClient(
            timeout=20,
            headers=HTTP_HEADERS,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if not _IMAGE_CT.match(ct) and not _is_image_url(str(resp.url)):
                return None
            data = resp.content
            if len(data) < 2000 or len(data) > max_bytes:
                return None
            return data
    except Exception as exc:
        logger.debug("Image download failed %s: %s", url[:80], exc)
        return None


async def fetch_og_image(page_url: str) -> bytes | None:
    if not page_url or not page_url.startswith("http"):
        return None
    try:
        async with httpx.AsyncClient(
            timeout=15,
            headers=HTTP_HEADERS,
            follow_redirects=True,
        ) as client:
            resp = await client.get(page_url)
            resp.raise_for_status()
            img_url = extract_image_from_html(resp.text, str(resp.url))
            if not img_url:
                return None
            return await download_image(img_url)
    except Exception as exc:
        logger.debug("og:image fetch failed %s: %s", page_url[:80], exc)
        return None


def _search_terms(item: MacroNewsItem) -> str:
    words = re.findall(r"[A-Za-z0-9]{3,}", item.title or "")
    blob = " ".join(words[:8])
    if len(blob) < 12:
        blob = _CATEGORY_SEARCH.get(item.category, "finance news")
    return blob[:120]


async def fetch_wikimedia_photo(item: MacroNewsItem) -> bytes | None:
    query = _search_terms(item)
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": 5,
        "prop": "pageimages",
        "piprop": "original",
        "pilicense": "any",
    }
    try:
        async with httpx.AsyncClient(timeout=15, headers=HTTP_HEADERS) as client:
            resp = await client.get(api, params=params)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                orig = page.get("original", {})
                src = orig.get("source")
                if src and src.startswith("http"):
                    img = await download_image(src)
                    if img:
                        return img
    except Exception as exc:
        logger.debug("Wikimedia fetch failed for %s: %s", item.id, exc)
    return None


async def fetch_pexels_photo(item: MacroNewsItem) -> bytes | None:
    key = settings.pexels_api_key.strip()
    if not key:
        return None
    query = _search_terms(item)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": 3, "orientation": "landscape"},
                headers={"Authorization": key},
            )
            resp.raise_for_status()
            photos = resp.json().get("photos") or []
            for photo in photos:
                src = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                if src:
                    img = await download_image(src)
                    if img:
                        return img
    except Exception as exc:
        logger.debug("Pexels fetch failed for %s: %s", item.id, exc)
    return None


def _upscale_thumbnail(url: str) -> str:
    if "ichef.bbci.co.uk" in url and "/240/" in url:
        return url.replace("/240/", "/976/")
    return url


async def resolve_photo_bytes(item: MacroNewsItem) -> tuple[bytes | None, str]:
    """Try sources in order; return (bytes, source_label)."""
    if item.source_image_url:
        data = await download_image(_upscale_thumbnail(item.source_image_url))
        if data:
            return data, "rss"

    page_url = item.url or ""
    if page_url and "news.google.com" not in page_url:
        data = await fetch_og_image(page_url)
        if data:
            return data, "og"

    data = await fetch_pexels_photo(item)
    if data:
        return data, "pexels"

    data = await fetch_wikimedia_photo(item)
    if data:
        return data, "wikimedia"

    return None, ""


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)

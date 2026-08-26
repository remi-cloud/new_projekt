"""Binance radar — CZ / listing / Alpha signals via Google News RSS (not a DEX feeder)."""

from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any
import httpx

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 18.0
UA = "CyclicalTrader-LaunchScout/1.0"

_FEEDS = (
    ("cz", "Changpeng+Zhao+OR+CZ+Binance+when:24h"),
    ("cz", "Binance+listing+OR+Binance+Alpha+OR+Binance+Launchpool+when:24h"),
    ("cz", "Binance+meme+OR+Binance+memecoin+when:24h"),
)

_TICKER_RE = re.compile(r"\$([A-Z]{2,12})\b")
_WORD_TICKER_RE = re.compile(
    r"\b(PEPE|DOGE|BONK|WIF|FLOKI|SHIB|MEME|PNUT|MOODENG|TRUMP|FARTCOIN|BOME|MEW|POPCAT)\b",
    re.I,
)


async def fetch_binance_radar(limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for author, q in _FEEDS:
            url = (
                "https://news.google.com/rss/search?"
                f"q={q}&hl=en-US&gl=US&ceid=US:en"
            )
            try:
                resp = await client.get(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
                if resp.status_code >= 400:
                    continue
                items.extend(_parse_rss(resp.text, author=author))
            except Exception as exc:
                logger.debug("Binance radar RSS failed: %s", exc)
    # dedupe by url
    by_url: dict[str, dict] = {}
    for it in items:
        u = it.get("url") or it.get("id")
        if u and u not in by_url:
            by_url[u] = it
    out = sorted(by_url.values(), key=lambda x: int(x.get("ts_unix") or 0), reverse=True)
    return out[: max(1, min(80, limit))]


def _parse_rss(xml_text: str, *, author: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    channel = root.find("channel")
    if channel is None:
        return out
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        text = f"{title}. {re.sub('<[^>]+>', ' ', desc)}"
        ts = _pub_unix(pub)
        wid = hashlib.sha256(f"{author}:{link or title}".encode()).hexdigest()[:24]
        keywords = extract_keywords(text)
        out.append(
            {
                "id": f"radar-{wid}",
                "author": author,
                "text": text[:500],
                "url": link,
                "ts_unix": ts,
                "keywords": keywords,
                "source": "binance_radar",
                "tags": ["binance_radar"],
            }
        )
    return out


def extract_keywords(text: str) -> list[str]:
    found: list[str] = []
    for m in _TICKER_RE.findall(text.upper()):
        found.append(m.lower())
    for m in _WORD_TICKER_RE.findall(text):
        found.append(m.lower())
    low = text.lower()
    for kw in ("listing", "alpha", "launchpool", "meme", "memecoin", "binance"):
        if kw in low:
            found.append(kw)
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for k in found:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _pub_unix(pub: str) -> int:
    if not pub:
        return int(time.time())
    try:
        return int(parsedate_to_datetime(pub).timestamp())
    except (TypeError, ValueError, IndexError):
        return int(time.time())

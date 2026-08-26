"""Elon / CZ meme whisper ingest — RSS always, X timeline when OAuth1 configured."""

from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 18.0
UA = "CyclicalTrader-LaunchScout/1.0"

_CASHTAG = re.compile(r"\$([A-Za-z]{2,12})\b")
_MEME_WORDS = re.compile(
    r"\b(doge|dogecoin|pepe|bonk|wif|floki|shib|meme|memecoin|moon|gm|wagmi|"
    r"pnut|moodeng|trump|fartcoin|bome|mew|popcat|kitty|cat|frog|inu)\b",
    re.I,
)

_RSS_FEEDS: list[tuple[str, str]] = [
    ("elon", "https://news.google.com/rss/search?q=Elon+Musk+(meme+OR+memecoin+OR+DOGE+OR+Dogecoin+OR+crypto)+when:24h&hl=en-US&gl=US&ceid=US:en"),
    ("elon", "https://news.google.com/rss/search?q=Elon+Musk+(pepe+OR+bonk+OR+%22who+owns+the+memes%22)+when:7d&hl=en-US&gl=US&ceid=US:en"),
    ("cz", "https://news.google.com/rss/search?q=Changpeng+Zhao+OR+%22CZ%22+Binance+(meme+OR+listing+OR+Alpha)+when:24h&hl=en-US&gl=US&ceid=US:en"),
]

_X_HANDLES = (("elon", "elonmusk"), ("cz", "cz_binance"))


def whispers_enabled() -> bool:
    return bool(getattr(settings, "meme_whispers_enabled", True))


def x_whispers_enabled() -> bool:
    return bool(getattr(settings, "meme_whispers_x_enabled", True)) and _x_oauth_ready()


def _x_oauth_ready() -> bool:
    return bool(
        getattr(settings, "x_api_key", "")
        and getattr(settings, "x_api_secret", "")
        and getattr(settings, "x_access_token", "")
        and getattr(settings, "x_access_token_secret", "")
    )


def extract_whisper_keywords(text: str) -> list[str]:
    found: list[str] = []
    for m in _CASHTAG.findall(text or ""):
        found.append(m.lower())
    for m in _MEME_WORDS.findall(text or ""):
        found.append(m.lower())
    low = (text or "").lower()
    for kw in ("listing", "alpha", "binance", "pump", "universe"):
        if kw in low:
            found.append(kw)
    seen: set[str] = set()
    out: list[str] = []
    for k in found:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


_NOISE_KWS = frozenset({"meme", "memecoin", "listing", "alpha", "binance", "pump", "universe", "moon", "gm", "wagmi"})


def correlate_whisper_tags(candidate: dict, whispers: list[dict]) -> list[str]:
    """Return tag names to add when whisper keywords hit candidate symbol/name."""
    sym = str(candidate.get("symbol") or "").lower().strip()
    name = str(candidate.get("name") or "").lower()
    blob = f"{sym} {name}"
    tags: list[str] = []
    for w in whispers:
        kws = [str(k).lower() for k in (w.get("keywords") or [])]
        signal_kws = [k for k in kws if k not in _NOISE_KWS and len(k) >= 2]
        if not signal_kws:
            continue
        hit = any(k == sym or (len(k) >= 3 and k in blob) for k in signal_kws)
        if not hit:
            continue
        author = str(w.get("author") or "")
        if author == "elon" and "elon_whisper" not in tags:
            tags.append("elon_whisper")
        if author == "cz":
            if w.get("source") == "binance_radar" or "binance_radar" in (w.get("tags") or []):
                if "binance_radar" not in tags:
                    tags.append("binance_radar")
            elif "cz_whisper" not in tags:
                tags.append("cz_whisper")
    return tags


async def ingest_whispers() -> list[dict[str, Any]]:
    """Fetch RSS (+ optional X) and return normalized whisper dicts."""
    if not whispers_enabled():
        return []
    items: list[dict[str, Any]] = []
    items.extend(await _fetch_rss_whispers())
    if x_whispers_enabled():
        try:
            items.extend(await _fetch_x_whispers())
        except Exception as exc:
            logger.debug("X whisper fetch failed: %s", exc)
    by_id: dict[str, dict] = {}
    for it in items:
        wid = it.get("id")
        if wid and wid not in by_id:
            by_id[wid] = it
    return sorted(by_id.values(), key=lambda x: int(x.get("ts_unix") or 0), reverse=True)


async def _fetch_rss_whispers() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for author, url in _RSS_FEEDS:
            try:
                resp = await client.get(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
                if resp.status_code >= 400:
                    continue
                out.extend(_parse_rss(resp.text, author=author, source="rss"))
            except Exception as exc:
                logger.debug("Whisper RSS failed (%s): %s", author, exc)
    return out


def _parse_rss(xml_text: str, *, author: str, source: str) -> list[dict[str, Any]]:
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
        desc = re.sub("<[^>]+>", " ", item.findtext("description") or "")
        text = f"{title}. {desc}".strip()
        ts = _pub_unix(pub)
        wid = "w-" + hashlib.sha256(f"{author}:{link or title}".encode()).hexdigest()[:22]
        out.append(
            {
                "id": wid,
                "author": author,
                "text": text[:600],
                "url": link,
                "ts_unix": ts,
                "keywords": extract_whisper_keywords(text),
                "source": source,
                "tags": [],
            }
        )
    return out


def _pub_unix(pub: str) -> int:
    if not pub:
        return int(time.time())
    try:
        return int(parsedate_to_datetime(pub).timestamp())
    except (TypeError, ValueError, IndexError):
        return int(time.time())


async def _fetch_x_whispers() -> list[dict[str, Any]]:
    """Best-effort Twitter API v2 user timeline via OAuth1 (same keys as publish)."""
    from app.notifications.social_clients import _oauth1_header

    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for author, handle in _X_HANDLES:
            try:
                lookup = f"https://api.twitter.com/2/users/by/username/{handle}"
                auth = _oauth1_header("GET", lookup)
                r = await client.get(lookup, headers={"Authorization": auth})
                if r.status_code >= 400:
                    logger.debug("X user lookup %s → %s", handle, r.status_code)
                    continue
                uid = (r.json().get("data") or {}).get("id")
                if not uid:
                    continue
                tl = f"https://api.twitter.com/2/users/{uid}/tweets"
                params = {"max_results": "10", "tweet.fields": "created_at,text"}
                # OAuth1 signing with query params
                auth2 = _oauth1_header("GET", tl, params)
                r2 = await client.get(tl, params=params, headers={"Authorization": auth2})
                if r2.status_code >= 400:
                    logger.debug("X timeline %s → %s", handle, r2.status_code)
                    continue
                for tw in r2.json().get("data") or []:
                    if not isinstance(tw, dict):
                        continue
                    text = str(tw.get("text") or "")
                    tid = str(tw.get("id") or "")
                    created = tw.get("created_at")
                    ts = _iso_unix(created)
                    out.append(
                        {
                            "id": f"x-{tid}" if tid else "x-" + hashlib.sha256(text.encode()).hexdigest()[:16],
                            "author": author,
                            "text": text[:600],
                            "url": f"https://x.com/{handle}/status/{tid}" if tid else f"https://x.com/{handle}",
                            "ts_unix": ts,
                            "keywords": extract_whisper_keywords(text),
                            "source": "x",
                            "tags": [],
                        }
                    )
            except Exception as exc:
                logger.debug("X whisper %s failed: %s", handle, exc)
    return out


def _iso_unix(ts: Any) -> int:
    if not ts:
        return int(time.time())
    try:
        from datetime import datetime

        return int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return int(time.time())

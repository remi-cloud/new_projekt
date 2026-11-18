"""X (Twitter) and LinkedIn HTTP clients — live publish only."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import quote

import httpx

from app.config import settings
from app.news.x_auto import X_AUTHOR_FOOTER, assert_post_has_source

logger = logging.getLogger(__name__)


def x_configured() -> bool:
    return bool(
        settings.x_api_key
        and settings.x_api_secret
        and settings.x_access_token
        and settings.x_access_token_secret
    )


def linkedin_configured() -> bool:
    return bool(settings.linkedin_access_token and settings.linkedin_author_urn)


def _pct(s: str) -> str:
    return quote(str(s), safe="~")


def _oauth1_header(method: str, url: str, extra_params: dict[str, str] | None = None) -> str:
    oauth = {
        "oauth_consumer_key": settings.x_api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": settings.x_access_token,
        "oauth_version": "1.0",
    }
    params = {**(extra_params or {}), **oauth}
    base = "&".join(f"{_pct(k)}={_pct(params[k])}" for k in sorted(params))
    sig_base = f"{method.upper()}&{_pct(url)}&{_pct(base)}"
    key = f"{_pct(settings.x_api_secret)}&{_pct(settings.x_access_token_secret)}"
    digest = hmac.new(key.encode(), sig_base.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(digest).decode()
    auth = ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))
    return f"OAuth {auth}"


def clip_x_text(text: str, source_name: str, source_url: str, limit: int = 280) -> str:
    """Shorten the story first and keep the source name, link, and author line."""
    name = (source_name or "").strip()
    url = (source_url or "").strip()
    original = text or ""
    footer_lines: list[str] = []
    if name:
        footer_lines.append(f"Źródło: {name}")
    if url:
        footer_lines.append(url)
    if X_AUTHOR_FOOTER in original:
        footer_lines.append(X_AUTHOR_FOOTER)
    footer = "\n".join(footer_lines)
    fits = (
        len(original) <= limit
        and (not name or name.lower() in original.lower())
        and (not url or url in original)
    )
    if fits:
        return original
    budget = limit - (len(footer) + 1 if footer else 0)
    if budget < 8:
        return original[:limit]
    head = original.split("\n", 1)[0].strip()
    if len(head) > budget:
        head = head[: budget - 1].rstrip() + "…"
    return f"{head}\n{footer}" if footer else head[:limit]


async def post_to_x(text: str, *, source_name: str = "", source_url: str = "") -> dict:
    """POST https://api.twitter.com/2/tweets. Source is re-checked after the cut."""
    if not x_configured():
        raise RuntimeError("X credentials missing")
    clipped = clip_x_text(text, source_name, source_url, 280)
    assert_post_has_source(clipped, source_name, source_url)
    url = "https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": _oauth1_header("POST", url),
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json={"text": clipped})
    if r.status_code >= 400:
        raise RuntimeError(f"X API {r.status_code}: {r.text[:400]}")
    data = r.json()
    tweet_id = (data.get("data") or {}).get("id")
    return {"external_id": str(tweet_id) if tweet_id else None, "raw": data}


async def post_to_linkedin(text: str) -> dict:
    """UGC share via LinkedIn REST API."""
    if not linkedin_configured():
        raise RuntimeError("LinkedIn credentials missing")
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": settings.linkedin_author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[:1300]},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    headers = {
        "Authorization": f"Bearer {settings.linkedin_access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        raise RuntimeError(f"LinkedIn API {r.status_code}: {r.text[:400]}")
    # Rest.li returns id in header or body
    ext = r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id")
    try:
        body = r.json()
        ext = ext or body.get("id")
    except Exception:
        body = {}
    return {"external_id": str(ext) if ext else None, "raw": body}

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


async def post_to_x(text: str) -> dict:
    """POST https://api.twitter.com/2/tweets"""
    if not x_configured():
        raise RuntimeError("X credentials missing")
    url = "https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": _oauth1_header("POST", url),
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json={"text": text[:280]})
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

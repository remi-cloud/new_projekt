"""Four.meme (BNB Chain) launchpad feeder — public token search API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://four.meme/meme-api/v1"
IMG_CDN = "https://static.four.meme"
HTTP_TIMEOUT = 20.0
UA = "CyclicalTrader-LaunchScout/1.0"


def _image_url(img: Any) -> str:
    raw = str(img or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = f"/{raw}"
    return f"{IMG_CDN}{raw}"


async def fetch_recent_tokens(limit: int = 40) -> list[dict]:
    """POST /public/token/search — newest BNB meme launches."""
    body = {
        "type": "NEW",
        "listType": "NOR",
        "pageIndex": 1,
        "pageSize": max(1, min(50, limit)),
        "status": "ALL",
        "sort": "DESC",
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{API_BASE}/public/token/search",
                json=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": UA,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("4meme search failed: %s", exc)
        return []

    rows: list[dict] = []
    if isinstance(data, dict):
        payload = data.get("data")
        if isinstance(payload, list):
            rows = [r for r in payload if isinstance(r, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("list"), list):
            rows = [r for r in payload["list"] if isinstance(r, dict)]
    return rows[: max(1, limit)]


def normalize_4meme_token(row: dict) -> dict[str, Any] | None:
    mint = str(row.get("tokenAddress") or "").strip()
    if not mint:
        return None
    if ":" in mint:
        mint = mint.split(":")[0].strip()
    status = str(row.get("status") or "").upper()
    dex_type = int(row.get("dexType") or 0)
    # Only tokens that left bonding (TRADE / DEX) — PUBLISH has no DexScreener pair
    migrated = status in ("TRADE", "DEX") or dex_type > 0
    if not migrated:
        return None

    symbol = str(row.get("shortName") or row.get("name") or "?").strip()[:32]
    name = str(row.get("name") or symbol).strip()[:80]
    try:
        mc = float(row.get("cap")) if row.get("cap") is not None else None
    except (TypeError, ValueError):
        mc = None
    try:
        price = float(row.get("price")) if row.get("price") is not None else None
    except (TypeError, ValueError):
        price = None
    created = row.get("createDate")
    try:
        created_ms = int(created) if created is not None else None
    except (TypeError, ValueError):
        created_ms = None
    tags = ["4meme", "bnb", "bsc", "migrated", "pancake"]
    img = _image_url(row.get("img"))
    return {
        "candidate_id": f"bsc:{mint}".lower(),
        "mint": mint,
        "symbol": symbol or "?",
        "name": name,
        "chain": "bsc",
        "dex_id": "pancakeswap",
        "pair_address": "",
        "market_cap": mc,
        "liq_usd": None,
        "pair_created_ms": created_ms,
        "url": f"https://four.meme/token/{mint}",
        "price_usd": price,
        "image_url": img,
        "source": "4meme",
        "tags": tags,
        "raw": {"tokenId": row.get("tokenId"), "status": status, "progress": row.get("progress")},
    }

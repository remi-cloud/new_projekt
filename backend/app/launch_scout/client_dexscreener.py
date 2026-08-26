"""DexScreener HTTP client — multi-DEX / multi-chain launch discovery."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DS_BASE = "https://api.dexscreener.com"
HTTP_TIMEOUT = 20.0
UA = "CyclicalTrader-LaunchScout/1.0"


async def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{DS_BASE}{path}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params or {}, headers={"Accept": "application/json", "User-Agent": UA})
        resp.raise_for_status()
        return resp.json()


async def fetch_latest_profiles(limit: int = 40) -> list[dict]:
    data = await _get_json("/token-profiles/latest/v1")
    rows = data if isinstance(data, list) else []
    return [r for r in rows if isinstance(r, dict)][: max(1, limit)]


async def fetch_latest_boosts(limit: int = 40) -> list[dict]:
    data = await _get_json("/token-boosts/latest/v1")
    rows = data if isinstance(data, list) else []
    return [r for r in rows if isinstance(r, dict)][: max(1, limit)]


async def fetch_token_pairs(chain_id: str, token_address: str) -> list[dict]:
    path = f"/tokens/v1/{chain_id}/{token_address}"
    try:
        data = await _get_json(path)
    except Exception as exc:
        logger.debug("DexScreener tokens enrich failed %s/%s: %s", chain_id, token_address[:8], exc)
        return []
    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)]
    if isinstance(data, dict) and "pairs" in data and isinstance(data["pairs"], list):
        return [p for p in data["pairs"] if isinstance(p, dict)]
    return []


MEME_SEARCH_QUERIES = (
    "meme",
    "pepe",
    "doge",
    "pump",
    "bonk",
    "wif",
    "cat",
    "new",
    "launch",
    "bonding",
    "btc",
    "ordinal",
    # Value tickers the desk should not miss (migrated / paid listings)
    "memestock",
    "cate",
    "cash",
    "xst",
    "calas",
)


async def search_pairs(query: str, limit: int = 20) -> list[dict]:
    """GET /latest/dex/search?q=… — multi-DEX pairs matching query."""
    try:
        data = await _get_json("/latest/dex/search", {"q": query})
    except Exception as exc:
        logger.debug("DexScreener search %r failed: %s", query, exc)
        return []
    pairs = []
    if isinstance(data, dict):
        raw = data.get("pairs")
        if isinstance(raw, list):
            pairs = [p for p in raw if isinstance(p, dict)]
    elif isinstance(data, list):
        pairs = [p for p in data if isinstance(p, dict)]
    return pairs[: max(1, min(40, limit))]


async def fetch_meme_search_pairs(limit_per_q: int = 12) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for q in MEME_SEARCH_QUERIES:
        for p in await search_pairs(q, limit=limit_per_q):
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


async def fetch_chain_search_pairs(chain_id: str, queries: tuple[str, ...] | None = None, limit_per_q: int = 10) -> list[dict]:
    """Search + keep only pairs on a given chain (e.g. robinhood, bitcoin)."""
    chain = chain_id.strip().lower()
    qs = queries or ("meme", "new", "launch", "token")
    out: list[dict] = []
    seen: set[str] = set()
    for q in qs:
        for p in await search_pairs(q, limit=limit_per_q):
            if str(p.get("chainId") or "").lower() != chain:
                continue
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


def best_pair(pairs: list[dict]) -> dict | None:
    if not pairs:
        return None
    def _liq(p: dict) -> float:
        liq = p.get("liquidity")
        if isinstance(liq, dict):
            try:
                return float(liq.get("usd") or 0)
            except (TypeError, ValueError):
                return 0.0
        return 0.0
    return max(pairs, key=_liq)


def normalize_pair(
    pair: dict,
    *,
    source: str = "dex",
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    base = pair.get("baseToken") if isinstance(pair.get("baseToken"), dict) else {}
    liq = pair.get("liquidity") if isinstance(pair.get("liquidity"), dict) else {}
    mc = pair.get("marketCap")
    if mc is None:
        mc = pair.get("fdv")
    try:
        mc_f = float(mc) if mc is not None else None
    except (TypeError, ValueError):
        mc_f = None
    try:
        liq_f = float(liq.get("usd")) if liq.get("usd") is not None else None
    except (TypeError, ValueError):
        liq_f = None
    created = pair.get("pairCreatedAt")
    try:
        created_ms = int(created) if created is not None else None
    except (TypeError, ValueError):
        created_ms = None
    mint = str(base.get("address") or pair.get("tokenAddress") or "").strip()
    # Never keep mint:4meme style junk
    if ":" in mint:
        mint = mint.split(":")[0].strip()
    chain = str(pair.get("chainId") or "").strip().lower()
    tags = list(extra_tags or [])
    dex_id = str(pair.get("dexId") or "").strip().lower()
    pair_address = str(pair.get("pairAddress") or "").strip()
    if ":" in pair_address:
        pair_address = pair_address.split(":")[0].strip()

    bonding_dex = dex_id in ("pumpfun", "pump", "4meme", "flap", "flapsh", "moonshot")
    migrated_hint = any(
        h in dex_id
        for h in (
            "raydium",
            "pumpswap",
            "pancake",
            "uniswap",
            "meteora",
            "orca",
            "aerodrome",
            "sushiswap",
        )
    )
    if bonding_dex and not migrated_hint:
        if "bonding" not in tags:
            tags.append("bonding")
    if migrated_hint or (pair_address and liq_f and liq_f > 0 and not bonding_dex):
        if "migrated" not in tags:
            tags.append("migrated")
        tags = [t for t in tags if t != "bonding"]

    if dex_id in ("pumpfun", "pumpswap", "pump"):
        if "pump" not in tags:
            tags.append("pump")
    if mint.lower().endswith("pump") and "pump" not in tags:
        tags.append("pump")
    if "flap" in dex_id and "flap" not in tags:
        tags.append("flap")
    if "pancake" in dex_id and "pancake" not in tags:
        tags.append("pancake")
    if chain == "bsc" and "bsc" not in tags:
        tags.append("bsc")
    info = pair.get("info") if isinstance(pair.get("info"), dict) else {}
    image_url = str(info.get("imageUrl") or info.get("image") or "").strip()
    # DexScreener paid visibility signals
    boosts = pair.get("boosts") if isinstance(pair.get("boosts"), dict) else {}
    try:
        boost_active = int(boosts.get("active") or 0)
    except (TypeError, ValueError):
        boost_active = 0
    if boost_active > 0 or image_url or info.get("header") or info.get("openGraph"):
        if "dex_paid" not in tags:
            tags.append("dex_paid")
        if "profile" not in tags and (image_url or info.get("header")):
            tags.append("profile")

    return {
        "candidate_id": f"{chain}:{mint}".lower() if mint else "",
        "mint": mint,
        "symbol": str(base.get("symbol") or pair.get("symbol") or "?").strip()[:32],
        "name": str(base.get("name") or "").strip()[:80],
        "chain": chain,
        "dex_id": dex_id,
        "pair_address": pair_address,
        "market_cap": mc_f,
        "liq_usd": liq_f,
        "pair_created_ms": created_ms,
        "url": str(pair.get("url") or "").strip(),
        "price_usd": _float(pair.get("priceUsd")),
        "image_url": image_url,
        "source": source,
        "tags": tags,
        "raw": {"dexId": dex_id, "pairAddress": pair.get("pairAddress"), "boosts": boosts},
    }


def normalize_profile_stub(row: dict, *, tag: str) -> dict[str, Any]:
    chain = str(row.get("chainId") or "").strip().lower()
    mint = str(row.get("tokenAddress") or "").strip()
    if ":" in mint:
        mint = mint.split(":")[0].strip()
    tags = [tag, "dex_paid"]
    if tag == "boost":
        tags.append("planned_visibility")
    if tag == "profile":
        tags.append("planned_visibility")
    image_url = str(row.get("icon") or row.get("imageUrl") or "").strip()
    return {
        "candidate_id": f"{chain}:{mint}".lower() if mint else "",
        "mint": mint,
        "symbol": "?",
        "name": "",
        "chain": chain,
        "dex_id": "",
        "pair_address": "",
        "market_cap": None,
        "liq_usd": None,
        "pair_created_ms": None,
        "url": str(row.get("url") or "").strip(),
        "price_usd": None,
        "image_url": image_url,
        "source": "dex",
        "tags": tags,
        "raw": {"profile": True, "dex_paid": True},
    }


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

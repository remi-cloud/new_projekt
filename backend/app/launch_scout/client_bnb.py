"""BNB Chain launchpads via DexScreener — Flap.sh + PancakeSwap early tape."""

from __future__ import annotations

import logging
from typing import Any

from app.launch_scout.client_dexscreener import normalize_pair, search_pairs

logger = logging.getLogger(__name__)

_FLAP_QUERIES = ("flapsh", "flap")
_PANCAKE_QUERIES = ("pancakeswap", "bsc meme", "bnb pepe", "bsc new", "cake meme")


def _is_bsc(pair: dict) -> bool:
    return str(pair.get("chainId") or "").strip().lower() == "bsc"


def _dex_id(pair: dict) -> str:
    return str(pair.get("dexId") or "").strip().lower()


def _is_flap(pair: dict) -> bool:
    d = _dex_id(pair)
    return "flap" in d


def _is_pancake(pair: dict) -> bool:
    d = _dex_id(pair)
    return "pancake" in d


async def fetch_flap_pairs(limit: int = 24) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for q in _FLAP_QUERIES:
        try:
            pairs = await search_pairs(q, limit=30)
        except Exception as exc:
            logger.debug("Flap search %r failed: %s", q, exc)
            continue
        for p in pairs:
            if not _is_bsc(p) or not _is_flap(p):
                continue
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
            if len(out) >= limit:
                return out
    return out


async def fetch_pancake_bsc_pairs(limit: int = 24) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for q in _PANCAKE_QUERIES:
        try:
            pairs = await search_pairs(q, limit=14)
        except Exception as exc:
            logger.debug("Pancake search %r failed: %s", q, exc)
            continue
        for p in pairs:
            if not _is_bsc(p) or not _is_pancake(p):
                continue
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
            if len(out) >= limit:
                return out
    return out


def normalize_bnb_pair(pair: dict, *, kind: str) -> dict[str, Any]:
    """kind: flap | pancake"""
    tags = ["bnb", "bsc"]
    if kind == "flap":
        tags.extend(["flap", "bonding"])
        source = "flap"
    else:
        tags.append("pancake")
        source = "pancake"
    return normalize_pair(pair, source=source, extra_tags=tags)

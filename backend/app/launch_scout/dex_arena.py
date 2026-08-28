"""Dex Arena (P1) — per-DEX boards with whale-weighted opportunity ranking."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from app.launch_scout import db as launch_db
from app.launch_scout.terminal_url import (
    dex_home_url,
    ensure_candidate_urls,
    normalize_dex_lane,
    terminal_url,
)

logger = logging.getLogger(__name__)

_DEFAULT_LANES = "pumpfun,raydium,pancakeswap,flap,4meme,other"


def _enabled() -> bool:
    return bool(getattr(settings, "dex_arena_enabled", True))


def _lanes() -> list[str]:
    raw = str(getattr(settings, "dex_arena_lanes", _DEFAULT_LANES) or _DEFAULT_LANES)
    out = [normalize_dex_lane(p.strip()) for p in raw.split(",") if p.strip()]
    # preserve order, unique
    seen: set[str] = set()
    ordered: list[str] = []
    for lane in out:
        if lane not in seen:
            seen.add(lane)
            ordered.append(lane)
    return ordered or ["other"]


def _top_n() -> int:
    return max(1, min(20, int(getattr(settings, "dex_arena_top_n", 8) or 8)))


def _whale_mint_set(traders: list[dict]) -> dict[str, float]:
    """mint → boost weight from open bags / pump trader activity."""
    weights: dict[str, float] = {}
    for t in traders:
        wallet_score = float(t.get("score") or 0) + 10.0 * int(t.get("buys") or 0)
        rank = int(t.get("rank") or 99)
        rank_boost = max(1.0, 31 - rank)
        for bag in t.get("bags") or []:
            if str(bag.get("status") or "open") == "closed":
                continue
            mint = str(bag.get("mint") or "").strip().lower()
            if not mint:
                continue
            net = abs(float(bag.get("net_usd") or 0))
            w = rank_boost + min(50.0, net / 10.0) + min(30.0, wallet_score / 100.0)
            weights[mint] = max(weights.get(mint, 0.0), w)
        for mint in t.get("mints") or []:
            m = str(mint or "").strip().lower()
            if m:
                weights[m] = max(weights.get(m, 0.0), rank_boost * 0.5)
    return weights


def _candidate_whale_boost(c: dict, whale_mints: dict[str, float]) -> float:
    mint = str(c.get("mint") or "").strip().lower()
    boost = float(whale_mints.get(mint, 0.0))
    tags = {str(t).lower() for t in (c.get("tags") or [])}
    if "pump_trader" in tags:
        boost += 15.0
    if "fomo_bag" in tags:
        boost += 10.0
    return boost


def rank_dex_arena(
    candidates: list[dict],
    *,
    traders: list[dict] | None = None,
    lanes: list[str] | None = None,
    top_n: int | None = None,
) -> dict[str, Any]:
    """Group candidates by DEX lane and rank with whale_boost."""
    lane_order = lanes or _lanes()
    n = top_n if top_n is not None else _top_n()
    whale_mints = _whale_mint_set(traders or [])

    buckets: dict[str, list[dict]] = {lane: [] for lane in lane_order}
    if "other" not in buckets:
        buckets["other"] = []

    for raw in candidates:
        c = ensure_candidate_urls(dict(raw))
        lane = normalize_dex_lane(str(c.get("dex_id") or ""), str(c.get("source") or ""))
        if lane not in buckets:
            # map unknown into other if not an explicit lane
            if lane not in lane_order:
                lane = "other"
            else:
                buckets[lane] = []
        whale_boost = _candidate_whale_boost(c, whale_mints)
        session_boost = float(c.get("session_boost") or 0)
        arena_score = float(c.get("score") or 0) + whale_boost + session_boost
        term = (
            c.get("terminal_url")
            or c.get("url")
            or terminal_url(
                mint=str(c.get("mint") or ""),
                symbol=str(c.get("symbol") or ""),
                chain=str(c.get("chain") or ""),
                pair_address=str(c.get("pair_address") or ""),
                source=str(c.get("source") or c.get("dex_id") or ""),
            )
        )
        entry = {
            "candidate_id": c.get("candidate_id"),
            "mint": c.get("mint"),
            "symbol": c.get("symbol") or "?",
            "chain": c.get("chain") or "solana",
            "dex_id": c.get("dex_id"),
            "tier": c.get("tier"),
            "market_cap": c.get("market_cap"),
            "score": c.get("score"),
            "whale_boost": round(whale_boost, 2),
            "session_boost": round(session_boost, 2),
            "arena_score": round(arena_score, 2),
            "url": term,
            "dex_home_url": c.get("dex_home_url")
            or dex_home_url(str(c.get("dex_id") or ""), str(c.get("chain") or "")),
            "tags": c.get("tags") or [],
            "image_url": c.get("image_url"),
            "whale": whale_boost > 0,
        }
        buckets.setdefault(lane, []).append(entry)

    boards: list[dict] = []
    for lane in lane_order:
        rows = buckets.get(lane) or []
        rows.sort(
            key=lambda x: (
                -float(x.get("arena_score") or 0),
                x.get("market_cap") is None,
                float(x.get("market_cap") or 1e18),
            )
        )
        best = rows[:n]
        chain_hint = "solana"
        if lane in ("pancakeswap", "flap", "4meme"):
            chain_hint = "bsc"
        elif best:
            chain_hint = str(best[0].get("chain") or "solana")
        whale_on_lane = [str(b["mint"]) for b in best if b.get("whale") and b.get("mint")]
        boards.append(
            {
                "dex_id": lane,
                "label": lane,
                "home_url": dex_home_url(lane, chain_hint),
                "candidate_count": len(rows),
                "whale_mints": whale_on_lane[:12],
                "best": best,
            }
        )

    return {
        "ok": True,
        "enabled": _enabled(),
        "brand": "Dex Arena",
        "priority": "P1",
        "lanes": lane_order,
        "top_n": n,
        "whale_mints_tracked": len(whale_mints),
        "boards": boards,
        "note": "Per-DEX best picks weighted by Wallet Scout bags / pump_trader. Educational — not advice.",
    }


async def run_dex_arena(
    *,
    candidates: list[dict] | None = None,
    traders: list[dict] | None = None,
) -> dict[str, Any]:
    """Build arena snapshot; persist JSON for API/coordinator."""
    await launch_db.init_launch_scout_db()
    if not _enabled():
        return {"ok": False, "reason": "disabled", "boards": []}

    if candidates is None:
        candidates = await launch_db.list_candidates(tier=None, limit=200)
    if traders is None:
        traders = await launch_db.list_traders(limit=30)

    result = rank_dex_arena(candidates, traders=traders)
    try:
        await launch_db.set_state("dex_arena_json", json.dumps(result, ensure_ascii=False)[:120_000])
    except Exception as exc:
        logger.debug("dex_arena_json persist failed: %s", exc)
    return result


async def get_dex_arena_snapshot() -> dict[str, Any]:
    """Read-only: prefer last tick JSON, else rebuild."""
    await launch_db.init_launch_scout_db()
    if not _enabled():
        return {"ok": False, "reason": "disabled", "boards": [], "brand": "Dex Arena", "priority": "P1"}
    raw = await launch_db.get_state("dex_arena_json")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("boards") is not None:
                data["ok"] = True
                data["enabled"] = True
                return data
        except json.JSONDecodeError:
            pass
    return await run_dex_arena()


def candidate_matches_dex_filter(c: dict, dex: str) -> bool:
    """True if candidate belongs to requested dex lane or source alias."""
    want = (dex or "").lower().strip()
    if not want or want in ("all", "universe"):
        return True
    lane = normalize_dex_lane(str(c.get("dex_id") or ""), str(c.get("source") or ""))
    tags = {str(t).lower() for t in (c.get("tags") or [])}
    src = str(c.get("source") or "").lower()
    if want == "seed":
        return str(c.get("tier") or "") == "seed"
    if want in ("dex", "universe"):
        return True
    if want == "pump" or want == "pumpfun":
        return lane == "pumpfun" or "pump" in tags or "pump" in src
    if want == "bnb":
        return str(c.get("chain") or "").lower() in ("bsc", "bnb") or lane in (
            "pancakeswap",
            "flap",
            "4meme",
        )
    if want == "top-30" or want == "traders":
        return "pump_trader" in tags
    if want in ("gecko", "geckoterminal"):
        return "gecko" in src or "gecko" in tags
    if want in ("binance", "binance_radar", "radar"):
        return "binance" in src or "radar" in tags
    if want in ("whispers", "whisper"):
        return any(t.startswith("whisper") or t in ("elon", "cz") for t in tags)
    return lane == normalize_dex_lane(want) or want in tags or want in src

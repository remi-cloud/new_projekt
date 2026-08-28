"""Tier + score for low-MC launch candidates."""

from __future__ import annotations

import time
from typing import Any

# DEX ids that mean still on bonding / launchpad (not migrated)
_BONDING_DEX = {
    "pumpfun",
    "pump",
    "4meme",
    "flap",
    "flapsh",
    "moonshot",
    "letsbonk",
}
_MIGRATED_DEX_HINTS = (
    "raydium",
    "pumpswap",
    "pancake",
    "uniswap",
    "meteora",
    "orca",
    "jupiter",
    "aerodrome",
    "sushiswap",
    "traderjoe",
    "virtuals",
)


def mc_tier(
    market_cap: float | None,
    *,
    seed_mc: float = 2_000,
    fresh_mc: float = 100_000,
    early_mc: float = 500_000,
    max_mc: float = 1_000_000,
) -> str | None:
    if market_cap is None or market_cap <= 0:
        return None
    if market_cap >= max_mc:
        return None
    if market_cap < seed_mc:
        return "seed"
    if market_cap < fresh_mc:
        return "fresh"
    if market_cap < early_mc:
        return "early"
    return "watch"


def age_hours(pair_created_ms: int | None, now_ts: int | None = None) -> float | None:
    if not pair_created_ms:
        return None
    now = int(now_ts or time.time())
    created_s = int(pair_created_ms) // 1000 if pair_created_ms > 10_000_000_000 else int(pair_created_ms)
    if created_s <= 0:
        return None
    return max(0.0, (now - created_s) / 3600.0)


TAG_BONUS_CAP = 40.0


def _tag_bonus(tags: list[str]) -> float:
    tag_bonus = 0.0
    tagset = {t.lower() for t in tags}
    if "dex_paid" in tagset:
        tag_bonus += 22.0
    if "migrated" in tagset:
        tag_bonus += 14.0
    if "pump" in tagset:
        tag_bonus += 12.0
    if "boost" in tagset:
        tag_bonus += 8.0
    if "fomo_bag" in tagset:
        tag_bonus += 15.0
    if "pump_trader" in tagset:
        tag_bonus += 16.0
    if "rh_trader" in tagset:
        tag_bonus += 12.0
    if "rh_chain" in tagset:
        tag_bonus += 6.0
    if "profile" in tagset:
        tag_bonus += 5.0
    if "planned_visibility" in tagset:
        tag_bonus += 6.0
    if "gecko" in tagset:
        tag_bonus += 5.0
    if "elon_whisper" in tagset:
        tag_bonus += 18.0
    if "cz_whisper" in tagset:
        tag_bonus += 14.0
    if "binance_radar" in tagset:
        tag_bonus += 12.0
    if "4meme" in tagset:
        tag_bonus += 14.0
    if "flap" in tagset:
        tag_bonus += 14.0
    if "pancake" in tagset:
        tag_bonus += 8.0
    if "value_watch" in tagset:
        tag_bonus += 20.0
    if "session_asia" in tagset or "session_eu" in tagset or "session_us" in tagset:
        tag_bonus += 4.0
    if "bsc" in tagset or "bnb" in tagset:
        tag_bonus += 4.0
    if "bonding" in tagset:
        tag_bonus -= 30.0
    # Cap positive stack; keep bonding penalty uncapped below zero
    if tag_bonus > TAG_BONUS_CAP:
        return TAG_BONUS_CAP
    return tag_bonus


def data_confidence(
    *,
    mint: str | None,
    market_cap: float | None,
    age_h: float | None,
    liq_usd: float | None,
    tags: list[str],
) -> float:
    """0–100 completeness of candidate data (separate from ranking score)."""
    score = 20.0
    if mint:
        score += 20.0
    if market_cap is not None and market_cap > 0:
        score += 20.0
    if age_h is not None:
        score += 15.0
    if liq_usd is not None and liq_usd > 0:
        score += 15.0
    if tags:
        score += min(10.0, 2.0 * len(tags))
    return round(min(100.0, score), 1)


def score_candidate(
    *,
    market_cap: float,
    age_h: float | None,
    liq_usd: float | None,
    tags: list[str],
) -> float:
    """Higher = more interesting for early entry (low MC, young, tagged)."""
    mc_score = max(0.0, 100.0 - min(market_cap, 1_000_000) / 10_000.0)
    if market_cap < 2_000:
        mc_score += 40.0
    elif market_cap < 10_000:
        mc_score += 20.0
    age_score = 0.0
    if age_h is not None:
        if age_h < 6:
            age_score = 35.0
        elif age_h < 24:
            age_score = 25.0
        elif age_h < 72:
            age_score = 12.0
        else:
            age_score = 4.0
    tag_bonus = _tag_bonus(tags)
    liq_bonus = 0.0
    if liq_usd is not None:
        if 1_000 <= liq_usd < 50_000:
            liq_bonus = 8.0
        elif 50_000 <= liq_usd < 250_000:
            liq_bonus = 4.0
    return round(mc_score + age_score + tag_bonus + liq_bonus, 2)


def is_bonding_candidate(
    *,
    source: str,
    dex_id: str,
    tags: list[str],
    pair_address: str = "",
) -> bool:
    tagset = {t.lower() for t in tags}
    if "bonding" in tagset:
        return True
    if "migrated" in tagset:
        return False
    d = (dex_id or "").lower()
    s = (source or "").lower()
    if d in _BONDING_DEX or s in _BONDING_DEX:
        # pumpswap / pancake enrichment means migrated
        if any(h in d for h in _MIGRATED_DEX_HINTS):
            return False
        if pair_address and ":" not in pair_address:
            # Real DS pair address present → treat as listed
            if d not in _BONDING_DEX:
                return False
        return True
    return False


def is_dex_paid(tags: list[str]) -> bool:
    tagset = {t.lower() for t in tags}
    return bool(tagset & {"dex_paid", "boost", "profile"})


def is_migrated_candidate(
    *,
    source: str,
    dex_id: str,
    tags: list[str],
    pair_address: str = "",
    liq_usd: float | None = None,
) -> bool:
    if is_bonding_candidate(source=source, dex_id=dex_id, tags=tags, pair_address=pair_address):
        return False
    tagset = {t.lower() for t in tags}
    if "migrated" in tagset:
        return True
    d = (dex_id or "").lower()
    if any(h in d for h in _MIGRATED_DEX_HINTS):
        return True
    # Listed on DexScreener with real pair + liquidity
    if pair_address and ":" not in pair_address and liq_usd is not None and liq_usd > 0:
        return True
    if source in ("dex", "pancake", "gecko") and liq_usd is not None and liq_usd > 0:
        return True
    return False


def passes_liquidity(
    liq_usd: float | None,
    *,
    min_liq_usd: float,
    source: str,
    tags: list[str],
    market_cap: float | None = None,
    seed_mc: float = 2_000,
    require_migrated: bool = False,
) -> bool:
    """Liquidity gate. When require_migrated, bonding with zero liq is rejected."""
    tagset = {t.lower() for t in tags}
    if require_migrated:
        if liq_usd is None or liq_usd < min_liq_usd:
            return False
        return True
    bonding_sources = {"pump", "4meme", "flap"}
    if source in bonding_sources or "pump" in tagset or "4meme" in tagset or "flap" in tagset or "bonding" in tagset:
        if liq_usd is None or liq_usd <= 0:
            return True
    if market_cap is not None and market_cap < seed_mc:
        return True
    if liq_usd is None:
        return False
    return liq_usd >= min_liq_usd


def finalize_candidate(raw: dict[str, Any], thresholds: dict[str, float | bool]) -> dict[str, Any] | None:
    mc = raw.get("market_cap")
    try:
        mc_f = float(mc) if mc is not None else None
    except (TypeError, ValueError):
        mc_f = None
    seed_mc = float(thresholds.get("seed_mc") or 2_000)
    tier = mc_tier(
        mc_f,
        seed_mc=seed_mc,
        fresh_mc=float(thresholds["fresh_mc"]),
        early_mc=float(thresholds["early_mc"]),
        max_mc=float(thresholds["max_mc"]),
    )
    if not tier or mc_f is None:
        return None
    tags = list(raw.get("tags") or [])
    source = str(raw.get("source") or "dex")
    dex_id = str(raw.get("dex_id") or "")
    pair_address = str(raw.get("pair_address") or "")
    liq = raw.get("liq_usd")
    try:
        liq_f = float(liq) if liq is not None else None
    except (TypeError, ValueError):
        liq_f = None

    require_migrated = bool(thresholds.get("require_migrated", False))
    require_dex_paid = bool(thresholds.get("require_dex_paid", False))

    if require_migrated:
        if not is_migrated_candidate(
            source=source,
            dex_id=dex_id,
            tags=tags,
            pair_address=pair_address,
            liq_usd=liq_f,
        ):
            return None
        if "migrated" not in {t.lower() for t in tags}:
            tags.append("migrated")
    if require_dex_paid and not is_dex_paid(tags):
        return None

    if not passes_liquidity(
        liq_f,
        min_liq_usd=float(thresholds["min_liq_usd"]),
        source=source,
        tags=tags,
        market_cap=mc_f,
        seed_mc=seed_mc,
        require_migrated=require_migrated,
    ):
        return None
    age_h = age_hours(raw.get("pair_created_ms"))
    if tier == "watch" and age_h is not None and age_h < 24 and mc_f < float(thresholds["early_mc"]):
        tier = "early"

    # Session Clock soft tags + boost (does not change Seed/migrated gates)
    session_boost = 0.0
    try:
        from app.cycles.session_clock import session_boost_for_timestamp

        ms = raw.get("pair_created_ms")
        ts = None
        if ms:
            ms_i = int(ms)
            ts = ms_i // 1000 if ms_i > 10_000_000_000 else ms_i
        boost, sess_tags = session_boost_for_timestamp(
            ts,
            hottest_session=str(thresholds.get("session_hottest") or "") or None,
            macro_strongest=str(thresholds.get("session_macro_strongest") or "") or None,
        )
        session_boost = float(boost)
        for t in sess_tags:
            if t not in tags:
                tags.append(t)
    except Exception:
        session_boost = 0.0

    score = score_candidate(market_cap=mc_f, age_h=age_h, liq_usd=liq_f, tags=tags)
    score = round(float(score) + session_boost, 2)
    mint = str(raw.get("mint") or raw.get("token_address") or "")
    confidence = data_confidence(
        mint=mint or None,
        market_cap=mc_f,
        age_h=age_h,
        liq_usd=liq_f,
        tags=tags,
    )
    out = dict(raw)
    out.update(
        {
            "market_cap": mc_f,
            "liq_usd": liq_f,
            "tier": tier,
            "age_hours": round(age_h, 2) if age_h is not None else None,
            "score": score,
            "session_boost": session_boost,
            "confidence": confidence,
            "tags": tags,
            "pair_address": pair_address.split(":")[0] if ":" in pair_address else pair_address,
        }
    )
    return out
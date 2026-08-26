"""Launch Scout / Meme Universe — Seed (~$200) + multi-DEX + Pump/RH traders."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.launch_scout import db as launch_db
from app.launch_scout.client_binance_radar import fetch_binance_radar
from app.launch_scout.client_bnb import fetch_flap_pairs, fetch_pancake_bsc_pairs, normalize_bnb_pair
from app.launch_scout.client_4meme import fetch_recent_tokens as fetch_4meme_tokens, normalize_4meme_token
from app.launch_scout.client_dexscreener import (
    best_pair,
    fetch_chain_search_pairs,
    fetch_latest_boosts,
    fetch_latest_profiles,
    fetch_meme_search_pairs,
    fetch_token_pairs,
    normalize_pair,
    normalize_profile_stub,
    search_pairs,
)
from app.launch_scout.client_geckoterminal import fetch_new_pools, normalize_gecko_pool
from app.launch_scout.client_pump_traders import fetch_top_traders_and_events
from app.launch_scout.client_pumpfun import fetch_recent_coins, normalize_pump_coin
from app.launch_scout.scorer import finalize_candidate
from app.launch_scout.terminal_url import ensure_candidate_urls
from app.launch_scout.whispers import correlate_whisper_tags, ingest_whispers, whispers_enabled
from app.coordinator.link_guard import audit_terminal_urls
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)

_DEFAULT_CHAINS = (
    "solana,base,ethereum,bsc,arbitrum,polygon,avalanche,optimism,blast,tron,sui,bitcoin,robinhood"
)


def _enabled() -> bool:
    return bool(getattr(settings, "launch_scout_enabled", True))


def _thresholds() -> dict:
    return {
        "max_mc": float(getattr(settings, "launch_scout_max_mc", 5_000_000) or 5_000_000),
        "seed_mc": float(getattr(settings, "launch_scout_seed_mc", 2_000) or 2_000),
        "fresh_mc": float(getattr(settings, "launch_scout_fresh_mc", 100_000) or 100_000),
        "early_mc": float(getattr(settings, "launch_scout_early_mc", 500_000) or 500_000),
        "min_liq_usd": float(getattr(settings, "launch_scout_min_liq_usd", 1_000) or 1_000),
        "require_migrated": bool(getattr(settings, "launch_scout_require_migrated", True)),
        "require_dex_paid": bool(getattr(settings, "launch_scout_require_dex_paid", True)),
    }


def _allowed_chains() -> set[str]:
    raw = str(getattr(settings, "launch_scout_chains", _DEFAULT_CHAINS) or _DEFAULT_CHAINS)
    return {c.strip().lower() for c in raw.split(",") if c.strip()}


async def get_launch_status() -> dict[str, Any]:
    await launch_db.init_launch_scout_db()
    last_tick = await launch_db.get_state("last_tick_at")
    last_error = await launch_db.get_state("last_error") or ""
    counts = {
        "all": await launch_db.candidates_count(),
        "seed": await launch_db.candidates_count("seed"),
        "fresh": await launch_db.candidates_count("fresh"),
        "early": await launch_db.candidates_count("early"),
        "watch": await launch_db.candidates_count("watch"),
    }
    return {
        "enabled": _enabled(),
        "flagship": True,
        "brand": "Meme Universe · Launch Scout",
        "tagline": "Who owns the memes owns the universe.",
        "entry_note": "Migrated + DexScreener-paid pairs only — no bonding junk.",
        "interval_seconds": int(getattr(settings, "launch_scout_interval_seconds", 60) or 60),
        "thresholds": _thresholds(),
        "chains": sorted(_allowed_chains()),
        "last_tick_at": last_tick,
        "last_error": last_error or None,
        "counts": counts,
        "whispers_count": await launch_db.whispers_count(),
        "whispers_enabled": whispers_enabled(),
        "traders_count": await launch_db.traders_count(),
        "sources": [
            "dexscreener",
            "geckoterminal",
            "pump.fun",
            "pump_traders",
            "4meme",
            "flap",
            "pancakeswap",
            "robinhood_chain",
            "binance_radar",
            "elon_cz_whispers",
            "fomo_overlay",
            "value_tickers",
        ],
        "note": (
            "Desk filter: post-migration DEX pairs with DexScreener paid visibility "
            "(boost/profile/token info). Bonding 4meme/Pump PUBLISH is excluded. "
            "Broken mint:4meme DexScreener links are sanitized. "
            f"Max MC ${int(_thresholds()['max_mc']):,}."
        ),
    }


async def list_launch_candidates(tier: str | None = None, limit: int = 50) -> list[dict]:
    await launch_db.init_launch_scout_db()
    rows = await launch_db.list_candidates(tier=tier, limit=limit)
    return [ensure_candidate_urls(dict(r)) for r in rows]


async def list_meme_whispers(limit: int = 20) -> list[dict]:
    await launch_db.init_launch_scout_db()
    return await launch_db.list_whispers(limit=limit)


async def list_launch_traders(limit: int = 30) -> list[dict]:
    await launch_db.init_launch_scout_db()
    return await launch_db.list_traders(limit=limit)


async def list_launch_trader_events(limit: int = 40) -> list[dict]:
    await launch_db.init_launch_scout_db()
    return await launch_db.list_trader_events(limit=limit)


async def _fomo_mint_set() -> set[str]:
    try:
        from app.fomo.service import list_fomo_events

        events = await list_fomo_events(limit=80, side="buy")
        return {str(e.get("mint") or "").strip().lower() for e in events if e.get("mint")}
    except Exception:
        return set()


async def _enrich_stub(stub: dict, chains: set[str]) -> dict | None:
    chain = stub.get("chain") or ""
    mint = stub.get("mint") or ""
    if not chain or not mint:
        return None
    if chains and chain not in chains:
        return None
    pairs = await fetch_token_pairs(chain, mint)
    pair = best_pair(pairs)
    if not pair:
        if stub.get("market_cap"):
            return stub
        return None
    tags = list(stub.get("tags") or [])
    enriched = normalize_pair(pair, source=stub.get("source") or "dex", extra_tags=tags)
    if stub.get("url") and not enriched.get("url"):
        enriched["url"] = stub["url"]
    if stub.get("image_url") and not enriched.get("image_url"):
        enriched["image_url"] = stub["image_url"]
    return enriched


async def run_launch_scout_tick() -> dict[str, Any]:
    await launch_db.init_launch_scout_db()
    if not _enabled():
        return {"ok": False, "reason": "disabled"}

    now_iso = datetime.now(timezone.utc).isoformat()
    thresholds = _thresholds()
    chains = _allowed_chains()
    errors: list[str] = []
    stubs: list[dict] = []
    enriched: list[dict] = []
    pump_count = 0
    gecko_count = 0
    search_count = 0
    rh_count = 0
    fourmeme_count = 0
    flap_count = 0
    pancake_count = 0
    whisper_n = 0
    traders_n = 0
    trader_events_n = 0
    pump_trader_mints: set[str] = set()

    # --- Whispers + Binance radar ---
    all_whispers: list[dict] = []
    try:
        all_whispers.extend(await ingest_whispers())
    except Exception as exc:
        errors.append(f"whispers: {exc}")
        logger.warning("Meme whispers failed: %s", exc)
    try:
        radar = await fetch_binance_radar(limit=25)
        for r in radar:
            r.setdefault("tags", ["binance_radar"])
            all_whispers.append(r)
    except Exception as exc:
        errors.append(f"binance_radar: {exc}")
        logger.warning("Binance radar failed: %s", exc)
    if all_whispers:
        try:
            whisper_n = await launch_db.upsert_whispers(all_whispers)
        except Exception as exc:
            errors.append(f"whisper_persist: {exc}")

    # --- Pump top-30 traders (best-effort) ---
    try:
        traders, tevents, pump_trader_mints = await fetch_top_traders_and_events(top_n=30, events_limit=40)
        if traders:
            await launch_db.replace_traders(traders)
            traders_n = len(traders)
        if tevents:
            await launch_db.replace_trader_events(tevents)
            trader_events_n = len(tevents)
            for e in tevents:
                if e.get("mint"):
                    pump_trader_mints.add(str(e["mint"]).lower())
    except Exception as exc:
        errors.append(f"pump_traders: {exc}")
        logger.warning("Pump traders failed: %s", exc)

    # 1) DexScreener profiles + boosts
    try:
        for row in await fetch_latest_profiles(limit=30):
            stubs.append(normalize_profile_stub(row, tag="profile"))
    except Exception as exc:
        errors.append(f"dex_profiles: {exc}")
        logger.warning("Launch Scout profiles failed: %s", exc)

    try:
        for row in await fetch_latest_boosts(limit=30):
            stubs.append(normalize_profile_stub(row, tag="boost"))
    except Exception as exc:
        errors.append(f"dex_boosts: {exc}")
        logger.warning("Launch Scout boosts failed: %s", exc)

    by_id: dict[str, dict] = {}
    for s in stubs:
        cid = s.get("candidate_id") or ""
        if not cid:
            continue
        if cid in by_id:
            by_id[cid]["tags"] = list({*(by_id[cid].get("tags") or []), *(s.get("tags") or [])})
        else:
            by_id[cid] = s

    to_enrich = list(by_id.values())[:24]

    async def _one(stub: dict) -> dict | None:
        try:
            return await _enrich_stub(stub, chains)
        except Exception as exc:
            logger.debug("enrich fail: %s", exc)
            return None

    for r in await asyncio.gather(*[_one(s) for s in to_enrich]):
        if r:
            enriched.append(r)

    # 1b) DexScreener meme / ultra-early search
    try:
        pairs = await fetch_meme_search_pairs(limit_per_q=10)
        for p in pairs:
            n = normalize_pair(p, source="dex", extra_tags=["meme_search"])
            if chains and n.get("chain") not in chains:
                continue
            if n.get("candidate_id"):
                enriched.append(n)
                search_count += 1
    except Exception as exc:
        errors.append(f"dex_search: {exc}")
        logger.warning("Launch Scout meme search failed: %s", exc)

    # 1b2) Explicit value tickers (memestock / cate / cash / …) — do not miss named bags
    try:
        raw_tickers = str(getattr(settings, "launch_scout_value_tickers", "") or "")
        tickers = [t.strip() for t in raw_tickers.replace(";", ",").split(",") if t.strip()]
        for q in tickers[:16]:
            for p in await search_pairs(q, limit=8):
                n = normalize_pair(p, source="dex", extra_tags=["value_watch", "meme_search"])
                if chains and n.get("chain") not in chains:
                    continue
                sym = str(n.get("symbol") or "").lower()
                name = str(n.get("name") or "").lower()
                ql = q.lower()
                if ql not in sym and ql not in name and len(ql) > 2:
                    # keep near-matches from search still (Dex ranks them)
                    pass
                if n.get("candidate_id"):
                    enriched.append(n)
                    search_count += 1
    except Exception as exc:
        errors.append(f"value_tickers: {exc}")
        logger.warning("Launch Scout value ticker search failed: %s", exc)

    # 1c) Robinhood chain early tape
    if not chains or "robinhood" in chains:
        try:
            rh_pairs = await fetch_chain_search_pairs(
                "robinhood",
                queries=("meme", "new", "launch", "token", "crypto"),
                limit_per_q=12,
            )
            for p in rh_pairs:
                n = normalize_pair(p, source="dex", extra_tags=["rh_chain", "rh_trader"])
                if n.get("candidate_id"):
                    enriched.append(n)
                    rh_count += 1
            # Also tag profile stubs already on robinhood
            for c in enriched:
                if c.get("chain") == "robinhood":
                    tags = list(c.get("tags") or [])
                    if "rh_chain" not in tags:
                        tags.append("rh_chain")
                    c["tags"] = tags
        except Exception as exc:
            errors.append(f"robinhood: {exc}")
            logger.warning("Robinhood chain tape failed: %s", exc)

    # 1d) Bitcoin chain (when present on DexScreener)
    if not chains or "bitcoin" in chains:
        try:
            btc_pairs = await fetch_chain_search_pairs(
                "bitcoin",
                queries=("btc", "ordinal", "rune", "meme", "new"),
                limit_per_q=8,
            )
            for p in btc_pairs:
                n = normalize_pair(p, source="dex", extra_tags=["bitcoin"])
                if n.get("candidate_id"):
                    enriched.append(n)
                    search_count += 1
        except Exception as exc:
            errors.append(f"bitcoin: {exc}")
            logger.debug("Bitcoin chain search: %s", exc)

    # 2) GeckoTerminal new pools
    try:
        pools = await fetch_new_pools(per_network=10)
        for row in pools:
            n = normalize_gecko_pool(row)
            if not n:
                continue
            if chains and n.get("chain") not in chains:
                continue
            enriched.append(n)
            gecko_count += 1
    except Exception as exc:
        errors.append(f"gecko: {exc}")
        logger.warning("Launch Scout GeckoTerminal failed: %s", exc)

    # 3) Pump.fun recent coins (prefer Seed-band MC when present)
    try:
        coins = await fetch_recent_coins(limit=60)
        pump_norms: list[dict] = []
        seed_mc = thresholds["seed_mc"]
        for row in coins:
            norm = normalize_pump_coin(row)
            if not norm:
                continue
            if chains and norm["chain"] not in chains:
                continue
            # Skip bonding (not graduated) when desk requires migration
            if thresholds.get("require_migrated") and not bool((norm.get("raw") or {}).get("complete")):
                continue
            pump_norms.append(norm)
        # Prefer ultra-low MC first for enrich budget
        pump_norms.sort(
            key=lambda n: (
                n.get("market_cap") is None,
                float(n.get("market_cap") or 1e18),
            )
        )
        pump_count = len(pump_norms)

        async def _enrich_pump(norm: dict) -> dict:
            try:
                pairs = await fetch_token_pairs("solana", norm["mint"])
                pair = best_pair(pairs)
                if pair:
                    merged = normalize_pair(pair, source="pump", extra_tags=list(norm.get("tags") or []))
                    if not merged.get("url"):
                        merged["url"] = norm.get("url") or ""
                    # Keep pump MC if DS inflated / missing
                    pmc = norm.get("market_cap")
                    if pmc is not None and (merged.get("market_cap") is None or float(pmc) < seed_mc):
                        if merged.get("market_cap") is None or float(pmc) < float(merged.get("market_cap") or 1e18):
                            merged["market_cap"] = pmc
                    return merged
            except Exception:
                pass
            return norm

        enriched.extend(await asyncio.gather(*[_enrich_pump(n) for n in pump_norms[:20]]))
        for n in pump_norms[20:]:
            enriched.append(n)
    except Exception as exc:
        errors.append(f"pump: {exc}")
        logger.warning("Launch Scout pump feeder failed: %s", exc)

    # 3b) BNB Chain — 4meme + Flap + PancakeSwap
    if not chains or "bsc" in chains:
        try:
            for row in await fetch_4meme_tokens(limit=40):
                norm = normalize_4meme_token(row)
                if not norm:
                    continue
                mint = norm.get("mint") or ""
                try:
                    pairs = await fetch_token_pairs("bsc", mint)
                    pair = best_pair(pairs)
                    if pair:
                        merged = normalize_pair(
                            pair,
                            source="4meme",
                            extra_tags=list(norm.get("tags") or []),
                        )
                        if norm.get("image_url") and not merged.get("image_url"):
                            merged["image_url"] = norm["image_url"]
                        if not merged.get("url"):
                            merged["url"] = norm.get("url") or ""
                        pmc = norm.get("market_cap")
                        if pmc is not None and (
                            merged.get("market_cap") is None
                            or float(pmc) < float(merged.get("market_cap") or 1e18)
                        ):
                            merged["market_cap"] = pmc
                        enriched.append(merged)
                        fourmeme_count += 1
                    # No DexScreener pair yet → skip (would produce Token Not Found)
                except Exception:
                    pass
        except Exception as exc:
            errors.append(f"4meme: {exc}")
            logger.warning("4meme feeder failed: %s", exc)

        try:
            # Flap is bonding — only when migrated desk is off
            if not thresholds.get("require_migrated"):
                for p in await fetch_flap_pairs(limit=20):
                    n = normalize_bnb_pair(p, kind="flap")
                    if n.get("candidate_id"):
                        enriched.append(n)
                        flap_count += 1
        except Exception as exc:
            errors.append(f"flap: {exc}")
            logger.warning("Flap feeder failed: %s", exc)

        try:
            for p in await fetch_pancake_bsc_pairs(limit=20):
                n = normalize_bnb_pair(p, kind="pancake")
                if n.get("candidate_id"):
                    enriched.append(n)
                    pancake_count += 1
        except Exception as exc:
            errors.append(f"pancake: {exc}")
            logger.warning("PancakeSwap BSC feeder failed: %s", exc)

    # 4) FOMO + whisper + pump_trader correlate tags
    fomo_mints = await _fomo_mint_set()
    for c in enriched:
        tags = list(c.get("tags") or [])
        mint_l = (c.get("mint") or "").lower()
        if mint_l and mint_l in fomo_mints and "fomo_bag" not in tags:
            tags.append("fomo_bag")
        if mint_l and mint_l in pump_trader_mints and "pump_trader" not in tags:
            tags.append("pump_trader")
        for t in correlate_whisper_tags(c, all_whispers):
            if t not in tags:
                tags.append(t)
        c["tags"] = tags

    # Score + filter
    final: dict[str, dict] = {}
    for raw in enriched:
        if chains and (raw.get("chain") or "") not in chains:
            continue
        done = finalize_candidate(raw, thresholds)
        if not done or not done.get("candidate_id"):
            continue
        cid = done["candidate_id"]
        prev = final.get(cid)
        if prev is None or float(done.get("score") or 0) >= float(prev.get("score") or 0):
            final[cid] = done

    # Sort: Seed first (lowest MC), then score
    rows = sorted(
        final.values(),
        key=lambda x: (
            {"seed": 0, "fresh": 1, "early": 2, "watch": 3}.get(str(x.get("tier")), 9),
            x.get("market_cap") is None,
            float(x.get("market_cap") or 1e18),
            -float(x.get("score") or 0),
        ),
    )
    rows = [ensure_candidate_urls(r) for r in rows]
    link_audit = audit_terminal_urls(rows)
    await launch_db.replace_candidates(rows)

    err_msg = "; ".join(errors)[:500] if errors else ""
    await launch_db.set_state("last_tick_at", now_iso)
    await launch_db.set_state("last_error", err_msg)

    counts = {
        "all": len(rows),
        "seed": sum(1 for r in rows if r.get("tier") == "seed"),
        "fresh": sum(1 for r in rows if r.get("tier") == "fresh"),
        "early": sum(1 for r in rows if r.get("tier") == "early"),
        "watch": sum(1 for r in rows if r.get("tier") == "watch"),
    }
    payload = {
        "counts": counts,
        "whispers": whisper_n,
        "traders": traders_n,
        "seed_sample": [
            {
                "symbol": r.get("symbol"),
                "mc": r.get("market_cap"),
                "chain": r.get("chain"),
                "dex": r.get("dex_id"),
                "tags": r.get("tags"),
            }
            for r in rows
            if r.get("tier") == "seed"
        ][:12],
        "at": now_iso,
        "errors": errors[:5],
        "link_guard": link_audit,
    }
    try:
        await broadcaster.publish("launch_scout_tick", payload)
    except Exception as exc:
        logger.debug("launch_scout_tick publish failed: %s", exc)

    logger.info(
        "Meme Universe tick: total=%d seed=%d fresh=%d pump=%d 4meme=%d flap=%d pancake=%d traders=%d rh=%d errors=%d bad_urls=%d missing_chain=%d",
        counts["all"],
        counts["seed"],
        counts["fresh"],
        pump_count,
        fourmeme_count,
        flap_count,
        pancake_count,
        traders_n,
        rh_count,
        len(errors),
        link_audit.get("bad_4meme", 0),
        link_audit.get("missing_chain_axiom", 0),
    )
    return {
        "ok": True,
        "counts": counts,
        "link_guard": link_audit,
        "pump_seen": pump_count,
        "fourmeme_seen": fourmeme_count,
        "flap_seen": flap_count,
        "pancake_seen": pancake_count,
        "gecko_seen": gecko_count,
        "search_seen": search_count,
        "rh_seen": rh_count,
        "whispers_upserted": whisper_n,
        "traders": traders_n,
        "trader_events": trader_events_n,
        "enriched": len(enriched),
        "errors": errors,
    }

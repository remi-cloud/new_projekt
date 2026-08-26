"""Super-opportunity engine: Academy cycles + entry/exit + bid/ask + liq heatmap."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.data.assets import lookup_asset
from app.data.community_links import resolve_community_links
from app.data.orderbook import (
    estimate_liquidation_heatmap,
    fetch_bid_ask,
    fetch_volume_profile,
)
from app.data.whale_flows import fetch_whale_for_symbol, get_cached_whale
from app.models.schemas import AssetClass, InstrumentCommunity, Opportunity, SignalAction
from app.scanners.ai_trade_advisor import consult_trade_signal
from app.scanners.liq_prediction import predict_liq_path
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)


def _phase_label_for_asset(asset_class: AssetClass) -> tuple[str, SignalAction, float, str, str]:
    """Map catalog asset → (phase, action, confidence, cycle_source, rationale)."""
    if asset_class == AssetClass.CRYPTO and scanner.bitcoin_cycle:
        a = scanner.bitcoin_cycle
        conf = 58.0 if a.signal == SignalAction.WATCH else 62.0
        if a.signal == SignalAction.HOLD:
            conf = 45.0
        return (
            a.phase.value,
            a.signal,
            conf,
            "bitcoin",
            f"Pozycja katalogowa · Cykl Bitcoin ({a.phase.value}): {a.rationale}",
        )
    if scanner.presidential_cycle:
        b = scanner.presidential_cycle
        conf = 58.0 if b.signal == SignalAction.WATCH else 62.0
        if b.signal == SignalAction.HOLD:
            conf = 45.0
        return (
            b.current_year.value,
            b.signal,
            conf,
            "presidential",
            f"Pozycja katalogowa · Cykl prezydencki (rok {b.year_number}): {b.rationale}",
        )
    return (
        "neutral",
        SignalAction.WATCH,
        50.0,
        "catalog",
        "Pozycja z katalogu rynków — brak aktywnego modelu cyklu; tryb obserwacji.",
    )


async def resolve_opportunity_for_symbol(symbol: str) -> Opportunity | None:
    """Return scanned Opportunity or synthesize one from catalog + cycles."""
    sym = symbol.strip().upper()
    match = next((o for o in scanner.opportunities if o.symbol.upper() == sym), None)
    if match:
        return match

    assessment = next(
        (a for a in scanner.market_assessments if a.symbol.upper() == sym),
        None,
    )
    if assessment:
        return scanner._assessment_to_opportunity(assessment, datetime.now(timezone.utc))

    meta = lookup_asset(sym)
    if not meta:
        return None

    price = 0.0
    q = next((x for x in scanner.quotes if x.symbol.upper() == sym), None)
    if q and q.price > 0:
        price = float(q.price)
    if price <= 0:
        book = await fetch_bid_ask(sym, str(meta.get("asset_class", "index")))
        if book and book.get("mid"):
            price = float(book["mid"])
    if price <= 0:
        return None

    asset_class = AssetClass(meta["asset_class"])
    phase, action, confidence, source, rationale = _phase_label_for_asset(asset_class)

    return Opportunity(
        symbol=meta["symbol"],
        name=meta["name"],
        asset_class=asset_class,
        action=action,
        confidence=confidence,
        cycle_source=source,
        phase=phase,
        price=price,
        rationale=rationale,
        created_at=datetime.now(timezone.utc),
        community=InstrumentCommunity(**resolve_community_links(meta["symbol"], meta["name"])),
    )


def _structure_atr_pct(price: float, heatmap: dict) -> float:
    """ATR-like % from liquidation heatmap span — independent of cycle confidence."""
    if price <= 0:
        return 0.015
    bins = heatmap.get("bins") or []
    if len(bins) >= 2:
        prices = [float(b["price"]) for b in bins if b.get("price")]
        if len(prices) >= 2:
            span = (max(prices) - min(prices)) / price
            # ~1/6 of structure span; clamp 0.8%–4%
            return max(0.008, min(0.04, span / 6.0))
    return 0.015


def compute_entry_exit_levels(
    price: float,
    action: SignalAction,
    confidence: float,
    bid: float | None,
    ask: float | None,
    heatmap: dict,
) -> dict:
    """SL/TP from price structure (ATR proxy + liq walls), not from cycle confidence.

    ``confidence`` is kept for API compatibility but does not set risk/reward %.
    """
    mid = price
    if bid and ask:
        mid = (bid + ask) / 2

    risk_pct = _structure_atr_pct(mid, heatmap)
    # Base ~2:1 structure target; walls may tighten TP
    reward_pct = risk_pct * 2.0
    _ = confidence  # unused — break R:R ↔ confidence circularity
    bins = heatmap.get("bins") or []

    if action in (SignalAction.BUY, SignalAction.WATCH):
        entry = ask if ask else mid * 1.0002
        stop = mid * (1 - risk_pct)
        t1 = mid * (1 + reward_pct * 0.55)
        t2 = mid * (1 + reward_pct)

        strong_long = [
            b for b in bins if b["dominant"] == "long" and b["long_intensity"] >= 0.55 and b["price"] < mid
        ]
        if strong_long:
            wall = max(strong_long, key=lambda b: b["long_intensity"])
            stop = min(stop, wall["price"] * 0.997)

        min_target = entry + (entry - stop) * 0.9
        strong_short = [
            b
            for b in bins
            if b["dominant"] == "short"
            and b["short_intensity"] >= 0.55
            and b["price"] > min_target
        ]
        if strong_short:
            magnet = min(strong_short, key=lambda b: abs(b["price"] - mid))
            if magnet["price"] <= t2:
                t1 = min(t1, magnet["price"] * 0.998)

        side = "long"
        entry_note = "Wejście long przy ask / lekko powyżej mid; stop pod klastrem long-liq."
    elif action == SignalAction.SELL:
        entry = bid if bid else mid * 0.9998
        stop = mid * (1 + risk_pct)
        t1 = mid * (1 - reward_pct * 0.55)
        t2 = mid * (1 - reward_pct)

        strong_short = [
            b for b in bins if b["dominant"] == "short" and b["short_intensity"] >= 0.55 and b["price"] > mid
        ]
        if strong_short:
            wall = max(strong_short, key=lambda b: b["short_intensity"])
            stop = max(stop, wall["price"] * 1.003)

        side = "short"
        entry_note = "Wejście short przy bid / lekko poniżej mid; stop nad klastrem short-liq."
    else:
        entry = mid
        stop = mid * (1 - risk_pct * 0.7)
        t1 = mid * (1 + reward_pct * 0.4)
        t2 = mid * (1 + reward_pct * 0.7)
        side = "neutral"
        entry_note = "Brak agresywnego wejścia — trzymaj / zarządzaj istniejącą ekspozycją."

    rr = abs((t1 - entry) / (entry - stop)) if entry != stop else 0
    return {
        "side": side,
        "entry": round(entry, 6),
        "stop_loss": round(stop, 6),
        "take_profit_1": round(t1, 6),
        "take_profit_2": round(t2, 6),
        "risk_reward": round(rr, 2),
        "note": entry_note,
    }


def score_super_opportunity(
    opp: Opportunity,
    book: dict | None,
    levels: dict,
    heatmap: dict,
    whale: dict | None = None,
) -> tuple[float, list[str]]:
    # Lower cycle weight so structure R:R is not double-counted with confidence
    score = opp.confidence * 0.35
    model = {
        "bitcoin": "Cykl Bitcoin",
        "presidential": "Cykl prezydencki",
        "alpha": "Cykl Bitcoin",
        "beta": "Cykl prezydencki",
    }.get(opp.cycle_source, opp.cycle_source or "cykl")
    reasons: list[str] = [f"{model}: pewność {opp.confidence:.0f}"]

    if opp.action == SignalAction.BUY:
        score += 8
        reasons.append("Bias cyklu: LONG")
    elif opp.action == SignalAction.SELL:
        score += 8
        reasons.append("Bias cyklu: SHORT")
    elif opp.action == SignalAction.WATCH:
        score += 2
        reasons.append("Bias cyklu: LONG (słabszy)")
    else:
        score -= 6
        reasons.append("Bias cyklu: NEUTRAL")

    if whale and opp.asset_class == AssetClass.CRYPTO:
        bias = whale.get("bias")
        strength = float(whale.get("strength") or 0)
        summary = str(whale.get("summary") or "Whale flow")
        reasons.append(f"Whale: {summary}")
        for line in (whale.get("factors") or [])[:2]:
            reasons.append(str(line))
        side = levels.get("side")
        if bias == "accumulate" and side == "long":
            score += min(12.0, strength * 0.12)
        elif bias == "distribute" and side == "short":
            score += min(12.0, strength * 0.12)
        elif bias == "accumulate" and side == "short":
            score -= min(10.0, strength * 0.1)
            reasons.append("Whale akumuluje — kara dla SHORT")
        elif bias == "distribute" and side == "long":
            score -= min(10.0, strength * 0.1)
            reasons.append("Whale dystrybuuje — kara dla LONG")

    if book:
        spread = float(book.get("spread_pct") or 0)
        if spread <= 0.05:
            score += 12
            reasons.append(f"Wąski spread {spread:.3f}% (dobry fill)")
        elif spread <= 0.15:
            score += 7
            reasons.append(f"Spread OK {spread:.3f}%")
        elif spread <= 0.4:
            score += 2
            reasons.append(f"Spread szeroki {spread:.3f}%")
        else:
            score -= 8
            reasons.append(f"Spread zbyt szeroki {spread:.3f}%")

        mid = book["mid"]
        if opp.action in (SignalAction.BUY, SignalAction.WATCH) and book["ask"] <= mid * 1.0015:
            score += 4
            reasons.append("Ask blisko mid — dobre porównanie bid/ask")
        if opp.action == SignalAction.SELL and book["bid"] >= mid * 0.9985:
            score += 4
            reasons.append("Bid blisko mid — dobre porównanie bid/ask")
    else:
        score -= 4
        reasons.append("Brak bid/ask — obniżona ocena fill")

    rr = float(levels.get("risk_reward") or 0)
    if rr >= 2.0:
        score += 10
        reasons.append(f"R:R {rr:.2f} (≥2)")
    elif rr >= 1.4:
        score += 6
        reasons.append(f"R:R {rr:.2f}")
    elif rr >= 1.0:
        score += 2
    else:
        score -= 5
        reasons.append(f"Słabe R:R {rr:.2f}")

    bins = heatmap.get("bins") or []
    price = opp.price
    if bins and opp.action in (SignalAction.BUY, SignalAction.WATCH):
        near_long = [
            b for b in bins
            if b["price"] < price and abs(b["price"] - price) / price < 0.03 and b["long_intensity"] > 0.5
        ]
        near_short = [
            b for b in bins
            if b["price"] > price and abs(b["price"] - price) / price < 0.04 and b["short_intensity"] > 0.5
        ]
        if near_long:
            score += 6
            reasons.append("Stop strefa wsparta long-liq (zieleń)")
        if near_short:
            score += 5
            reasons.append("Cel w kierunku short-liq (czerwień)")
    if bins and opp.action == SignalAction.SELL:
        near_short = [
            b for b in bins
            if b["price"] > price and abs(b["price"] - price) / price < 0.03 and b["short_intensity"] > 0.5
        ]
        near_long = [
            b for b in bins
            if b["price"] < price and abs(b["price"] - price) / price < 0.04 and b["long_intensity"] > 0.5
        ]
        if near_short:
            score += 6
            reasons.append("Stop strefa wsparta short-liq (czerwień)")
        if near_long:
            score += 5
            reasons.append("Cel w kierunku long-liq (zieleń)")

    return max(0.0, min(100.0, round(score, 1))), reasons


async def build_super_opportunity(opp: Opportunity, *, include_heatmap_3d: bool = True) -> dict:
    whale: dict | None = None
    if opp.asset_class == AssetClass.CRYPTO:
        whale = get_cached_whale(opp.symbol)
        if whale is None:
            whale = await fetch_whale_for_symbol(opp.symbol)

    book, profile = await asyncio.gather(
        fetch_bid_ask(opp.symbol, opp.asset_class.value),
        fetch_volume_profile(opp.symbol, opp.asset_class.value),
    )
    price = opp.price
    if book:
        price = book["mid"]

    heatmap = estimate_liquidation_heatmap(
        price,
        highs=profile.get("highs"),
        lows=profile.get("lows"),
        volumes=profile.get("volumes"),
    )
    levels = compute_entry_exit_levels(
        price,
        opp.action,
        opp.confidence,
        book["bid"] if book else None,
        book["ask"] if book else None,
        heatmap,
    )
    super_score, reasons = score_super_opportunity(opp, book, levels, heatmap, whale=whale)
    prediction = predict_liq_path(heatmap, levels, opp.action.value)
    ai_signal = consult_trade_signal(
        action=opp.action.value,
        cycle_confidence=opp.confidence,
        cycle_source=opp.cycle_source,
        phase=opp.phase,
        super_score=super_score,
        levels=levels,
        spread_pct=book["spread_pct"] if book else None,
        prediction=prediction,
    )
    reasons = [ai_signal["summary"], prediction["summary"], *reasons]

    heat_out = heatmap
    if not include_heatmap_3d:
        heat_out = {**heatmap, "columns": [], "preview": True}

    whale_out = None
    if whale:
        whale_out = {
            "symbol": whale.get("symbol", opp.symbol),
            "bias": whale.get("bias", "neutral"),
            "side_hint": whale.get("side_hint", "neutral"),
            "strength": float(whale.get("strength") or 0),
            "score": float(whale.get("score") or 0),
            "summary": str(whale.get("summary") or ""),
            "factors": list(whale.get("factors") or [])[:6],
            "updated_at": whale.get("updated_at"),
        }

    return {
        "symbol": opp.symbol,
        "name": opp.name,
        "asset_class": opp.asset_class.value,
        "action": opp.action.value,
        "cycle_confidence": opp.confidence,
        "super_score": super_score,
        "is_super": super_score >= 72
        and ai_signal["signal"] in ("kup", "sprzedaj")
        and opp.action in (SignalAction.BUY, SignalAction.SELL, SignalAction.WATCH),
        "cycle_source": opp.cycle_source,
        "phase": opp.phase,
        "price": price,
        "bid": book["bid"] if book else None,
        "ask": book["ask"] if book else None,
        "spread_pct": book["spread_pct"] if book else None,
        "book_source": book["source"] if book else None,
        "levels": levels,
        "heatmap": heat_out,
        "prediction": prediction,
        "ai_signal": ai_signal,
        "whale": whale_out,
        "reasons": reasons,
        "rationale": opp.rationale,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "community": (
            opp.community.model_dump()
            if getattr(opp, "community", None) is not None
            else resolve_community_links(opp.symbol, opp.name)
        ),
    }


async def build_super_opportunities(min_score: float = 0) -> dict:
    if not scanner.opportunities:
        await scanner.scan()

    sem = asyncio.Semaphore(5)

    async def _one(opp: Opportunity) -> dict | None:
        async with sem:
            try:
                return await build_super_opportunity(opp, include_heatmap_3d=False)
            except Exception as exc:
                logger.warning("Super opp failed for %s: %s", opp.symbol, exc)
                return None

    actionable = [
        o
        for o in scanner.opportunities
        if o.action in (SignalAction.BUY, SignalAction.SELL, SignalAction.WATCH)
    ]
    longs = [o for o in actionable if o.action in (SignalAction.BUY, SignalAction.WATCH)]
    shorts = [o for o in actionable if o.action == SignalAction.SELL]
    longs.sort(key=lambda o: o.confidence, reverse=True)
    shorts.sort(key=lambda o: o.confidence, reverse=True)

    pool: list[Opportunity] = []
    pool.extend(shorts[:12])
    pool.extend(longs[:12])
    if len(pool) < 24:
        seen = {o.symbol for o in pool}
        for o in actionable:
            if o.symbol not in seen:
                pool.append(o)
                seen.add(o.symbol)
            if len(pool) >= 24:
                break

    results = await asyncio.gather(*[_one(o) for o in pool])
    items = [r for r in results if r and r["super_score"] >= min_score]
    # Equal sort by super_score — no short-side rank boost
    items.sort(key=lambda x: x["super_score"], reverse=True)

    supers = [i for i in items if i["is_super"]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "super_count": len(supers),
        "long_count": sum(1 for i in items if i["levels"]["side"] == "long"),
        "short_count": sum(1 for i in items if i["levels"]["side"] == "short"),
        "items": items,
        "supers": supers,
        "scanner_last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
    }

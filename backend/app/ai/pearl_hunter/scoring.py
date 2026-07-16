"""Shared scoring helpers for pearl hunters."""

from __future__ import annotations


def score_equity_momentum(
    *,
    change_pct: float | None,
    dist_from_low_pct: float | None,
    dist_from_high_pct: float | None,
) -> tuple[float, float, str, str]:
    """Return (score 0-100, confidence, action, rationale)."""
    chg = change_pct or 0.0
    from_low = dist_from_low_pct if dist_from_low_pct is not None else 50.0
    from_high = dist_from_high_pct if dist_from_high_pct is not None else 50.0

    # Prefer names near 52w low with constructive short-term bounce, or strong momentum away from highs carefully.
    near_low_bonus = max(0.0, 40.0 - from_low)  # closer to low → higher
    rebound = max(0.0, min(chg, 12.0)) * 2.5
    overheat_penalty = max(0.0, chg - 15.0) * 1.5
    room_to_high = max(0.0, from_high) * 0.35

    score = 35.0 + near_low_bonus + rebound + room_to_high - overheat_penalty
    score = max(0.0, min(98.0, score))

    if from_low <= 18 and chg >= 1.5:
        action = "buy"
        rationale = (
            f"Perełka equity: blisko 52w low ({from_low:.0f}% od dołka), "
            f"odbicie {chg:+.1f}% — setup akumulacyjny poza core listą."
        )
    elif chg >= 6 and from_high >= 15:
        action = "watch"
        rationale = (
            f"Momentum {chg:+.1f}% z zapasem do ATH ({from_high:.0f}% od szczytu) — obserwuj kontynuację."
        )
    elif chg <= -8:
        action = "watch"
        rationale = f"Głęboka wyprzedaż ({chg:+.1f}%) — kandydat do watchlisty, nie chase."
    else:
        action = "watch"
        rationale = f"Skan equity: zmiana {chg:+.1f}%, pozycja w zakresie 52w (low {from_low:.0f}% / high {from_high:.0f}%)."

    confidence = min(95.0, score * 0.92)
    return round(score, 1), round(confidence, 1), action, rationale


def score_crypto_mover(
    *,
    change_pct_24h: float | None,
    market_cap_rank: int | None,
    volume_usd: float | None,
) -> tuple[float, float, str, str]:
    chg = change_pct_24h or 0.0
    rank = market_cap_rank or 999
    vol = volume_usd or 0.0

    rank_bonus = max(0.0, 40.0 - min(rank, 80) * 0.4)
    move_score = min(abs(chg), 25.0) * 2.0
    vol_bonus = 8.0 if vol >= 50_000_000 else (4.0 if vol >= 10_000_000 else 0.0)

    score = 30.0 + rank_bonus + move_score * 0.6 + vol_bonus
    if chg < 0:
        score *= 0.85  # dump ≠ automatic pearl; still interesting
    score = max(0.0, min(97.0, score))

    if chg >= 8 and rank <= 120:
        action = "buy"
        rationale = (
            f"Perełka crypto: +{chg:.1f}%/24h, rank #{rank}, płynność "
            f"{'wysoka' if vol >= 50_000_000 else 'OK'} — poza naszą listą core."
        )
    elif chg <= -12 and rank <= 80:
        action = "watch"
        rationale = f"Silna przecena {chg:.1f}% w top-80 — możliwe odbicie, tylko watch."
    else:
        action = "watch"
        rationale = f"Skan crypto: {chg:+.1f}%/24h, rank #{rank}."

    confidence = min(94.0, score * 0.9)
    return round(score, 1), round(confidence, 1), action, rationale

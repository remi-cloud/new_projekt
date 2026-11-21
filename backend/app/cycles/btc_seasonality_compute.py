"""Pure BTC seasonality statistics (shared by the live refresher and the offline script).

Input: monthly (date, close, high) rows downloaded from Yahoo Finance.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date

BEAR_DAYS = 364
BULL_DAYS = 1064
BULL_END = BEAR_DAYS + BULL_DAYS
BEST_SIX = {11, 12, 1, 2, 3, 4}
PHASE_KEYS = (
    "bear_early",
    "bear_late",
    "bull_early",
    "bull_mid",
    "late_distribution",
)
MIN_CELL_N = 3

def year_of_term(as_of: date) -> int:
    y = as_of.year if (as_of.month, as_of.day) >= (1, 20) else as_of.year - 1
    while y % 4 != 1:
        y -= 1
    term_start = date(y, 1, 20)
    years_elapsed = as_of.year - term_start.year
    if (as_of.month, as_of.day) < (1, 20):
        years_elapsed -= 1
    return min(max(years_elapsed + 1, 1), 4)


def monthly_returns(rows: list[tuple[date, float, float]]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for i in range(1, len(rows)):
        _d0, c0, _h0 = rows[i - 1]
        d1, c1, _h1 = rows[i]
        if c0 <= 0:
            continue
        out.append((d1, (c1 / c0 - 1.0) * 100.0))
    return out


def calendar_stats(rets: list[tuple[date, float]]) -> dict[int, dict]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for d, r in rets:
        buckets[d.month].append(r)
    out: dict[int, dict] = {}
    for m in range(1, 13):
        vals = buckets.get(m) or []
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        hit = round(100.0 * sum(1 for v in vals if v > 0) / len(vals), 1) if vals else 0.0
        out[m] = {"avg_pct": avg, "n": len(vals), "hit_rate_pct": hit}
    return out


def best_six_avg(cal: dict[int, dict]) -> tuple[float, float]:
    best_vals = [cal[m]["avg_pct"] for m in range(1, 13) if m in BEST_SIX]
    worst_vals = [cal[m]["avg_pct"] for m in range(1, 13) if m not in BEST_SIX]
    return (
        round(sum(best_vals) / len(best_vals), 2),
        round(sum(worst_vals) / len(worst_vals), 2),
    )


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 6 or len(xs) != len(ys):
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return round(num / (denx * deny), 3)


def aligned_pairs(
    a: list[tuple[date, float]], b: list[tuple[date, float]]
) -> list[tuple[date, float, float]]:
    mb = {(d.year, d.month): r for d, r in b}
    out: list[tuple[date, float, float]] = []
    for d, r in a:
        key = (d.year, d.month)
        if key in mb:
            out.append((d, r, mb[key]))
    return out


def rolling_corr(
    pairs: list[tuple[date, float, float]], window: int = 24
) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for i in range(window - 1, len(pairs)):
        chunk = pairs[i - window + 1 : i + 1]
        c = pearson([p[1] for p in chunk], [p[2] for p in chunk])
        if c is not None:
            out.append((chunk[-1][0], c))
    return out


def phase_bucket(days_since_ath: int) -> str:
    if days_since_ath < BEAR_DAYS // 2:
        return "bear_early"
    if days_since_ath < BEAR_DAYS:
        return "bear_late"
    progress_bull = days_since_ath - BEAR_DAYS
    if days_since_ath >= BULL_END:
        return "late_distribution"
    if progress_bull > BULL_DAYS * 0.75:
        return "late_distribution"
    if progress_bull > BULL_DAYS * 0.4:
        return "bull_mid"
    return "bull_early"


def attach_phases(
    rows: list[tuple[date, float, float]], rets: list[tuple[date, float]]
) -> list[tuple[date, float, str, int]]:
    """For each monthly return date, compute days since rolling ATH (by high)."""
    ath_date = rows[0][0]
    ath_high = rows[0][2]
    # Map month-start date → days_since_ath at that bar using highs up to prior bar
    phase_by_ym: dict[tuple[int, int], tuple[str, int]] = {}
    for i, (d, _c, h) in enumerate(rows):
        # ATH state before this bar's return accrues: use highs through previous bar
        if i == 0:
            days = 0
        else:
            # Update ATH with previous bar high first
            prev_d, _pc, prev_h = rows[i - 1]
            if prev_h >= ath_high:
                ath_high = prev_h
                ath_date = prev_d
            days = (d - ath_date).days
            if days < 0:
                days = 0
            if h >= ath_high:
                # new ATH this bar — still attribute return under prior days for that month start
                pass
        phase_by_ym[(d.year, d.month)] = (phase_bucket(days), days)
        if h >= ath_high:
            ath_high = h
            ath_date = d

    out: list[tuple[date, float, str, int]] = []
    for d, r in rets:
        ph, days = phase_by_ym.get((d.year, d.month), ("bull_mid", 0))
        out.append((d, r, ph, days))
    return out


def phase_month_matrix(
    labeled: list[tuple[date, float, str, int]],
) -> tuple[dict[str, dict[int, float]], dict[str, dict[int, int]]]:
    buckets: dict[tuple[str, int], list[float]] = defaultdict(list)
    for d, r, ph, _days in labeled:
        buckets[(ph, d.month)].append(r)
    avgs: dict[str, dict[int, float]] = {p: {} for p in PHASE_KEYS}
    ns: dict[str, dict[int, int]] = {p: {} for p in PHASE_KEYS}
    for ph in PHASE_KEYS:
        for m in range(1, 13):
            vals = buckets.get((ph, m)) or []
            ns[ph][m] = len(vals)
            if len(vals) >= MIN_CELL_N:
                avgs[ph][m] = round(sum(vals) / len(vals), 2)
            else:
                avgs[ph][m] = None  # type: ignore[assignment]
    # Serialize None as null in JSON; for Python file use None
    return avgs, ns


def term_year_avgs(rets: list[tuple[date, float]]) -> dict[int, float]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for d, r in rets:
        buckets[year_of_term(d)].append(r)
    return {y: round(sum(v) / len(v), 2) for y, v in sorted(buckets.items()) if v}


def verdict(
    corr: float | None,
    sign_agree: int,
    best_six_delta: float,
    rolling_latest: float | None,
) -> tuple[str, str]:
    """Return (verdict, regime)."""
    if corr is not None and corr >= 0.45 and sign_agree >= 8 and abs(best_six_delta) <= 4.0:
        v = "similar_to_spx"
    elif corr is not None and (corr >= 0.25 or sign_agree >= 6):
        v = "partially"
    else:
        v = "idiosyncratic"
    regime = "equity_beta"
    if rolling_latest is None or rolling_latest < 0.25:
        regime = "crypto_idiosyncratic"
    elif rolling_latest < 0.45:
        regime = "mixed"
    return v, regime

"""BTC calendar + ATH-phase seasonality helpers (additive to 364/1064 clock)."""

from __future__ import annotations

from datetime import date

from app.cycles.bitcoin_seasonality_data import (
    BTC_CALENDAR_MONTHLY_N,
    BTC_CALENDAR_MONTHLY_RETURNS,
    BTC_PHASE_MONTHLY_N,
    BTC_PHASE_MONTHLY_RETURNS,
    MIN_CELL_N,
    SPX_COMPARISON,
)
from app.models.schemas import CyclePhase, SignalAction

BEST_SIX_MONTHS = {11, 12, 1, 2, 3, 4}

MONTH_NAMES_PL = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień",
}

PHASE_BUCKET = {
    CyclePhase.BEAR: "bear_late",  # refined by days below
    CyclePhase.BULL: "bull_mid",
    CyclePhase.DISTRIBUTION: "late_distribution",
    CyclePhase.ACCUMULATION: "bear_late",
    CyclePhase.NEUTRAL: "bull_mid",
}


def phase_bucket_from_cycle(
    phase: CyclePhase,
    days_since_ath: int,
    bear_end: int = 364,
    bull_days: int = 1064,
) -> str:
    if days_since_ath < bear_end // 2:
        return "bear_early"
    if days_since_ath < bear_end:
        return "bear_late"
    bull_end = bear_end + bull_days
    if days_since_ath >= bull_end:
        return "late_distribution"
    progress = days_since_ath - bear_end
    if progress > bull_days * 0.75 or phase == CyclePhase.DISTRIBUTION:
        return "late_distribution"
    if progress > bull_days * 0.4:
        return "bull_mid"
    return "bull_early"


def calendar_season(month: int) -> str:
    """US Almanac label for comparison only — not a BTC primary signal."""
    return "best_six" if month in BEST_SIX_MONTHS else "worst_six"


def month_bias(avg_pct: float | None) -> str:
    if avg_pct is None:
        return "neutral"
    return "up" if avg_pct >= 0 else "down"


def calendar_month_avg(month: int) -> float | None:
    n = BTC_CALENDAR_MONTHLY_N.get(month, 0)
    if n < MIN_CELL_N:
        return None
    return float(BTC_CALENDAR_MONTHLY_RETURNS.get(month, 0.0))


def phase_month_avg(phase_key: str, month: int) -> float | None:
    n = (BTC_PHASE_MONTHLY_N.get(phase_key) or {}).get(month, 0)
    if n < MIN_CELL_N:
        return None
    val = (BTC_PHASE_MONTHLY_RETURNS.get(phase_key) or {}).get(month)
    if val is None:
        return None
    return float(val)


def resolve_month_avg(
    phase: CyclePhase,
    days_since_ath: int,
    month: int,
    bear_end: int = 364,
    bull_days: int = 1064,
) -> tuple[float | None, int, str]:
    """Prefer phase×month; fall back to calendar. Returns (avg, n, source)."""
    key = phase_bucket_from_cycle(phase, days_since_ath, bear_end, bull_days)
    n_phase = (BTC_PHASE_MONTHLY_N.get(key) or {}).get(month, 0)
    avg_phase = phase_month_avg(key, month)
    if avg_phase is not None:
        return avg_phase, n_phase, f"phase:{key}"
    n_cal = BTC_CALENDAR_MONTHLY_N.get(month, 0)
    avg_cal = calendar_month_avg(month)
    if avg_cal is not None:
        return avg_cal, n_cal, "calendar"
    return None, 0, "none"


def btc_seasonality_overlay_delta(
    phase: CyclePhase,
    days_since_ath: int,
    as_of: date,
    *,
    weight: float = 1.0,
    bear_end: int = 364,
    bull_days: int = 1064,
) -> tuple[float, str, float | None]:
    """Confidence delta for crypto. weight=1 for BTC, 0.5 for alts.

    Does not upgrade DISTRIBUTION toward BUY — caller must respect signal rules.
    """
    avg, n, source = resolve_month_avg(
        phase, days_since_ath, as_of.month, bear_end, bull_days
    )
    if avg is None:
        return 0.0, "Sezonowość BTC: brak próby (min_n).", None

    from app.cycles.seasonality_monitor import get_overlay_scale

    delta = 0.0
    if avg >= 0.5:
        delta += 6.0
    elif avg <= -0.3:
        delta -= 7.0

    # Soft Best Six comparison only when not idiosyncratic
    verdict = SPX_COMPARISON.get("verdict", "partially")
    if verdict != "idiosyncratic":
        if calendar_season(as_of.month) == "best_six":
            delta += 1.0
        else:
            delta -= 1.0

    scale = get_overlay_scale()
    delta *= weight * scale
    note = (
        f"Sezonowość BTC: {MONTH_NAMES_PL[as_of.month]} hist. {avg:+.1f}% "
        f"({month_bias(avg)}, n={n}, {source}"
        + (f", scale={scale:.1f}" if scale < 1.0 else "")
        + ")."
    )
    return delta, note, avg


def adjust_signal_for_btc_seasonality(
    base: SignalAction,
    month_avg: float | None,
    phase: CyclePhase,
) -> SignalAction:
    """Additive tweak; never upgrades out of DISTRIBUTION/SELL via month alone."""
    if month_avg is None:
        return base
    if phase == CyclePhase.DISTRIBUTION or base == SignalAction.SELL:
        if month_avg <= -0.3 and base == SignalAction.WATCH:
            return SignalAction.HOLD
        return base
    signal = base
    if month_avg >= 0.5:
        if signal == SignalAction.HOLD:
            signal = SignalAction.WATCH
        elif signal == SignalAction.WATCH:
            signal = SignalAction.BUY
    elif month_avg <= -0.3:
        if signal == SignalAction.BUY:
            signal = SignalAction.WATCH
        elif signal == SignalAction.WATCH:
            signal = SignalAction.HOLD
    return signal


def month_returns_strip(as_of: date | None = None) -> list[dict]:
    as_of = as_of or date.today()
    out = []
    for m in range(1, 13):
        avg = calendar_month_avg(m)
        pct = float(avg) if avg is not None else 0.0
        out.append(
            {
                "month": m,
                "avg_return_pct": pct,
                "bias": month_bias(avg) if avg is not None else "neutral",
                "is_current": m == as_of.month,
                "n": BTC_CALENDAR_MONTHLY_N.get(m, 0),
            }
        )
    return out


def btc_seasonality_desk_brief(
    phase: CyclePhase,
    days_since_ath: int,
    as_of: date | None = None,
    *,
    top_n: int = 3,
    bear_end: int = 364,
    bull_days: int = 1064,
) -> dict:
    as_of = as_of or date.today()
    avg, n, source = resolve_month_avg(
        phase, days_since_ath, as_of.month, bear_end, bull_days
    )
    ranked = sorted(
        (
            (m, float(BTC_CALENDAR_MONTHLY_RETURNS[m]))
            for m in range(1, 13)
            if BTC_CALENDAR_MONTHLY_N.get(m, 0) >= MIN_CELL_N
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    strongest = [
        {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": a} for m, a in ranked[:top_n]
    ]
    weakest = [
        {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": a} for m, a in ranked[-top_n:]
    ]
    cmp = dict(SPX_COMPARISON)
    season = calendar_season(as_of.month)
    phase_key = phase_bucket_from_cycle(phase, days_since_ath, bear_end, bull_days)
    cur = avg if avg is not None else 0.0
    return {
        "phase": phase.value,
        "phase_bucket": phase_key,
        "current_month": as_of.month,
        "current_month_name_pl": MONTH_NAMES_PL[as_of.month],
        "current_month_avg_pct": round(cur, 2) if avg is not None else None,
        "current_month_bias": month_bias(avg),
        "seasonality_sample_count": n,
        "source": source,
        "calendar_season": season,
        "calendar_season_note": (
            "Best Six (Nov–Apr) is a US equity Almanac window — comparison only for BTC; "
            f"BTC best/worst six avgs: {cmp.get('best_six_btc_avg_pct')}% / "
            f"{cmp.get('worst_six_btc_avg_pct')}% (often similar — do not copy SPX blindly)."
        ),
        "strongest_months": strongest,
        "weakest_months": weakest,
        "spx_comparison": {
            "corr_full": cmp.get("corr_full"),
            "corr_rolling_24m_latest": cmp.get("corr_rolling_24m_latest"),
            "best_six_delta_pct": cmp.get("best_six_delta_pct"),
            "month_sign_agreement": cmp.get("month_sign_agreement"),
            "verdict": cmp.get("verdict"),
            "regime": cmp.get("regime"),
        },
        "expect_now": (
            f"BTC {MONTH_NAMES_PL[as_of.month]} ({phase_key}): "
            + (
                f"hist. {cur:+.1f}% ({month_bias(avg)}, n={n}); "
                if avg is not None
                else "za mało prób; "
            )
            + f"vs SPX verdict={cmp.get('verdict')}, regime={cmp.get('regime')}."
        ),
    }


__all__ = [
    "BEST_SIX_MONTHS",
    "MONTH_NAMES_PL",
    "adjust_signal_for_btc_seasonality",
    "btc_seasonality_desk_brief",
    "btc_seasonality_overlay_delta",
    "calendar_month_avg",
    "calendar_season",
    "month_bias",
    "month_returns_strip",
    "phase_bucket_from_cycle",
    "phase_month_avg",
    "resolve_month_avg",
]

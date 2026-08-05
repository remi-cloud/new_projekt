"""US presidential seasonality helpers (universe + per-symbol overlay)."""

from __future__ import annotations

from datetime import date

from app.cycles.presidential_seasonality_data import (
    SEASONALITY_UNIVERSE_SIZE,
    US_CLASS_MONTHLY_RETURNS,
    US_SYMBOL_MONTHLY_RETURNS,
    US_UNIVERSE_MONTHLY_RETURNS,
)
from app.models.schemas import PresidentialYear, SignalAction

# Stock Trader's Almanac Best Six Months (Nov–Apr)
BEST_SIX_MONTHS = {11, 12, 1, 2, 3, 4}

YEAR_NUM = {
    PresidentialYear.YEAR_1: 1,
    PresidentialYear.YEAR_2: 2,
    PresidentialYear.YEAR_3: 3,
    PresidentialYear.YEAR_4: 4,
}

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


def calendar_season(month: int) -> str:
    return "best_six" if month in BEST_SIX_MONTHS else "worst_six"


def month_bias(avg_pct: float) -> str:
    return "up" if avg_pct >= 0 else "down"


def universe_month_avg(year: PresidentialYear, month: int) -> float:
    y = YEAR_NUM[year]
    return float(US_UNIVERSE_MONTHLY_RETURNS.get(y, {}).get(month, 0.0))


def symbol_month_avg(
    symbol: str,
    year: PresidentialYear,
    month: int,
    asset_class: str | None = None,
) -> float:
    """Per-symbol → class → universe fallback."""
    y = YEAR_NUM[year]
    sym_mat = US_SYMBOL_MONTHLY_RETURNS.get(symbol)
    if sym_mat and y in sym_mat and month in sym_mat[y]:
        return float(sym_mat[y][month])
    if asset_class:
        cls_mat = US_CLASS_MONTHLY_RETURNS.get(asset_class)
        if cls_mat and y in cls_mat and month in cls_mat[y]:
            return float(cls_mat[y][month])
    return universe_month_avg(year, month)


def month_weight_multiplier(month_avg: float) -> float:
    if month_avg >= 0.5:
        return 1.15
    if month_avg <= -0.3:
        return 0.75
    return 1.0


def season_weight_multiplier(season: str) -> float:
    return 1.1 if season == "best_six" else 0.85


def adjust_signal_for_seasonality(
    base: SignalAction,
    month_avg: float,
    season: str,
) -> SignalAction:
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

    if season == "worst_six" and signal == SignalAction.BUY and month_avg < 0.5:
        signal = SignalAction.WATCH
    return signal


def compute_buy_weight(base_weight: float, month_avg: float, season: str) -> float:
    w = base_weight * month_weight_multiplier(month_avg) * season_weight_multiplier(season)
    return round(min(1.0, max(0.15, w)), 3)


def seasonality_overlay_delta(
    symbol: str,
    year: PresidentialYear,
    as_of: date,
    asset_class: str | None = None,
) -> tuple[float, str]:
    """Return (confidence_delta, note) for a US instrument."""
    from app.cycles.seasonality_monitor import get_overlay_scale

    avg = symbol_month_avg(symbol, year, as_of.month, asset_class)
    season = calendar_season(as_of.month)
    delta = 0.0
    if avg >= 0.5:
        delta += 6.0
    elif avg <= -0.3:
        delta -= 7.0
    if season == "best_six":
        delta += 2.0
    else:
        delta -= 2.0
    scale = get_overlay_scale()
    delta *= scale
    note = (
        f"Sezonowość {symbol}: {MONTH_NAMES_PL[as_of.month]} "
        f"hist. {avg:+.1f}% ({month_bias(avg)}), {season}"
        + (f", scale={scale:.1f}" if scale < 1.0 else "")
        + "."
    )
    return delta, note


def seasonality_desk_brief(
    year: PresidentialYear,
    as_of: date | None = None,
    *,
    top_n: int = 3,
) -> dict:
    """Human + structured brief for the AI desk: where/when up vs down."""
    as_of = as_of or date.today()
    y = YEAR_NUM[year]
    row = US_UNIVERSE_MONTHLY_RETURNS.get(y, {})
    ranked = sorted(((m, float(avg)) for m, avg in row.items()), key=lambda x: x[1], reverse=True)
    strongest = [
        {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": avg}
        for m, avg in ranked[:top_n]
    ]
    weakest = [
        {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": avg}
        for m, avg in ranked[-top_n:]
    ]
    cur = float(row.get(as_of.month, 0.0))
    season = calendar_season(as_of.month)
    all_years: dict[int, dict[str, object]] = {}
    for yn in range(1, 5):
        yrow = US_UNIVERSE_MONTHLY_RETURNS.get(yn, {})
        ranked_y = sorted(
            ((m, float(avg)) for m, avg in yrow.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        all_years[yn] = {
            "months": {m: float(yrow.get(m, 0.0)) for m in range(1, 13)},
            "strongest": [
                {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": avg}
                for m, avg in ranked_y[:top_n]
            ],
            "weakest": [
                {"month": m, "name_pl": MONTH_NAMES_PL[m], "avg_pct": avg}
                for m, avg in ranked_y[-top_n:]
            ],
        }
    return {
        "year_of_term": y,
        "universe_size": SEASONALITY_UNIVERSE_SIZE,
        "current_month": as_of.month,
        "current_month_name_pl": MONTH_NAMES_PL[as_of.month],
        "current_month_avg_pct": round(cur, 2),
        "current_month_bias": month_bias(cur),
        "calendar_season": season,
        "calendar_season_note": (
            "Best Six Months (Nov–Apr): historically stronger window for US risk assets."
            if season == "best_six"
            else "Out of season (May–Oct): historically softer window — prefer confirmation, smaller size."
        ),
        "strongest_months": strongest,
        "weakest_months": weakest,
        "all_years": all_years,
        "expect_now": (
            f"Y{y} {MONTH_NAMES_PL[as_of.month]}: agregat USA {cur:+.1f}% "
            f"({month_bias(cur)}); {season}."
        ),
    }


__all__ = [
    "BEST_SIX_MONTHS",
    "MONTH_NAMES_PL",
    "SEASONALITY_UNIVERSE_SIZE",
    "US_UNIVERSE_MONTHLY_RETURNS",
    "adjust_signal_for_seasonality",
    "calendar_season",
    "compute_buy_weight",
    "month_bias",
    "seasonality_desk_brief",
    "seasonality_overlay_delta",
    "symbol_month_avg",
    "universe_month_avg",
]

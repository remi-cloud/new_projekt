"""Intra-month seasonality: day-of-month (1–31) and week-of-month (1–4)."""

from __future__ import annotations

from typing import Any, Literal

from app.cycles.intramonth_seasonality_data import (
    BTC_INTRAMONTH,
    MIN_OBS,
    US_INTRAMONTH,
    US_INTRAMONTH_UNIVERSE_SIZE,
)

Universe = Literal["us", "btc"]

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


def _table(universe: Universe) -> dict[int, dict]:
    return US_INTRAMONTH if universe == "us" else BTC_INTRAMONTH


def get_intramonth(universe: Universe, month: int) -> dict[str, Any]:
    if month < 1 or month > 12:
        raise ValueError("month must be 1–12")
    if universe not in ("us", "btc"):
        raise ValueError("universe must be us|btc")
    table = _table(universe)
    row = table.get(month) or {"days": {}, "weeks": {}}
    days_out = []
    for d in range(1, 32):
        cell = (row.get("days") or {}).get(d) or {"avg_pct": None, "n": 0, "bias": "neutral"}
        days_out.append(
            {
                "day": d,
                "avg_return_pct": cell.get("avg_pct"),
                "bias": cell.get("bias") or "neutral",
                "n": int(cell.get("n") or 0),
                "week": min(4, ((d - 1) // 7) + 1),
            }
        )
    weeks_out = []
    for w in range(1, 5):
        cell = (row.get("weeks") or {}).get(w) or {
            "avg_pct": None,
            "n": 0,
            "bias": "neutral",
            "days": "",
        }
        weeks_out.append(
            {
                "week": w,
                "label": f"W{w}",
                "day_range": cell.get("days") or f"{(w - 1) * 7 + 1}-{31 if w == 4 else w * 7}",
                "avg_return_pct": cell.get("avg_pct"),
                "bias": cell.get("bias") or "neutral",
                "n": int(cell.get("n") or 0),
            }
        )
    ranked_days = sorted(
        [x for x in days_out if x["avg_return_pct"] is not None],
        key=lambda x: x["avg_return_pct"],
        reverse=True,
    )
    return {
        "universe": universe,
        "universe_label": (
            f"USA equal-weight ({US_INTRAMONTH_UNIVERSE_SIZE} tickerów)"
            if universe == "us"
            else "BTC-USD"
        ),
        "month": month,
        "month_name_pl": MONTH_NAMES_PL[month],
        "min_obs": MIN_OBS,
        "days": days_out,
        "weeks": weeks_out,
        "strongest_days": ranked_days[:3],
        "weakest_days": list(reversed(ranked_days[-3:])) if ranked_days else [],
        "note": (
            "Średnie dzienne zwroty w danym miesiącu kalendarzowym (trading days). "
            "Tygodnie: 1–7, 8–14, 15–21, 22–31. Nie rekomendacja inwestycyjna."
        ),
    }


def month_has_intramonth(universe: Universe, month: int) -> bool:
    row = _table(universe).get(month) or {}
    weeks = row.get("weeks") or {}
    return any((weeks.get(w) or {}).get("avg_pct") is not None for w in range(1, 5))

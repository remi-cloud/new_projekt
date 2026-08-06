"""Global cycle order book — adopted patterns that reproduce across markets."""

from __future__ import annotations

from typing import Any, Literal

try:
    from app.cycles.global_cycle_book_data import (
        GENERATED_AT,
        META,
        ORDER_BOOK,
        PAIRWISE_MONTH_CORR,
        PROFILES,
    )
except ImportError:  # pragma: no cover
    GENERATED_AT = ""
    META: dict[str, Any] = {}
    ORDER_BOOK: list[dict[str, Any]] = []
    PAIRWISE_MONTH_CORR: dict[str, float] = {}
    PROFILES: dict[str, Any] = {}

MONTH_KEYS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def get_global_cycle_book(
    status: Literal["all", "adopted", "watch", "rejected"] = "all",
) -> dict[str, Any]:
    book = list(ORDER_BOOK)
    if status != "all":
        book = [e for e in book if e.get("status") == status]

    profiles_out: dict[str, Any] = {}
    for uid, p in PROFILES.items():
        months = []
        for m in range(1, 13):
            cell = (p.get("months") or {}).get(m) or {}
            months.append(
                {
                    "month": m,
                    "label": MONTH_KEYS[m - 1],
                    "avg_return_pct": cell.get("avg_pct"),
                    "n": cell.get("n", 0),
                    "bias": cell.get("bias", "neutral"),
                }
            )
        weeks = []
        for w in range(1, 5):
            cell = (p.get("weeks") or {}).get(w) or {}
            weeks.append(
                {
                    "week": w,
                    "label": f"W{w}",
                    "day_range": cell.get("days", ""),
                    "avg_return_pct": cell.get("avg_pct"),
                    "n": cell.get("n", 0),
                    "bias": cell.get("bias", "neutral"),
                }
            )
        profiles_out[uid] = {
            "universe": uid,
            "label": p.get("label", uid),
            "symbols_included": p.get("symbols_included", 0),
            "symbols_total": p.get("symbols_total", 0),
            "months": months,
            "weeks": weeks,
            "yearly": p.get("yearly") or {},
        }

    return {
        "generated_at": GENERATED_AT or META.get("generated_at"),
        "meta": META,
        "pairwise_month_corr": PAIRWISE_MONTH_CORR,
        "profiles": profiles_out,
        "order_book": book,
        "adopted": [e for e in ORDER_BOOK if e.get("status") == "adopted"],
        "note": (
            "Field scouts: te same reguły (equal-weight stock/etf/index lub crypto) "
            "na us/eu/asia/em/pl/crypto. Adopted = wzorzec odtworzony na ≥N rynkach."
        ),
    }

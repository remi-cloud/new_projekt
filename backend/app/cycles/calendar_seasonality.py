"""Plain calendar-month seasonality + monthly pump leaderboards."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from app.data.assets import CATALOG_BY_SYMBOL

try:
    from app.cycles.calendar_seasonality_data import (
        BY_CLASS,
        BY_REGION,
        GENERATED_AT,
        META,
        MONTH_TOP,
        MONTH_TOP_BY_CLASS,
        SYMBOL_META,
        SYMBOL_MONTHS,
    )
except ImportError:  # pragma: no cover
    GENERATED_AT = ""
    META: dict[str, Any] = {}
    SYMBOL_META: dict[str, Any] = {}
    SYMBOL_MONTHS: dict[str, Any] = {}
    BY_CLASS: dict[str, Any] = {}
    BY_REGION: dict[str, Any] = {}
    MONTH_TOP: dict[int, list] = {m: [] for m in range(1, 13)}
    MONTH_TOP_BY_CLASS: dict[str, Any] = {}

MONTH_LABELS_PL = [
    "Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
    "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru",
]
MONTH_LABELS_EN = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _norm_sym(symbol: str) -> str:
    return symbol.strip()


def _resolve_symbol_key(symbol: str) -> str:
    """Match SYMBOL_MONTHS key (original case) or catalog uppercase."""
    s = _norm_sym(symbol)
    if s in SYMBOL_MONTHS or s in SYMBOL_META:
        return s
    upper = s.upper()
    for key in SYMBOL_MONTHS:
        if key.upper() == upper:
            return key
    for key in SYMBOL_META:
        if key.upper() == upper:
            return key
    cat = CATALOG_BY_SYMBOL.get(upper)
    if cat:
        return cat["symbol"]
    return s


def _catalog_meta(symbol: str) -> dict[str, str]:
    key = _resolve_symbol_key(symbol)
    if key in SYMBOL_META:
        return SYMBOL_META[key]
    a = CATALOG_BY_SYMBOL.get(key.upper()) or CATALOG_BY_SYMBOL.get(symbol.strip().upper()) or {}
    return {
        "name": a.get("name") or key,
        "asset_class": a.get("asset_class") or "stock",
        "region": a.get("region") or "global",
    }


def _month_row(month: int, cell: dict[str, Any] | None) -> dict[str, Any]:
    cell = cell or {}
    return {
        "month": month,
        "label_pl": MONTH_LABELS_PL[month - 1],
        "label_en": MONTH_LABELS_EN[month - 1],
        "avg_return_pct": cell.get("avg_pct"),
        "median_pct": cell.get("median_pct"),
        "win_rate": cell.get("win_rate"),
        "n": cell.get("n", 0),
        "bias": cell.get("bias", "neutral"),
    }


def symbol_calendar_month(
    symbol: str,
    month: int,
    asset_class: str | None = None,
    region: str | None = None,
) -> dict[str, Any] | None:
    """Lookup with symbol → class → region fallback."""
    if month < 1 or month > 12:
        return None
    key = _resolve_symbol_key(symbol)
    meta = _catalog_meta(key)
    cls = asset_class or meta.get("asset_class")
    reg = region or meta.get("region")
    sym_months = SYMBOL_MONTHS.get(key)
    if sym_months and sym_months.get(month) and sym_months[month].get("avg_pct") is not None:
        cell = sym_months[month]
        return {**_month_row(month, cell), "source": "symbol"}
    if cls and BY_CLASS.get(cls) and BY_CLASS[cls].get(month):
        cell = BY_CLASS[cls][month]
        if cell.get("avg_pct") is not None:
            return {**_month_row(month, cell), "source": f"class:{cls}"}
    if reg and BY_REGION.get(reg) and BY_REGION[reg].get(month):
        cell = BY_REGION[reg][month]
        if cell.get("avg_pct") is not None:
            return {**_month_row(month, cell), "source": f"region:{reg}"}
    return None


def get_instrument_calendar(symbol: str) -> dict[str, Any]:
    key = _resolve_symbol_key(symbol)
    meta = _catalog_meta(key)
    months_raw = SYMBOL_MONTHS.get(key) or {}
    months = []
    for m in range(1, 13):
        cell = months_raw.get(m)
        if cell and cell.get("avg_pct") is not None:
            months.append(_month_row(m, cell))
        else:
            fb = symbol_calendar_month(key, m, meta.get("asset_class"), meta.get("region"))
            if fb:
                months.append(fb)
            else:
                months.append(_month_row(m, None))

    scored = [m for m in months if m.get("avg_return_pct") is not None]
    strongest = sorted(scored, key=lambda x: x["avg_return_pct"], reverse=True)[:3]
    weakest = sorted(scored, key=lambda x: x["avg_return_pct"])[:3]
    top3_pos = [m for m in strongest if (m.get("avg_return_pct") or 0) > 0]
    pump_score = (
        round(sum(m["avg_return_pct"] for m in top3_pos) / len(top3_pos), 3)
        if top3_pos
        else None
    )
    best = strongest[0] if strongest else None
    worst = weakest[0] if weakest else None
    narrative = None
    if best and worst and best.get("avg_return_pct") is not None:
        narrative = (
            f"Historycznie najmocniej pompowany w {best['label_pl']} "
            f"({best['avg_return_pct']:+.2f}%), najsłabszy {worst['label_pl']} "
            f"({worst['avg_return_pct']:+.2f}%)."
        )

    return {
        "symbol": key,
        "name": meta.get("name") or key,
        "asset_class": meta.get("asset_class"),
        "region": meta.get("region"),
        "available": bool(scored),
        "source": "symbol" if key in SYMBOL_MONTHS else "fallback",
        "months": months,
        "strongest_months": strongest,
        "weakest_months": weakest,
        "pump_score": pump_score,
        "narrative": narrative,
        "generated_at": GENERATED_AT or META.get("generated_at"),
        "note": (
            "Średnie historyczne zwroty miesięczne (kalendarz). "
            "Nie gwarantują powtórzenia — edukacyjnie."
        ),
    }


def get_month_pumps(
    month: int,
    asset_class: str | None = None,
    region: str | None = None,
    limit: int = 25,
    direction: Literal["up", "down", "both"] = "both",
) -> dict[str, Any]:
    if month < 1 or month > 12:
        raise ValueError("month must be 1–12")
    limit = max(1, min(limit, 100))

    if asset_class:
        rows = list((MONTH_TOP_BY_CLASS.get(asset_class) or {}).get(month) or [])
    else:
        rows = list(MONTH_TOP.get(month) or [])

    if region:
        rows = [r for r in rows if r.get("region") == region]

    pumped = [r for r in rows if (r.get("avg_pct") or 0) > 0]
    drained = [r for r in rows if (r.get("avg_pct") or 0) < 0]
    drained_sorted = sorted(drained, key=lambda r: r.get("avg_pct") or 0)

    top = pumped[:limit] if direction in ("up", "both") else []
    bottom = drained_sorted[:limit] if direction in ("down", "both") else []

    def _map(e: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": e["symbol"],
            "name": e.get("name") or e["symbol"],
            "asset_class": e.get("asset_class"),
            "region": e.get("region"),
            "avg_return_pct": e.get("avg_pct"),
            "median_pct": e.get("median_pct"),
            "win_rate": e.get("win_rate"),
            "n": e.get("n"),
            "bias": e.get("bias"),
        }

    return {
        "month": month,
        "label_pl": MONTH_LABELS_PL[month - 1],
        "label_en": MONTH_LABELS_EN[month - 1],
        "asset_class": asset_class,
        "region": region,
        "pumped": [_map(e) for e in top],
        "drained": [_map(e) for e in bottom],
        "universe_n": len(rows),
        "generated_at": GENERATED_AT or META.get("generated_at"),
        "meta": META,
        "note": (
            f"Ranking historycznej sezonowości miesiąca {MONTH_LABELS_PL[month - 1]} "
            "w katalogu (stock/etf/bond/commodity/crypto/forex/index)."
        ),
    }


def month_pump_snippet(month: int, top_n: int = 3) -> dict[str, Any]:
    data = get_month_pumps(month, limit=top_n, direction="both")
    top = data["pumped"][:top_n]
    bottom = data["drained"][:top_n]
    parts_up = [
        f"{e['symbol']} ({e['avg_return_pct']:+.2f}%)"
        for e in top
        if e.get("avg_return_pct") is not None
    ]
    parts_down = [
        f"{e['symbol']} ({e['avg_return_pct']:+.2f}%)"
        for e in bottom
        if e.get("avg_return_pct") is not None
    ]
    text = (
        f"{data['label_pl']}: pompowane {', '.join(parts_up) or '—'}; "
        f"słabe {', '.join(parts_down) or '—'}."
    )
    return {
        "month": month,
        "label_pl": data["label_pl"],
        "label_en": data["label_en"],
        "text": text,
        "pumped": top,
        "drained": bottom,
    }


def search_catalog(query: str, limit: int = 20) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []
    # Prefer symbols that have seasonality matrices
    pool = list(SYMBOL_META.items())
    if not pool:
        pool = [
            (
                sym,
                {
                    "name": a.get("name") or sym,
                    "asset_class": a.get("asset_class"),
                    "region": a.get("region"),
                },
            )
            for sym, a in CATALOG_BY_SYMBOL.items()
            if a.get("asset_class") != "tokenized" and sym != "^VIX"
        ]
    for sym, meta in pool:
        name = (meta.get("name") or "").lower()
        if q in sym.lower() or q in name:
            hits.append(
                {
                    "symbol": sym,
                    "name": meta.get("name") or sym,
                    "asset_class": meta.get("asset_class"),
                    "region": meta.get("region"),
                    "has_calendar": sym in SYMBOL_MONTHS,
                }
            )
        if len(hits) >= limit:
            break
    return hits


def current_month_pumps_brief(as_of: date | None = None, top_n: int = 5) -> dict[str, Any]:
    m = (as_of or date.today()).month
    return month_pump_snippet(m, top_n=top_n)

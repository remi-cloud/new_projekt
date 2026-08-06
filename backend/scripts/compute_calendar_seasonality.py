#!/usr/bin/env python3
"""Compute plain calendar-month seasonality for the full monitored catalog.

Per symbol: avg/median/win_rate/n for months 1–12.
Also class/region fallbacks + MONTH_TOP leaderboards.

Excludes tokenized and ^VIX. Includes stocks, ETFs (sectors/utility/commodity),
bonds, commodities, crypto, forex, indices.

Usage (from backend/):
  PYTHONPATH=. .venv/bin/python scripts/compute_calendar_seasonality.py
"""

from __future__ import annotations

import json
import statistics
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.data.assets import MONITORED_ASSETS, resolve_yahoo_symbol

MIN_OBS = 6
MIN_RETS = 24
UA = "Mozilla/5.0 (compatible; CyclicalTraderCalendarSeasonality/1.0)"
OUT = Path(__file__).resolve().parents[1] / "app" / "cycles" / "calendar_seasonality_data.py"
SKIP_SYMBOLS = {"^VIX"}


def fetch_monthly_closes(symbol: str, start_year: int = 1985) -> list[tuple[date, float]]:
    yahoo = resolve_yahoo_symbol(symbol)
    encoded = urllib.parse.quote(yahoo, safe="")
    period1 = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={period1}&period2={period2}&interval=1mo&events=history"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode())
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return []
    r0 = result[0]
    ts = r0.get("timestamp") or []
    closes = ((r0.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    rows: list[tuple[date, float]] = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        rows.append((d, float(c)))
    rows.sort()
    return rows


def monthly_returns(rows: list[tuple[date, float]]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for i in range(1, len(rows)):
        _d0, c0 = rows[i - 1]
        d1, c1 = rows[i]
        if c0 <= 0:
            continue
        out.append((d1, (c1 / c0 - 1.0) * 100.0))
    return out


def summarize_month(vals: list[float]) -> dict[str, Any]:
    if len(vals) < MIN_OBS:
        return {
            "avg_pct": None,
            "median_pct": None,
            "win_rate": None,
            "n": len(vals),
            "bias": "neutral",
        }
    avg = sum(vals) / len(vals)
    med = statistics.median(vals)
    win = sum(1 for v in vals if v >= 0) / len(vals)
    return {
        "avg_pct": round(avg, 3),
        "median_pct": round(med, 3),
        "win_rate": round(win, 3),
        "n": len(vals),
        "bias": "up" if avg >= 0 else "down",
    }


def empty_months() -> dict[int, dict[str, Any]]:
    return {m: summarize_month([]) for m in range(1, 13)}


def py_literal(obj: Any, indent: int = 0) -> str:
    sp = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        for k, v in obj.items():
            key = repr(k) if isinstance(k, str) else str(k)
            lines.append(f"{sp}    {key}: {py_literal(v, indent + 4)},")
        lines.append(f"{sp}}}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = ["["]
        for item in obj:
            lines.append(f"{sp}    {py_literal(item, indent + 4)},")
        lines.append(f"{sp}]")
        return "\n".join(lines)
    return repr(obj)


def main() -> None:
    assets = [
        a
        for a in MONITORED_ASSETS
        if a.get("asset_class") != "tokenized" and a["symbol"] not in SKIP_SYMBOLS
    ]
    print(f"Calendar seasonality candidates: {len(assets)}")

    symbol_months: dict[str, dict[int, dict[str, Any]]] = {}
    meta: dict[str, dict[str, str]] = {}
    class_buckets: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    region_buckets: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    for i, asset in enumerate(assets, start=1):
        sym = asset["symbol"]
        cls = asset["asset_class"]
        region = asset.get("region") or "global"
        start_year = 2014 if cls == "crypto" else 1985
        try:
            rows = fetch_monthly_closes(sym, start_year)
            rets = monthly_returns(rows)
            if len(rets) < MIN_RETS:
                print(f"[{i}/{len(assets)}] {sym}: skip n={len(rets)}")
                time.sleep(0.08)
                continue
            buckets: dict[int, list[float]] = defaultdict(list)
            for d, pct in rets:
                buckets[d.month].append(pct)
            months = {}
            for m in range(1, 13):
                cell = summarize_month(buckets.get(m) or [])
                months[m] = cell
                if cell["avg_pct"] is not None:
                    class_buckets[cls][m].append(cell["avg_pct"])
                    region_buckets[region][m].append(cell["avg_pct"])
            symbol_months[sym] = months
            meta[sym] = {
                "name": asset.get("name") or sym,
                "asset_class": cls,
                "region": region,
            }
            print(f"[{i}/{len(assets)}] {sym}: ok n={len(rets)}")
        except Exception as exc:
            print(f"[{i}/{len(assets)}] {sym}: ERR {exc}")
        time.sleep(0.1)

    by_class: dict[str, dict[int, dict[str, Any]]] = {}
    for cls, mb in class_buckets.items():
        by_class[cls] = {m: summarize_month(mb.get(m) or []) for m in range(1, 13)}

    by_region: dict[str, dict[int, dict[str, Any]]] = {}
    for region, mb in region_buckets.items():
        by_region[region] = {m: summarize_month(mb.get(m) or []) for m in range(1, 13)}

    # Leaderboards: all + per class
    month_top: dict[int, list[dict[str, Any]]] = {}
    month_top_by_class: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(dict)

    for m in range(1, 13):
        rows_all: list[dict[str, Any]] = []
        by_cls_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sym, months in symbol_months.items():
            cell = months[m]
            if cell["avg_pct"] is None:
                continue
            entry = {
                "symbol": sym,
                "name": meta[sym]["name"],
                "asset_class": meta[sym]["asset_class"],
                "region": meta[sym]["region"],
                "avg_pct": cell["avg_pct"],
                "median_pct": cell["median_pct"],
                "win_rate": cell["win_rate"],
                "n": cell["n"],
                "bias": cell["bias"],
            }
            rows_all.append(entry)
            by_cls_rows[meta[sym]["asset_class"]].append(entry)
        rows_all.sort(key=lambda e: e["avg_pct"], reverse=True)
        month_top[m] = rows_all
        for cls, lst in by_cls_rows.items():
            lst.sort(key=lambda e: e["avg_pct"], reverse=True)
            month_top_by_class[cls][m] = lst

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "generated_at": generated,
        "symbols_included": len(symbol_months),
        "symbols_total": len(assets),
        "min_obs": MIN_OBS,
        "classes": sorted(by_class.keys()),
        "regions": sorted(by_region.keys()),
    }

    body = f'''"""AUTO-GENERATED by scripts/compute_calendar_seasonality.py — do not edit by hand.

Plain calendar-month seasonality for the monitored catalog (ex tokenized/^VIX).

Generated: {generated}
Symbols: {len(symbol_months)}/{len(assets)}
"""

from __future__ import annotations

GENERATED_AT = {generated!r}
META = {py_literal(summary)}
SYMBOL_META = {py_literal(meta)}
SYMBOL_MONTHS = {py_literal(symbol_months)}
BY_CLASS = {py_literal(by_class)}
BY_REGION = {py_literal(by_region)}
MONTH_TOP = {py_literal(month_top)}
MONTH_TOP_BY_CLASS = {py_literal(dict(month_top_by_class))}
'''
    OUT.write_text(body, encoding="utf-8")
    print(f"\nWrote {OUT}")
    print(f"Included {len(symbol_months)} symbols")
    if 11 in month_top and month_top[11]:
        print("Nov top5:", [(e["symbol"], e["avg_pct"]) for e in month_top[11][:5]])
        print("Nov bottom5:", [(e["symbol"], e["avg_pct"]) for e in month_top[11][-5:]])


if __name__ == "__main__":
    main()

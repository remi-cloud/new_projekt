#!/usr/bin/env python3
"""Compute presidential year×month seasonality across the US catalog.

Equal-weight aggregate + per-class + per-symbol matrices.
Writes backend/app/cycles/presidential_seasonality_data.py

Usage (from backend/):
  PYTHONPATH=. .venv/bin/python scripts/compute_presidential_monthly.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from app.data.assets import MONITORED_ASSETS, resolve_yahoo_symbol

MIN_OBS = 6
UA = "Mozilla/5.0 (compatible; CyclicalTraderSeasonality/1.0)"
OUT = Path(__file__).resolve().parents[1] / "app" / "cycles" / "presidential_seasonality_data.py"


def year_of_term(as_of: date) -> int:
    """Inauguration years ≡ 1 mod 4 (1953, 1957, …, 2025)."""
    y = as_of.year if (as_of.month, as_of.day) >= (1, 20) else as_of.year - 1
    while y % 4 != 1:
        y -= 1
    term_start = date(y, 1, 20)
    years_elapsed = as_of.year - term_start.year
    if (as_of.month, as_of.day) < (1, 20):
        years_elapsed -= 1
    return min(max(years_elapsed + 1, 1), 4)


def fetch_monthly_closes(symbol: str) -> list[tuple[date, float]]:
    yahoo = resolve_yahoo_symbol(symbol)
    encoded = urllib.parse.quote(yahoo, safe="")
    period1 = int(datetime(1985, 1, 1, tzinfo=timezone.utc).timestamp())
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


def empty_matrix() -> dict[int, dict[int, float]]:
    return {y: {m: 0.0 for m in range(1, 13)} for y in range(1, 5)}


def avg_matrix(buckets: dict[tuple[int, int], list[float]]) -> dict[int, dict[int, float]]:
    mat = empty_matrix()
    for y in range(1, 5):
        for m in range(1, 13):
            vals = buckets.get((y, m)) or []
            if vals:
                mat[y][m] = round(sum(vals) / len(vals), 2)
            else:
                mat[y][m] = 0.0
    return mat


def main() -> None:
    us_assets = [
        a
        for a in MONITORED_ASSETS
        if a.get("region") == "us" and a.get("asset_class") != "tokenized"
    ]
    us_assets = [a for a in us_assets if a["symbol"] not in ("^VIX",)]

    print(f"US symbols: {len(us_assets)}")
    symbol_mats: dict[str, dict[int, dict[int, float]]] = {}
    class_buckets: dict[str, dict[tuple[int, int], list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    cell_symbol_avgs: dict[tuple[int, int], list[float]] = defaultdict(list)

    for i, asset in enumerate(us_assets, start=1):
        sym = asset["symbol"]
        cls = asset["asset_class"]
        try:
            rows = fetch_monthly_closes(sym)
            rets = monthly_returns(rows)
            if len(rets) < 24:
                print(f"[{i}/{len(us_assets)}] {sym}: skip (n={len(rets)})")
                time.sleep(0.12)
                continue
            buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
            for d, pct in rets:
                if d < date(1985, 1, 20):
                    continue
                yot = year_of_term(d)
                buckets[(yot, d.month)].append(pct)
                class_buckets[cls][(yot, d.month)].append(pct)
            mat = avg_matrix(buckets)
            symbol_mats[sym] = mat
            for y in range(1, 5):
                for m in range(1, 13):
                    vals = buckets.get((y, m)) or []
                    if len(vals) >= MIN_OBS:
                        cell_symbol_avgs[(y, m)].append(sum(vals) / len(vals))
            print(f"[{i}/{len(us_assets)}] {sym}: ok months={len(rets)}")
        except Exception as exc:
            print(f"[{i}/{len(us_assets)}] {sym}: FAIL {exc}")
        time.sleep(0.15)

    universe = empty_matrix()
    for y in range(1, 5):
        for m in range(1, 13):
            vals = cell_symbol_avgs.get((y, m)) or []
            universe[y][m] = round(sum(vals) / len(vals), 2) if vals else 0.0

    classes = {cls: avg_matrix(b) for cls, b in class_buckets.items()}

    lines = [
        '"""Auto-generated US presidential seasonality matrices.',
        "",
        "Equal-weight across region=us catalog (excl. tokenized, ^VIX).",
        f"Generated: {datetime.now(timezone.utc).date().isoformat()}",
        f"Symbols with history: {len(symbol_mats)}",
        '"""',
        "",
        f"SEASONALITY_UNIVERSE_SIZE = {len(symbol_mats)}",
        "",
        "# year_of_term 1..4 → month 1..12 → avg return %",
        f"US_UNIVERSE_MONTHLY_RETURNS = {repr(universe)}",
        "",
        f"US_CLASS_MONTHLY_RETURNS = {repr(classes)}",
        "",
        f"US_SYMBOL_MONTHLY_RETURNS = {repr(symbol_mats)}",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    for y in range(1, 5):
        s = sum(universe[y].values())
        print(f"Universe Y{y} sum≈{s:.1f}%")


if __name__ == "__main__":
    main()

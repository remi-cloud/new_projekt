#!/usr/bin/env python3
"""Compute intra-month seasonality: day-of-month (1–31) + week-of-month (1–4).

Universes:
  - US equal-weight catalog (same filter as presidential monthly)
  - BTC-USD

Writes backend/app/cycles/intramonth_seasonality_data.py

Usage (from backend/):
  PYTHONPATH=. .venv/bin/python scripts/compute_intramonth_seasonality.py
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

MIN_OBS = 8
UA = "Mozilla/5.0 (compatible; CyclicalTraderIntramonth/1.0)"
OUT = Path(__file__).resolve().parents[1] / "app" / "cycles" / "intramonth_seasonality_data.py"


def week_of_month(day: int) -> int:
    """1–7 → W1, 8–14 → W2, 15–21 → W3, 22–31 → W4."""
    return min(4, ((day - 1) // 7) + 1)


def fetch_daily_closes(symbol: str, start_year: int = 2000) -> list[tuple[date, float]]:
    yahoo = resolve_yahoo_symbol(symbol)
    encoded = urllib.parse.quote(yahoo, safe="")
    period1 = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
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


def daily_returns(rows: list[tuple[date, float]]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for i in range(1, len(rows)):
        _d0, c0 = rows[i - 1]
        d1, c1 = rows[i]
        if c0 <= 0:
            continue
        # Skip weekend gaps is fine; Yahoo daily is trading days only
        out.append((d1, (c1 / c0 - 1.0) * 100.0))
    return out


def accumulate(
    rets: list[tuple[date, float]],
    day_buckets: dict[tuple[int, int], list[float]],
    week_buckets: dict[tuple[int, int], list[float]],
) -> None:
    for d, r in rets:
        day_buckets[(d.month, d.day)].append(r)
        week_buckets[(d.month, week_of_month(d.day))].append(r)


def finalize_universe(
    day_buckets: dict[tuple[int, int], list[float]],
    week_buckets: dict[tuple[int, int], list[float]],
) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for m in range(1, 13):
        days: dict[int, dict] = {}
        for day in range(1, 32):
            vals = day_buckets.get((m, day)) or []
            if len(vals) >= MIN_OBS:
                days[day] = {
                    "avg_pct": round(sum(vals) / len(vals), 3),
                    "n": len(vals),
                    "bias": "up" if sum(vals) / len(vals) >= 0 else "down",
                }
            else:
                days[day] = {"avg_pct": None, "n": len(vals), "bias": "neutral"}
        weeks: dict[int, dict] = {}
        for w in range(1, 5):
            vals = week_buckets.get((m, w)) or []
            if len(vals) >= MIN_OBS:
                avg = sum(vals) / len(vals)
                weeks[w] = {
                    "avg_pct": round(avg, 3),
                    "n": len(vals),
                    "bias": "up" if avg >= 0 else "down",
                    "days": f"{(w - 1) * 7 + 1}-{31 if w == 4 else w * 7}",
                }
            else:
                weeks[w] = {
                    "avg_pct": None,
                    "n": len(vals),
                    "bias": "neutral",
                    "days": f"{(w - 1) * 7 + 1}-{31 if w == 4 else w * 7}",
                }
        out[m] = {"days": days, "weeks": weeks}
    return out


def py_repr_universe(name: str, data: dict[int, dict]) -> str:
    lines = [f"{name}: dict[int, dict] = {{"]
    for m in range(1, 13):
        lines.append(f"    {m}: {{")
        days = data[m]["days"]
        d_parts = []
        for day in range(1, 32):
            cell = days[day]
            d_parts.append(
                f"{day}: {{'avg_pct': {cell['avg_pct']!r}, 'n': {cell['n']}, 'bias': {cell['bias']!r}}}"
            )
        lines.append(f"        'days': {{{', '.join(d_parts)}}},")
        w_parts = []
        for w in range(1, 5):
            cell = data[m]["weeks"][w]
            w_parts.append(
                f"{w}: {{'avg_pct': {cell['avg_pct']!r}, 'n': {cell['n']}, "
                f"'bias': {cell['bias']!r}, 'days': {cell['days']!r}}}"
            )
        lines.append(f"        'weeks': {{{', '.join(w_parts)}}},")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    us_assets = [
        a
        for a in MONITORED_ASSETS
        if a.get("region") == "us"
        and a.get("asset_class") != "tokenized"
        and a["symbol"] not in ("^VIX",)
    ]
    print(f"US symbols: {len(us_assets)}")

    # Per-symbol averages first, then equal-weight across symbols (reduces mega-cap bias of pooling)
    us_day_sym: dict[tuple[int, int], list[float]] = defaultdict(list)
    us_week_sym: dict[tuple[int, int], list[float]] = defaultdict(list)
    included = 0

    for i, asset in enumerate(us_assets, start=1):
        sym = asset["symbol"]
        try:
            rows = fetch_daily_closes(sym, 2000)
            rets = daily_returns(rows)
            if len(rets) < 250:
                print(f"[{i}/{len(us_assets)}] {sym}: skip n={len(rets)}")
                time.sleep(0.1)
                continue
            local_day: dict[tuple[int, int], list[float]] = defaultdict(list)
            local_week: dict[tuple[int, int], list[float]] = defaultdict(list)
            accumulate(rets, local_day, local_week)
            for key, vals in local_day.items():
                if len(vals) >= 3:
                    us_day_sym[key].append(sum(vals) / len(vals))
            for key, vals in local_week.items():
                if len(vals) >= 5:
                    us_week_sym[key].append(sum(vals) / len(vals))
            included += 1
            print(f"[{i}/{len(us_assets)}] {sym}: ok bars={len(rets)}")
        except Exception as exc:
            print(f"[{i}/{len(us_assets)}] {sym}: ERR {exc}")
        time.sleep(0.12)

    # Convert symbol-level lists into bucket lists for finalize
    us_day_buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    us_week_buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for k, vals in us_day_sym.items():
        us_day_buckets[k] = vals
    for k, vals in us_week_sym.items():
        us_week_buckets[k] = vals

    us_data = finalize_universe(us_day_buckets, us_week_buckets)

    print("Fetching BTC-USD…")
    btc_day: dict[tuple[int, int], list[float]] = defaultdict(list)
    btc_week: dict[tuple[int, int], list[float]] = defaultdict(list)
    btc_rows = fetch_daily_closes("BTC-USD", 2014)
    btc_rets = daily_returns(btc_rows)
    accumulate(btc_rets, btc_day, btc_week)
    btc_data = finalize_universe(btc_day, btc_week)
    print(f"BTC bars={len(btc_rows)} rets={len(btc_rets)}")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f'''"""AUTO-GENERATED by scripts/compute_intramonth_seasonality.py — do not edit by hand.

Generated: {generated}
US symbols included: {included}
"""

from __future__ import annotations

GENERATED_AT = {generated!r}
US_INTRAMONTH_UNIVERSE_SIZE = {included}
MIN_OBS = {MIN_OBS}

# calendar_month -> days[1..31] / weeks[1..4]
{py_repr_universe("US_INTRAMONTH", us_data)}

{py_repr_universe("BTC_INTRAMONTH", btc_data)}
'''
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT}")

    # Quick sanity
    aug_w = us_data[8]["weeks"]
    print("US Aug weeks:", {w: aug_w[w]["avg_pct"] for w in range(1, 5)})
    print("BTC Aug weeks:", {w: btc_data[8]["weeks"][w]["avg_pct"] for w in range(1, 5)})


if __name__ == "__main__":
    main()

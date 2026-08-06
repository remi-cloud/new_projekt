#!/usr/bin/env python3
"""Field scouts: global seasonality (monthly / week-of-month / yearly windows).

Same rules across markets — equal-weight equity+index per region + crypto basket.
Compares patterns; writes adoption order book of cycles that reproduce.

Universes: us, eu, asia, em, pl, crypto

Usage (from backend/):
  PYTHONPATH=. .venv/bin/python scripts/compute_global_cycle_book.py
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.data.assets import MONITORED_ASSETS, resolve_yahoo_symbol

MIN_MONTH_OBS = 8
MIN_WEEK_OBS = 20
MIN_SYM_BARS = 250
UA = "Mozilla/5.0 (compatible; CyclicalTraderGlobalBook/1.0)"
OUT = Path(__file__).resolve().parents[1] / "app" / "cycles" / "global_cycle_book_data.py"

# Sell-in-May window (May–Oct) vs Best-Six style (Nov–Apr)
BEST_SIX = {11, 12, 1, 2, 3, 4}
SELL_MAY = {5, 6, 7, 8, 9, 10}

REGION_LABELS = {
    "us": "USA",
    "eu": "Europa",
    "asia": "Azja",
    "em": "EM",
    "pl": "Polska",
    "crypto": "Crypto",
}

ADOPT_MIN_MARKETS = 4
ADOPT_MONTH_ABS = 0.12  # %
ADOPT_WEEK_ABS = 0.015
ADOPT_YEAR_EDGE = 0.25  # Best-Six minus Sell-May average edge (pp)


def week_of_month(day: int) -> int:
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
        out.append((d1, (c1 / c0 - 1.0) * 100.0))
    return out


def symbols_for_universe(universe: str) -> list[str]:
    if universe == "crypto":
        return [
            a["symbol"]
            for a in MONITORED_ASSETS
            if a.get("asset_class") == "crypto"
        ]
    skip = {"^VIX"}
    out: list[str] = []
    for a in MONITORED_ASSETS:
        if a.get("region") != universe:
            continue
        if a.get("asset_class") not in ("stock", "etf", "index"):
            continue
        if a["symbol"] in skip:
            continue
        out.append(a["symbol"])
    return out


def pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 3:
        return None
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da < 1e-12 or db < 1e-12:
        return None
    return num / (da * db)


def scout_universe(universe: str, symbols: list[str]) -> dict[str, Any]:
    """Equal-weight month / week-of-month / yearly-window profile."""
    month_sym: dict[int, list[float]] = defaultdict(list)
    week_sym: dict[int, list[float]] = defaultdict(list)
    included = 0
    start_year = 2014 if universe == "crypto" else 2000

    for i, sym in enumerate(symbols, start=1):
        try:
            rows = fetch_daily_closes(sym, start_year)
            rets = daily_returns(rows)
            if len(rets) < MIN_SYM_BARS:
                print(f"  [{universe}] [{i}/{len(symbols)}] {sym}: skip n={len(rets)}")
                time.sleep(0.08)
                continue
            local_m: dict[int, list[float]] = defaultdict(list)
            local_w: dict[int, list[float]] = defaultdict(list)
            for d, r in rets:
                local_m[d.month].append(r)
                local_w[week_of_month(d.day)].append(r)
            for m, vals in local_m.items():
                if len(vals) >= 10:
                    month_sym[m].append(sum(vals) / len(vals))
            for w, vals in local_w.items():
                if len(vals) >= 20:
                    week_sym[w].append(sum(vals) / len(vals))
            included += 1
            print(f"  [{universe}] [{i}/{len(symbols)}] {sym}: ok bars={len(rets)}")
        except Exception as exc:
            print(f"  [{universe}] [{i}/{len(symbols)}] {sym}: ERR {exc}")
        time.sleep(0.1)

    months: dict[int, dict[str, Any]] = {}
    for m in range(1, 13):
        vals = month_sym.get(m) or []
        if len(vals) >= max(3, min(MIN_MONTH_OBS, len(symbols) // 3 or 1)):
            avg = sum(vals) / len(vals)
            months[m] = {
                "avg_pct": round(avg, 3),
                "n": len(vals),
                "bias": "up" if avg >= 0 else "down",
            }
        else:
            months[m] = {"avg_pct": None, "n": len(vals), "bias": "neutral"}

    weeks: dict[int, dict[str, Any]] = {}
    for w in range(1, 5):
        vals = week_sym.get(w) or []
        if len(vals) >= 3:
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

    best_vals = [months[m]["avg_pct"] for m in BEST_SIX if months[m]["avg_pct"] is not None]
    sell_vals = [months[m]["avg_pct"] for m in SELL_MAY if months[m]["avg_pct"] is not None]
    best_avg = sum(best_vals) / len(best_vals) if best_vals else None
    sell_avg = sum(sell_vals) / len(sell_vals) if sell_vals else None
    edge = None
    if best_avg is not None and sell_avg is not None:
        edge = round(best_avg - sell_avg, 3)

    return {
        "label": REGION_LABELS[universe],
        "symbols_included": included,
        "symbols_total": len(symbols),
        "months": months,
        "weeks": weeks,
        "yearly": {
            "best_six_avg_pct": round(best_avg, 3) if best_avg is not None else None,
            "sell_may_avg_pct": round(sell_avg, 3) if sell_avg is not None else None,
            "best_six_edge_pct": edge,
            "bias": (
                "best_six"
                if edge is not None and edge >= 0
                else "sell_may"
                if edge is not None
                else "neutral"
            ),
        },
    }


def month_vector(profile: dict[str, Any]) -> list[float]:
    return [
        float(profile["months"][m]["avg_pct"] or 0.0)
        for m in range(1, 13)
    ]


def week_vector(profile: dict[str, Any]) -> list[float]:
    return [
        float(profile["weeks"][w]["avg_pct"] or 0.0)
        for w in range(1, 5)
    ]


def mean_pairwise_corr(vectors: dict[str, list[float]]) -> float | None:
    keys = list(vectors.keys())
    pairs: list[float] = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            c = pearson(vectors[keys[i]], vectors[keys[j]])
            if c is not None:
                pairs.append(c)
    if not pairs:
        return None
    return sum(pairs) / len(pairs)


def build_order_book(profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Adoption order book: bids (historically up) / asks (historically down)."""
    book: list[dict[str, Any]] = []
    universes = list(profiles.keys())

    # ── Monthly slots ──
    for m in range(1, 13):
        agreeing_up: list[str] = []
        agreeing_down: list[str] = []
        rets: list[float] = []
        for u in universes:
            cell = profiles[u]["months"][m]
            v = cell["avg_pct"]
            if v is None:
                continue
            rets.append(v)
            if v >= 0:
                agreeing_up.append(u)
            else:
                agreeing_down.append(u)
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        if len(agreeing_up) >= ADOPT_MIN_MARKETS and abs(avg) >= ADOPT_MONTH_ABS:
            side, markets, status = "bid", agreeing_up, "adopted"
        elif len(agreeing_down) >= ADOPT_MIN_MARKETS and abs(avg) >= ADOPT_MONTH_ABS:
            side, markets, status = "ask", agreeing_down, "adopted"
        elif len(agreeing_up) >= 3 or len(agreeing_down) >= 3:
            side = "bid" if avg >= 0 else "ask"
            markets = agreeing_up if side == "bid" else agreeing_down
            status = "watch"
        else:
            side = "bid" if avg >= 0 else "ask"
            markets = agreeing_up if side == "bid" else agreeing_down
            status = "rejected"
        score = round(len(markets) / len(universes), 3)
        book.append(
            {
                "id": f"month:{m:02d}",
                "horizon": "monthly",
                "slot": m,
                "slot_label": f"M{m}",
                "side": side,
                "avg_return_pct": round(avg, 3),
                "markets": markets,
                "markets_n": len(markets),
                "markets_total": len(universes),
                "reproduction_score": score,
                "status": status,
            }
        )

    # ── Week-of-month slots (pooled across months) ──
    for w in range(1, 5):
        agreeing_up: list[str] = []
        agreeing_down: list[str] = []
        rets: list[float] = []
        for u in universes:
            cell = profiles[u]["weeks"][w]
            v = cell["avg_pct"]
            if v is None:
                continue
            rets.append(v)
            if v >= 0:
                agreeing_up.append(u)
            else:
                agreeing_down.append(u)
        if not rets:
            continue
        avg = sum(rets) / len(rets)
        days = profiles[universes[0]]["weeks"][w]["days"]
        if len(agreeing_up) >= ADOPT_MIN_MARKETS and abs(avg) >= ADOPT_WEEK_ABS:
            side, markets, status = "bid", agreeing_up, "adopted"
        elif len(agreeing_down) >= ADOPT_MIN_MARKETS and abs(avg) >= ADOPT_WEEK_ABS:
            side, markets, status = "ask", agreeing_down, "adopted"
        elif len(agreeing_up) >= 3 or len(agreeing_down) >= 3:
            side = "bid" if avg >= 0 else "ask"
            markets = agreeing_up if side == "bid" else agreeing_down
            status = "watch"
        else:
            side = "bid" if avg >= 0 else "ask"
            markets = agreeing_up if side == "bid" else agreeing_down
            status = "rejected"
        book.append(
            {
                "id": f"week:W{w}",
                "horizon": "weekly",
                "slot": w,
                "slot_label": f"W{w} ({days})",
                "side": side,
                "avg_return_pct": round(avg, 3),
                "markets": markets,
                "markets_n": len(markets),
                "markets_total": len(universes),
                "reproduction_score": round(len(markets) / len(universes), 3),
                "status": status,
            }
        )

    # ── Yearly window: Best Six vs Sell in May ──
    best_supporters: list[str] = []
    edges: list[float] = []
    for u in universes:
        edge = profiles[u]["yearly"].get("best_six_edge_pct")
        if edge is None:
            continue
        edges.append(edge)
        if edge >= 0:
            best_supporters.append(u)
    if edges:
        avg_edge = sum(edges) / len(edges)
        if len(best_supporters) >= ADOPT_MIN_MARKETS and avg_edge >= ADOPT_YEAR_EDGE:
            status = "adopted"
            side = "bid"
        elif len(best_supporters) >= 3:
            status = "watch"
            side = "bid" if avg_edge >= 0 else "ask"
        else:
            status = "rejected"
            side = "bid" if avg_edge >= 0 else "ask"
        book.append(
            {
                "id": "yearly:best_six",
                "horizon": "yearly",
                "slot": 0,
                "slot_label": "Best Six (Nov–Apr) vs Sell-May",
                "side": side,
                "avg_return_pct": round(avg_edge, 3),
                "markets": best_supporters if side == "bid" else [
                    u for u in universes if u not in best_supporters
                ],
                "markets_n": len(best_supporters) if side == "bid" else len(universes) - len(best_supporters),
                "markets_total": len(universes),
                "reproduction_score": round(len(best_supporters) / len(universes), 3),
                "status": status,
            }
        )

    # Rank: adopted first, then by reproduction × |return|
    def rank_key(e: dict[str, Any]) -> tuple:
        pri = {"adopted": 0, "watch": 1, "rejected": 2}.get(e["status"], 9)
        return (pri, -e["reproduction_score"] * abs(e["avg_return_pct"] or 0))

    book.sort(key=rank_key)
    for i, e in enumerate(book, start=1):
        e["rank"] = i
    return book


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
    universes = ["us", "eu", "asia", "em", "pl", "crypto"]
    profiles: dict[str, dict[str, Any]] = {}

    print("=== FIELD SCOUTS: global cycle discovery ===")
    for u in universes:
        syms = symbols_for_universe(u)
        print(f"\n→ Scout {u}: {len(syms)} candidates")
        profiles[u] = scout_universe(u, syms)

    # Cross-market profile correlations
    month_vecs = {u: month_vector(profiles[u]) for u in universes}
    week_vecs = {u: week_vector(profiles[u]) for u in universes}
    month_corr = mean_pairwise_corr(month_vecs)
    week_corr = mean_pairwise_corr(week_vecs)

    pairwise_month: dict[str, float] = {}
    for i, a in enumerate(universes):
        for b in universes[i + 1 :]:
            c = pearson(month_vecs[a], month_vecs[b])
            if c is not None:
                pairwise_month[f"{a}|{b}"] = round(c, 3)

    book = build_order_book(profiles)
    adopted = [e for e in book if e["status"] == "adopted"]
    watch = [e for e in book if e["status"] == "watch"]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "generated_at": generated,
        "universes": universes,
        "adopt_min_markets": ADOPT_MIN_MARKETS,
        "adopt_month_abs_pct": ADOPT_MONTH_ABS,
        "adopt_week_abs_pct": ADOPT_WEEK_ABS,
        "adopt_year_edge_pct": ADOPT_YEAR_EDGE,
        "mean_month_corr": round(month_corr, 3) if month_corr is not None else None,
        "mean_week_corr": round(week_corr, 3) if week_corr is not None else None,
        "adopted_n": len(adopted),
        "watch_n": len(watch),
        "book_n": len(book),
    }

    # Slim profiles for the data file (months/weeks/yearly + sizes)
    slim_profiles = {
        u: {
            "label": profiles[u]["label"],
            "symbols_included": profiles[u]["symbols_included"],
            "symbols_total": profiles[u]["symbols_total"],
            "months": profiles[u]["months"],
            "weeks": profiles[u]["weeks"],
            "yearly": profiles[u]["yearly"],
        }
        for u in universes
    }

    body = f'''"""AUTO-GENERATED by scripts/compute_global_cycle_book.py — do not edit by hand.

Field scouts compared monthly / week-of-month / Best-Six patterns across
us, eu, asia, em, pl, crypto. Adopted = reproduced on ≥{ADOPT_MIN_MARKETS} markets.

Generated: {generated}
"""

from __future__ import annotations

GENERATED_AT = {generated!r}
META = {py_literal(meta)}
PROFILES = {py_literal(slim_profiles)}
PAIRWISE_MONTH_CORR = {py_literal(pairwise_month)}
ORDER_BOOK = {py_literal(book)}
'''
    OUT.write_text(body, encoding="utf-8")
    print(f"\nWrote {OUT}")
    print(f"Adopted={len(adopted)} watch={len(watch)} book={len(book)}")
    print(f"Mean month corr={meta['mean_month_corr']} week corr={meta['mean_week_corr']}")
    print("Top adopted:")
    for e in adopted[:8]:
        print(f"  {e['id']} {e['side']} {e['avg_return_pct']}% markets={e['markets']}")


if __name__ == "__main__":
    main()

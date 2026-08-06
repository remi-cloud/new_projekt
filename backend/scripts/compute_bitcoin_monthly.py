#!/usr/bin/env python3
"""Compute BTC calendar + ATH-phase×month seasonality and BTC vs S&P comparison.

Writes:
  backend/app/cycles/bitcoin_seasonality_data.py
  docs/BTC-SEASONALITY.md  (repo root)

Usage (from backend/):
  PYTHONPATH=. .venv/bin/python scripts/compute_bitcoin_monthly.py
"""

from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

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
UA = "Mozilla/5.0 (compatible; CyclicalTraderBtcSeasonality/1.0)"

BACKEND = Path(__file__).resolve().parents[1]
OUT_PY = BACKEND / "app" / "cycles" / "bitcoin_seasonality_data.py"
OUT_MD = BACKEND.parent / "docs" / "BTC-SEASONALITY.md"
OUT_JSON = BACKEND / "data" / "btc_seasonality_debug.json"


def year_of_term(as_of: date) -> int:
    y = as_of.year if (as_of.month, as_of.day) >= (1, 20) else as_of.year - 1
    while y % 4 != 1:
        y -= 1
    term_start = date(y, 1, 20)
    years_elapsed = as_of.year - term_start.year
    if (as_of.month, as_of.day) < (1, 20):
        years_elapsed -= 1
    return min(max(years_elapsed + 1, 1), 4)


def fetch_monthly(symbol: str, start_year: int = 2010) -> list[tuple[date, float, float]]:
    """Return list of (date, close, high)."""
    encoded = urllib.parse.quote(symbol, safe="")
    period1 = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={period1}&period2={period2}&interval=1mo&events=history"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return []
    r0 = result[0]
    ts = r0.get("timestamp") or []
    quote = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    highs = quote.get("high") or []
    rows: list[tuple[date, float, float]] = []
    for i, t in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        h = highs[i] if i < len(highs) else None
        if c is None:
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        hi = float(h) if h is not None else float(c)
        rows.append((d, float(c), hi))
    rows.sort()
    return rows


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


def py_repr_matrix(avgs: dict[str, dict[int, float | None]]) -> str:
    lines = ["{"]
    for ph in PHASE_KEYS:
        inner = ", ".join(
            f"{m}: {avgs[ph][m]!r}" for m in range(1, 13)
        )
        lines.append(f"    {ph!r}: {{{inner}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    print("Fetching BTC-USD…")
    btc_rows = fetch_monthly("BTC-USD", 2010)
    print(f"  bars={len(btc_rows)}")
    print("Fetching ^GSPC…")
    spx_rows = fetch_monthly("^GSPC", 2010)
    print(f"  bars={len(spx_rows)}")

    btc_rets = monthly_returns(btc_rows)
    spx_rets = monthly_returns(spx_rows)
    btc_cal = calendar_stats(btc_rets)
    spx_cal = calendar_stats(spx_rets)
    btc_best, btc_worst = best_six_avg(btc_cal)
    spx_best, spx_worst = best_six_avg(spx_cal)
    best_six_delta = round(btc_best - spx_best, 2)

    pairs = aligned_pairs(btc_rets, spx_rets)
    corr_full = pearson([p[1] for p in pairs], [p[2] for p in pairs])
    roll = rolling_corr(pairs, 24)
    roll_latest = roll[-1][1] if roll else None
    roll_avg = round(statistics.mean([c for _, c in roll]), 3) if roll else None

    sign_agree = sum(
        1
        for m in range(1, 13)
        if (btc_cal[m]["avg_pct"] >= 0) == (spx_cal[m]["avg_pct"] >= 0)
    )

    labeled = attach_phases(btc_rows, btc_rets)
    phase_avgs, phase_ns = phase_month_matrix(labeled)
    # Convert for writing: keep None
    phase_avgs_ser = {
        ph: {m: phase_avgs[ph].get(m) for m in range(1, 13)} for ph in PHASE_KEYS
    }

    btc_term = term_year_avgs(btc_rets)
    spx_term = term_year_avgs(spx_rets)

    v, regime = verdict(corr_full, sign_agree, best_six_delta, roll_latest)

    cal_avgs = {m: btc_cal[m]["avg_pct"] for m in range(1, 13)}
    cal_ns = {m: btc_cal[m]["n"] for m in range(1, 13)}
    spx_avgs = {m: spx_cal[m]["avg_pct"] for m in range(1, 13)}

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "generated_at": generated,
        "btc_bars": len(btc_rows),
        "spx_bars": len(spx_rows),
        "aligned_months": len(pairs),
        "btc_calendar": btc_cal,
        "spx_calendar": spx_cal,
        "btc_best_six_avg_pct": btc_best,
        "btc_worst_six_avg_pct": btc_worst,
        "spx_best_six_avg_pct": spx_best,
        "spx_worst_six_avg_pct": spx_worst,
        "best_six_delta_pct": best_six_delta,
        "corr_full": corr_full,
        "corr_rolling_24m_latest": roll_latest,
        "corr_rolling_24m_avg": roll_avg,
        "month_sign_agreement": sign_agree,
        "btc_term_year_avgs": btc_term,
        "spx_term_year_avgs": spx_term,
        "verdict": v,
        "regime": regime,
        "phase_month_n_total": sum(sum(phase_ns[ph].values()) for ph in PHASE_KEYS),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # --- Python data module ---
    py = f'''"""AUTO-GENERATED by scripts/compute_bitcoin_monthly.py — do not edit by hand.

Generated: {generated}
Verdict: {v} | regime: {regime}
"""

from __future__ import annotations

GENERATED_AT = {generated!r}
MIN_CELL_N = {MIN_CELL_N}
BEAR_PHASE_DAYS = {BEAR_DAYS}
BULL_PHASE_DAYS = {BULL_DAYS}

# Calendar month average returns (BTC-USD), pct
BTC_CALENDAR_MONTHLY_RETURNS: dict[int, float] = {cal_avgs!r}

BTC_CALENDAR_MONTHLY_N: dict[int, int] = {cal_ns!r}

# S&P 500 (^GSPC) same window — comparison only
SPX_CALENDAR_MONTHLY_RETURNS: dict[int, float] = {spx_avgs!r}

# ATH phase × calendar month; None = below MIN_CELL_N
BTC_PHASE_MONTHLY_RETURNS: dict[str, dict[int, float | None]] = {py_repr_matrix(phase_avgs_ser)}

BTC_PHASE_MONTHLY_N: dict[str, dict[int, int]] = {{
'''
    for ph in PHASE_KEYS:
        inner = ", ".join(f"{m}: {phase_ns[ph][m]}" for m in range(1, 13))
        py += f"    {ph!r}: {{{inner}}},\n"
    py += f'''}}

SPX_COMPARISON: dict = {{
    "corr_full": {corr_full!r},
    "corr_rolling_24m_latest": {roll_latest!r},
    "corr_rolling_24m_avg": {roll_avg!r},
    "best_six_btc_avg_pct": {btc_best!r},
    "best_six_spx_avg_pct": {spx_best!r},
    "worst_six_btc_avg_pct": {btc_worst!r},
    "worst_six_spx_avg_pct": {spx_worst!r},
    "best_six_delta_pct": {best_six_delta!r},
    "month_sign_agreement": {sign_agree!r},
    "verdict": {v!r},
    "regime": {regime!r},
    "aligned_months": {len(pairs)!r},
    "btc_term_year_avgs": {btc_term!r},
    "spx_term_year_avgs": {spx_term!r},
}}
'''
    OUT_PY.write_text(py, encoding="utf-8")
    print(f"Wrote {OUT_PY}")

    # --- Markdown report ---
    month_names = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    rows_md = []
    for m in range(1, 13):
        rows_md.append(
            f"| {month_names[m]} | {btc_cal[m]['avg_pct']:+.2f}% (n={btc_cal[m]['n']}) "
            f"| {spx_cal[m]['avg_pct']:+.2f}% (n={spx_cal[m]['n']}) |"
        )
    md = f"""# BTC seasonality vs S&P 500

Generated: `{generated}`

## Verdict

| Field | Value |
|-------|-------|
| verdict | **{v}** |
| regime (rolling 24m) | **{regime}** |
| corr monthly full | {corr_full} |
| corr rolling 24m latest | {roll_latest} |
| corr rolling 24m avg | {roll_avg} |
| month sign agreement | {sign_agree}/12 |
| Best Six BTC avg | {btc_best}% |
| Best Six SPX avg | {spx_best}% |
| Best Six delta (BTC−SPX) | {best_six_delta} pp |
| Worst Six BTC / SPX | {btc_worst}% / {spx_worst}% |
| aligned months | {len(pairs)} |

Interpretation:
- `similar_to_spx` — calendar seasonality closely tracks equity; lean on ATH phase for crypto edge.
- `partially` — some overlap; cite both phase and month bias.
- `idiosyncratic` — BTC calendar path differs; do not copy US Best Six blindly.

Regime:
- `equity_beta` — recent 24m corr ≥ 0.45 (BTC moves with SPX).
- `mixed` — 0.25–0.45.
- `crypto_idiosyncratic` — corr < 0.25.

## Calendar month averages

| Month | BTC-USD | ^GSPC |
|-------|---------|-------|
{chr(10).join(rows_md)}

## Presidential term-year averages (monthly means)

| Term year | BTC | SPX |
|-----------|-----|-----|
"""
    for y in range(1, 5):
        md += f"| Y{y} | {btc_term.get(y, '—')} | {spx_term.get(y, '—')} |\n"

    md += f"""
## Regeneracja

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/compute_bitcoin_monthly.py
```

Debug JSON: `backend/data/btc_seasonality_debug.json`
Data module: `backend/app/cycles/bitcoin_seasonality_data.py`
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print(f"VERDICT={v} REGIME={regime} corr={corr_full} agree={sign_agree}/12")


if __name__ == "__main__":
    main()

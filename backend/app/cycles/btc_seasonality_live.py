"""Live refresh of BTC month-seasonality tables from real Yahoo Finance history.

The tables in ``bitcoin_seasonality_data`` were an offline snapshot. They are now
recomputed at runtime (scheduler, every few hours) from monthly BTC-USD and ^GSPC
closes and updated *in place*, so every importer sees the fresh numbers.
If a refresh fails, the last real values stay and ``seasonality_state()`` keeps
the timestamp of that last successful computation — nothing is invented.
"""

from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timezone
from urllib.parse import quote as url_quote

import httpx

from app.cycles import bitcoin_seasonality_data as data
from app.cycles.btc_seasonality_compute import (
    PHASE_KEYS,
    aligned_pairs,
    attach_phases,
    best_six_avg,
    calendar_stats,
    monthly_returns,
    pearson,
    phase_month_matrix,
    rolling_corr,
    term_year_avgs,
    verdict,
)

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CyclicalTraderSeasonality/2.0)"}
SOURCE_LIVE = "Yahoo Finance BTC-USD + ^GSPC (miesięczne zamknięcia, pełne miesiące)"


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


_STATE: dict = {
    "updated_at": _parse_iso(getattr(data, "GENERATED_AT", "")),
    "source": f"Yahoo Finance — migawka z {getattr(data, 'GENERATED_AT', '?')[:10]}",
    "live": False,
    "last_error": None,
    "last_attempt_at": None,
}


def seasonality_state() -> dict:
    return dict(_STATE)


async def _fetch_monthly(client: httpx.AsyncClient, symbol: str) -> list[tuple[date, float, float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{url_quote(symbol, safe='')}"
    params = {
        "period1": int(datetime(2010, 1, 1, tzinfo=timezone.utc).timestamp()),
        "period2": int(datetime.now(timezone.utc).timestamp()),
        "interval": "1mo",
        "events": "history",
    }
    resp = await client.get(url, params=params, follow_redirects=True)
    resp.raise_for_status()
    result = (resp.json().get("chart") or {}).get("result") or []
    if not result:
        return []
    r0 = result[0]
    ts = r0.get("timestamp") or []
    q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    closes, highs = q.get("close") or [], q.get("high") or []
    rows: dict[tuple[int, int], tuple[date, float, float]] = {}
    for i, t in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue
        h = highs[i] if i < len(highs) and highs[i] is not None else c
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        rows[(d.year, d.month)] = (date(d.year, d.month, 1), float(c), float(h))
    return [rows[k] for k in sorted(rows)]


def complete_months(rows: list[tuple[date, float, float]], today: date) -> list[tuple[date, float, float]]:
    """Drop the in-progress calendar month (its return is not final yet)."""
    return [r for r in rows if (r[0].year, r[0].month) < (today.year, today.month)]


def compute_tables(
    btc_rows: list[tuple[date, float, float]],
    spx_rows: list[tuple[date, float, float]],
) -> dict:
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
        1 for m in range(1, 13) if (btc_cal[m]["avg_pct"] >= 0) == (spx_cal[m]["avg_pct"] >= 0)
    )
    phase_avgs, phase_ns = phase_month_matrix(attach_phases(btc_rows, btc_rets))
    v, regime = verdict(corr_full, sign_agree, best_six_delta, roll_latest)
    return {
        "calendar": {m: btc_cal[m]["avg_pct"] for m in range(1, 13)},
        "calendar_n": {m: btc_cal[m]["n"] for m in range(1, 13)},
        "spx_calendar": {m: spx_cal[m]["avg_pct"] for m in range(1, 13)},
        "phase": {ph: {m: phase_avgs[ph].get(m) for m in range(1, 13)} for ph in PHASE_KEYS},
        "phase_n": {ph: dict(phase_ns[ph]) for ph in PHASE_KEYS},
        "spx_comparison": {
            "corr_full": corr_full,
            "corr_rolling_24m_latest": roll_latest,
            "corr_rolling_24m_avg": roll_avg,
            "best_six_btc_avg_pct": btc_best,
            "best_six_spx_avg_pct": spx_best,
            "worst_six_btc_avg_pct": btc_worst,
            "worst_six_spx_avg_pct": spx_worst,
            "best_six_delta_pct": best_six_delta,
            "month_sign_agreement": sign_agree,
            "verdict": v,
            "regime": regime,
            "aligned_months": len(pairs),
            "btc_term_year_avgs": term_year_avgs(btc_rets),
            "spx_term_year_avgs": term_year_avgs(spx_rets),
        },
    }


def _replace(target: dict, new: dict) -> None:
    target.clear()
    target.update(new)


def apply_tables(tables: dict) -> None:
    _replace(data.BTC_CALENDAR_MONTHLY_RETURNS, tables["calendar"])
    _replace(data.BTC_CALENDAR_MONTHLY_N, tables["calendar_n"])
    _replace(data.SPX_CALENDAR_MONTHLY_RETURNS, tables["spx_calendar"])
    _replace(data.BTC_PHASE_MONTHLY_RETURNS, tables["phase"])
    _replace(data.BTC_PHASE_MONTHLY_N, tables["phase_n"])
    _replace(data.SPX_COMPARISON, tables["spx_comparison"])


async def refresh_btc_seasonality() -> bool:
    """Download real monthly history and recompute the tables. Returns success."""
    now = datetime.now(timezone.utc)
    _STATE["last_attempt_at"] = now
    try:
        async with httpx.AsyncClient(timeout=30, headers=YAHOO_HEADERS) as client:
            btc = await _fetch_monthly(client, "BTC-USD")
            spx = await _fetch_monthly(client, "^GSPC")
        btc, spx = complete_months(btc, now.date()), complete_months(spx, now.date())
        if len(btc) < 24 or len(spx) < 24:
            raise ValueError(f"too little history (btc={len(btc)}, spx={len(spx)})")
        apply_tables(compute_tables(btc, spx))
    except Exception as exc:
        _STATE["last_error"] = str(exc)[:200]
        logger.warning("BTC seasonality refresh failed (keeping last real values): %s", exc)
        return False
    _STATE.update(
        {
            "updated_at": now,
            "source": SOURCE_LIVE,
            "live": True,
            "last_error": None,
            "through_month": f"{btc[-1][0].year}-{btc[-1][0].month:02d}",
        }
    )
    return True

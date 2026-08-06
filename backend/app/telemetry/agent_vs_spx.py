"""Live paper portfolio NAV vs S&P 500 — real mark-to-market, not fake signal averages.

Primary series (shared baseline timestamp):
  - agent_nav / portfolio_nav: 100 * equity / equity_at_baseline
  - spx_nav: 100 * spx / spx_at_baseline
Baseline is persisted so process restarts do not invent a new race.

Also exposes inception return (equity / initial_cash) for total real P&L since account open.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db.sqlite import db_session
from app.models.schemas import SignalAction

logger = logging.getLogger(__name__)

_BASELINE: dict[str, Any] = {}
_BASELINE_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry_baseline.json"


def _load_baseline_file() -> dict[str, Any]:
    if not _BASELINE_PATH.exists():
        return {}
    try:
        return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_baseline_file(data: dict[str, Any]) -> None:
    try:
        _BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.debug("Could not persist telemetry baseline: %s", exc)


async def init_telemetry_table() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                agent_nav REAL NOT NULL,
                spx_nav REAL NOT NULL,
                agent_ret_pct REAL,
                spx_ret_pct REAL,
                n_long INTEGER NOT NULL,
                n_universe INTEGER NOT NULL,
                scan_id TEXT,
                health_ok INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_telemetry_ts ON agent_telemetry(ts)"
        )
        for alter in (
            "ALTER TABLE agent_telemetry ADD COLUMN portfolio_equity_pln REAL",
            "ALTER TABLE agent_telemetry ADD COLUMN signal_nav REAL",
            "ALTER TABLE agent_telemetry ADD COLUMN source TEXT DEFAULT 'portfolio'",
            "ALTER TABLE agent_telemetry ADD COLUMN inception_nav REAL",
        ):
            try:
                await db.execute(alter)
            except Exception:
                pass
        await db.commit()
    disk = _load_baseline_file()
    if disk.get("spx0") and disk.get("equity0"):
        _BASELINE.update(disk)


def _ew_return_nav(
    buy_prices: dict[str, float],
    *,
    prev_prices: dict[str, float] | None,
    prev_nav: float,
) -> tuple[float, dict[str, float]]:
    """Chain equal-weight returns across overlapping symbols (real %)."""
    if not buy_prices:
        return prev_nav, prev_prices or {}
    if not prev_prices:
        return 100.0, dict(buy_prices)
    rets: list[float] = []
    for sym, px in buy_prices.items():
        old = prev_prices.get(sym)
        if old and old > 0 and px > 0:
            rets.append(px / old - 1.0)
    if not rets:
        return prev_nav, dict(buy_prices)
    nav = prev_nav * (1.0 + sum(rets) / len(rets))
    return nav, dict(buy_prices)


async def _paper_equity() -> tuple[float, float] | None:
    """Return (equity_pln, initial_cash_pln) from real paper portfolio."""
    try:
        from app.paper.portfolio_service import build_portfolio

        pf = await build_portfolio()
        equity = float(pf.get("total_equity_pln") or 0)
        initial = float(pf.get("initial_cash_pln") or 0)
        if initial <= 0 or equity <= 0:
            return None
        return equity, initial
    except Exception as exc:
        logger.debug("Paper equity for telemetry unavailable: %s", exc)
        return None


async def record_telemetry_tick(
    assessments: list[Any],
    *,
    spx_price: float | None,
    scan_id: str | None = None,
) -> dict[str, Any] | None:
    """Record real paper portfolio vs SPX (+ honest EW signal book on the side)."""
    if spx_price is None or spx_price <= 0:
        return None

    paper = await _paper_equity()
    if paper is None:
        return None
    equity_pln, initial_pln = paper

    us_buy = [
        a
        for a in assessments
        if getattr(a, "region", None) == "us"
        and getattr(a, "signal", None) == SignalAction.BUY
        and getattr(a, "price", 0)
        and a.price > 0
    ]
    us_all = [a for a in assessments if getattr(a, "region", None) == "us"]
    n_universe = len(us_all)
    n_long = len(us_buy)
    buy_prices = {a.symbol: float(a.price) for a in us_buy}

    if "spx0" not in _BASELINE or not _BASELINE.get("equity0"):
        disk = _load_baseline_file()
        if disk.get("spx0") and disk.get("equity0"):
            _BASELINE.update(disk)
        else:
            _BASELINE["spx0"] = float(spx_price)
            _BASELINE["equity0"] = float(equity_pln)
            _BASELINE["initial"] = float(initial_pln)
            _BASELINE["signal_nav"] = 100.0
            _BASELINE["signal_prices"] = buy_prices
            _BASELINE["started_at"] = datetime.now(timezone.utc).isoformat()
            _save_baseline_file(
                {
                    "spx0": _BASELINE["spx0"],
                    "equity0": _BASELINE["equity0"],
                    "initial": _BASELINE["initial"],
                    "started_at": _BASELINE["started_at"],
                    "signal_nav": 100.0,
                }
            )

    spx_nav = 100.0 * (float(spx_price) / float(_BASELINE["spx0"]))
    agent_nav = 100.0 * (equity_pln / float(_BASELINE["equity0"]))
    inception_nav = 100.0 * (equity_pln / initial_pln)

    signal_nav, new_prices = _ew_return_nav(
        buy_prices,
        prev_prices=_BASELINE.get("signal_prices") or {},
        prev_nav=float(_BASELINE.get("signal_nav") or 100.0),
    )
    if n_long == 0:
        signal_nav = float(_BASELINE.get("signal_nav") or 100.0)
    _BASELINE["signal_nav"] = signal_nav
    _BASELINE["signal_prices"] = new_prices if n_long else _BASELINE.get("signal_prices") or {}

    agent_ret = agent_nav - 100.0
    spx_ret = spx_nav - 100.0
    ts = datetime.now(timezone.utc).isoformat()
    health_ok = 1 if equity_pln > 0 else 0

    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO agent_telemetry
            (ts, agent_nav, spx_nav, agent_ret_pct, spx_ret_pct, n_long, n_universe,
             scan_id, health_ok, portfolio_equity_pln, signal_nav, source, inception_nav)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                round(agent_nav, 4),
                round(spx_nav, 4),
                round(agent_ret, 4),
                round(spx_ret, 4),
                n_long,
                n_universe,
                scan_id,
                health_ok,
                round(equity_pln, 2),
                round(signal_nav, 4),
                "portfolio",
                round(inception_nav, 4),
            ),
        )
        await db.commit()

    return {
        "ts": ts,
        "agent_nav": round(agent_nav, 4),
        "spx_nav": round(spx_nav, 4),
        "portfolio_nav": round(agent_nav, 4),
        "inception_nav": round(inception_nav, 4),
        "signal_nav": round(signal_nav, 4),
        "portfolio_equity_pln": round(equity_pln, 2),
        "agent_ret_pct": round(agent_ret, 4),
        "spx_ret_pct": round(spx_ret, 4),
        "n_long": n_long,
        "n_universe": n_universe,
        "health_ok": bool(health_ok),
        "source": "portfolio",
    }


async def get_telemetry_series(range_key: str = "30d") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if range_key == "7d":
        since = now - timedelta(days=7)
    elif range_key == "90d":
        since = now - timedelta(days=90)
    elif range_key == "all":
        since = None
    else:
        since = now - timedelta(days=30)

    async with db_session() as db:
        cols = (
            "ts, agent_nav, spx_nav, agent_ret_pct, spx_ret_pct, n_long, n_universe, "
            "health_ok, portfolio_equity_pln, signal_nav, source, inception_nav"
        )
        try:
            if since:
                cur = await db.execute(
                    f"SELECT {cols} FROM agent_telemetry WHERE ts >= ? ORDER BY ts ASC",
                    (since.isoformat(),),
                )
            else:
                cur = await db.execute(f"SELECT {cols} FROM agent_telemetry ORDER BY ts ASC")
            rows = await cur.fetchall()
        except Exception:
            if since:
                cur = await db.execute(
                    "SELECT ts, agent_nav, spx_nav, agent_ret_pct, spx_ret_pct, n_long, n_universe, health_ok "
                    "FROM agent_telemetry WHERE ts >= ? ORDER BY ts ASC",
                    (since.isoformat(),),
                )
            else:
                cur = await db.execute(
                    "SELECT ts, agent_nav, spx_nav, agent_ret_pct, spx_ret_pct, n_long, n_universe, health_ok "
                    "FROM agent_telemetry ORDER BY ts ASC"
                )
            rows = [tuple(list(r) + [None, None, None, None]) for r in await cur.fetchall()]

    series = []
    for r in rows:
        series.append(
            {
                "ts": r[0],
                "time": int(datetime.fromisoformat(r[0]).timestamp()),
                "agent_nav": r[1],
                "spx_nav": r[2],
                "agent_ret_pct": r[3],
                "spx_ret_pct": r[4],
                "n_long": r[5],
                "n_universe": r[6],
                "health_ok": bool(r[7]),
                "portfolio_equity_pln": r[8] if len(r) > 8 else None,
                "signal_nav": r[9] if len(r) > 9 else None,
                "source": (r[10] if len(r) > 10 else None) or "portfolio",
                "inception_nav": r[11] if len(r) > 11 else None,
            }
        )

    last = series[-1] if series else None
    peak = 0.0
    max_dd = 0.0
    for p in series:
        peak = max(peak, p["agent_nav"])
        if peak > 0:
            max_dd = max(max_dd, (peak - p["agent_nav"]) / peak * 100)

    vs_spx = None
    if last:
        vs_spx = round(last["agent_nav"] - last["spx_nav"], 2)

    live = None
    try:
        paper = await _paper_equity()
        if paper:
            equity, initial = paper
            live = {
                "portfolio_equity_pln": round(equity, 2),
                "inception_nav": round(100.0 * equity / initial, 4),
                "vs_spx_nav": vs_spx,
            }
    except Exception:
        pass

    return {
        "range": range_key,
        "points": series,
        "last": last,
        "max_drawdown_pct": round(max_dd, 2),
        "vs_spx_nav": vs_spx,
        "count": len(series),
        "metric": "paper_portfolio_vs_spx",
        "baseline_started_at": _BASELINE.get("started_at") or _load_baseline_file().get("started_at"),
        "disclaimer": (
            "Real paper portfolio mark-to-market vs live ^GSPC. "
            "Both rebased to 100 at the persisted baseline tick. "
            "No fabricated or backfilled fake outperformance."
        ),
        "live": live,
    }

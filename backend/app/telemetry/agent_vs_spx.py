"""Live agent NAV vs S&P 500 telemetry (scan-driven)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.sqlite import db_session
from app.models.schemas import SignalAction

logger = logging.getLogger(__name__)

_BASELINE: dict[str, float] = {}  # agent_price_sum / spx_price at first tick for normalize


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
        await db.commit()


async def record_telemetry_tick(
    assessments: list[Any],
    *,
    spx_price: float | None,
    scan_id: str | None = None,
) -> dict[str, Any] | None:
    """Equal-weight NAV of US BUY signals vs SPX, normalized to 100 at first tick."""
    if not assessments or spx_price is None or spx_price <= 0:
        return None

    us_buy = [
        a
        for a in assessments
        if getattr(a, "region", None) == "us"
        and getattr(a, "signal", None) == SignalAction.BUY
        and getattr(a, "price", 0) and a.price > 0
    ]
    us_all = [a for a in assessments if getattr(a, "region", None) == "us"]
    n_universe = len(us_all)
    n_long = len(us_buy)

    # Basket: EW of BUY names; if none, hold cash (NAV flat vs previous via same NAV)
    if us_buy:
        basket = sum(a.price for a in us_buy) / n_long
    else:
        basket = _BASELINE.get("last_basket") or 1.0

    if "agent0" not in _BASELINE:
        _BASELINE["agent0"] = basket
        _BASELINE["spx0"] = spx_price
    _BASELINE["last_basket"] = basket

    agent_nav = 100.0 * (basket / _BASELINE["agent0"]) if _BASELINE["agent0"] else 100.0
    spx_nav = 100.0 * (spx_price / _BASELINE["spx0"]) if _BASELINE["spx0"] else 100.0
    # When no longs, freeze agent NAV at last recorded (cash drag)
    if n_long == 0 and "last_agent_nav" in _BASELINE:
        agent_nav = _BASELINE["last_agent_nav"]
    _BASELINE["last_agent_nav"] = agent_nav

    agent_ret = agent_nav - 100.0
    spx_ret = spx_nav - 100.0
    ts = datetime.now(timezone.utc).isoformat()
    health_ok = 1 if n_universe > 0 else 0

    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO agent_telemetry
            (ts, agent_nav, spx_nav, agent_ret_pct, spx_ret_pct, n_long, n_universe, scan_id, health_ok)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        await db.commit()

    return {
        "ts": ts,
        "agent_nav": round(agent_nav, 4),
        "spx_nav": round(spx_nav, 4),
        "agent_ret_pct": round(agent_ret, 4),
        "spx_ret_pct": round(spx_ret, 4),
        "n_long": n_long,
        "n_universe": n_universe,
        "health_ok": bool(health_ok),
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
        rows = await cur.fetchall()

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

    return {
        "range": range_key,
        "points": series,
        "last": last,
        "max_drawdown_pct": round(max_dd, 2),
        "vs_spx_nav": vs_spx,
        "count": len(series),
    }

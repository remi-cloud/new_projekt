"""Disk ledger agent — append-only trade bible under baza_portfela/ledger/.

Survives hard restarts and Docker/local path switches when the folder is shared.
On startup: export existing DB → ledger (once), then reconcile / rebuild if needed.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.paths import (
    portfolio_ledger_archive_dir,
    portfolio_ledger_dir,
    portfolio_ledger_state_path,
    portfolio_ledger_trades_path,
)
from app.db.sqlite import portfolio_db_session
from app.paper import paper_db
from app.paper.paper_db import INITIAL_CASH_PLN

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_ledger_dirs() -> Path:
    folder = portfolio_ledger_dir()
    folder.mkdir(parents=True, exist_ok=True)
    portfolio_ledger_archive_dir().mkdir(parents=True, exist_ok=True)
    return folder


def _fsync_file(path: Path) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.flush()
        os.fsync(fh.fileno())


def load_ledger_events() -> list[dict[str, Any]]:
    path = portfolio_ledger_trades_path()
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.warning("Ledger skip bad line: %s", exc)
    return events


def ledger_trade_count() -> int:
    return sum(1 for e in load_ledger_events() if e.get("event") == "trade")


def write_state_snapshot(
    *,
    cash_pln: float,
    realized_pnl_pln: float,
    positions: list[dict[str, Any]],
    trade_count: int,
    source: str = "ledger_agent",
) -> None:
    ensure_ledger_dirs()
    path = portfolio_ledger_state_path()
    payload = {
        "updated_at": _now(),
        "source": source,
        "cash_pln": cash_pln,
        "realized_pnl_pln": realized_pnl_pln,
        "trade_count": trade_count,
        "positions": positions,
        "ledger_path": str(portfolio_ledger_trades_path()),
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _positions_for_ledger(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for p in rows:
        out.append(
            {
                "symbol": p["symbol"],
                "name": p.get("name") or p["symbol"],
                "asset_class": p.get("asset_class") or "stock",
                "quantity": float(p["quantity"]),
                "avg_price_native": float(p["avg_price_native"]),
                "currency": p.get("currency") or "USD",
                "session_realized_pnl_pln": float(p.get("session_realized_pnl_pln") or 0),
            }
        )
    return out


async def append_trade(trade: dict[str, Any]) -> None:
    """Append one filled trade + post-state to trades.jsonl (after SQLite commit)."""
    ensure_ledger_dirs()
    account = await paper_db.get_account()
    positions = await paper_db.get_positions()
    events_n = ledger_trade_count() + 1
    event = {
        "event": "trade",
        "ts": trade.get("created_at") or _now(),
        "trade": {
            "symbol": trade["symbol"],
            "name": trade.get("name") or trade["symbol"],
            "asset_class": trade.get("asset_class") or "stock",
            "side": trade["side"],
            "quantity": float(trade["quantity"]),
            "price_native": float(trade["price_native"]),
            "price_pln": float(trade["price_pln"]),
            "total_pln": float(trade["total_pln"]),
            "fee_pln": float(trade.get("fee_pln") or 0),
            "currency": trade.get("currency") or "USD",
            "created_at": trade.get("created_at") or _now(),
            "trade_source": trade.get("trade_source") or "user",
        },
        "cash_after_pln": float(account["cash_pln"]),
        "realized_pnl_pln": float(account.get("realized_pnl_pln") or 0),
        "positions_after": _positions_for_ledger(positions),
    }
    path = portfolio_ledger_trades_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    write_state_snapshot(
        cash_pln=float(account["cash_pln"]),
        realized_pnl_pln=float(account.get("realized_pnl_pln") or 0),
        positions=_positions_for_ledger(positions),
        trade_count=events_n,
        source="append_trade",
    )


async def export_db_to_ledger_if_empty() -> bool:
    """One-shot: copy existing paper_trades into empty ledger (yesterday's bible)."""
    ensure_ledger_dirs()
    path = portfolio_ledger_trades_path()
    if path.exists() and path.stat().st_size > 0:
        return False

    trades = await paper_db.get_trades(limit=100_000)
    if not trades:
        # Still write empty state so folder exists
        account = await paper_db.get_account()
        positions = await paper_db.get_positions()
        write_state_snapshot(
            cash_pln=float(account["cash_pln"]),
            realized_pnl_pln=float(account.get("realized_pnl_pln") or 0),
            positions=_positions_for_ledger(positions),
            trade_count=0,
            source="export_empty",
        )
        return False

    # get_trades returns DESC — reverse to chronological
    trades_asc = list(reversed(trades))
    account = await paper_db.get_account()
    positions = await paper_db.get_positions()
    pos_ledger = _positions_for_ledger(positions)
    cash = float(account["cash_pln"])
    realized = float(account.get("realized_pnl_pln") or 0)

    lines: list[str] = []
    for i, t in enumerate(trades_asc):
        is_last = i == len(trades_asc) - 1
        event = {
            "event": "trade",
            "ts": t.get("created_at") or _now(),
            "trade": {
                "symbol": t["symbol"],
                "name": t.get("name") or t["symbol"],
                "asset_class": t.get("asset_class") or "stock",
                "side": t["side"],
                "quantity": float(t["quantity"]),
                "price_native": float(t["price_native"]),
                "price_pln": float(t["price_pln"]),
                "total_pln": float(t["total_pln"]),
                "fee_pln": float(t.get("fee_pln") or 0),
                "currency": t.get("currency") or "USD",
                "created_at": t.get("created_at") or _now(),
                "trade_source": t.get("trade_source") or "user",
            },
            # Intermediate cash unknown for historic export — only stamp final on last
            "cash_after_pln": cash if is_last else None,
            "realized_pnl_pln": realized if is_last else None,
            "positions_after": pos_ledger if is_last else None,
            "exported_from_db": True,
        }
        lines.append(json.dumps(event, ensure_ascii=False))

    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)
    _fsync_file(path)
    write_state_snapshot(
        cash_pln=cash,
        realized_pnl_pln=realized,
        positions=pos_ledger,
        trade_count=len(trades_asc),
        source="export_db",
    )
    logger.info("Ledger agent: exported %d trades from DB → %s", len(trades_asc), path)
    return True


async def _db_trade_count() -> int:
    async with portfolio_db_session() as db:
        row = await (await db.execute("SELECT COUNT(*) FROM paper_trades")).fetchone()
        return int(row[0]) if row else 0


async def rebuild_portfolio_from_ledger() -> dict[str, Any]:
    """Wipe paper book and restore from ledger events + final state."""
    events = [e for e in load_ledger_events() if e.get("event") == "trade"]
    if not events:
        raise ValueError("Ledger empty — cannot rebuild")

    await paper_db.init_paper_db()
    # Clear without archiving (caller archives on user reset)
    now = _now()
    async with portfolio_db_session() as db:
        await db.execute("DELETE FROM paper_positions")
        await db.execute("DELETE FROM paper_trades")
        await db.execute("DELETE FROM paper_limit_orders")
        await db.execute("DELETE FROM paper_closed_positions")
        await db.execute(
            """UPDATE paper_account SET cash_pln = ?, initial_cash_pln = ?,
               realized_pnl_pln = 0, updated_at = ? WHERE id = 1""",
            (INITIAL_CASH_PLN, INITIAL_CASH_PLN, now),
        )
        await db.commit()

    last_with_state = None
    for event in events:
        trade = event.get("trade") or {}
        if not trade.get("symbol"):
            continue
        await paper_db.insert_trade(trade)
        if event.get("cash_after_pln") is not None and event.get("positions_after") is not None:
            last_with_state = event

    if last_with_state is None:
        # Fallback: use state.json
        state_path = portfolio_ledger_state_path()
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            last_with_state = {
                "cash_after_pln": state.get("cash_pln", INITIAL_CASH_PLN),
                "realized_pnl_pln": state.get("realized_pnl_pln", 0),
                "positions_after": state.get("positions") or [],
            }
        else:
            raise ValueError("Ledger has trades but no cash/positions state to restore")

    cash = float(last_with_state["cash_after_pln"])
    realized = float(last_with_state.get("realized_pnl_pln") or 0)
    await paper_db.update_account_cash(cash, realized_pnl_delta=0)
    # Set realized absolutely
    async with portfolio_db_session() as db:
        await db.execute(
            "UPDATE paper_account SET realized_pnl_pln = ?, updated_at = ? WHERE id = 1",
            (realized, _now()),
        )
        await db.commit()

    for p in last_with_state.get("positions_after") or []:
        qty = float(p["quantity"])
        if abs(qty) < 1e-12:
            continue
        await paper_db.upsert_position(
            p["symbol"],
            p.get("name") or p["symbol"],
            p.get("asset_class") or "stock",
            qty,
            float(p["avg_price_native"]),
            p.get("currency") or "USD",
            session_realized_pnl_pln=float(p.get("session_realized_pnl_pln") or 0),
        )

    write_state_snapshot(
        cash_pln=cash,
        realized_pnl_pln=realized,
        positions=list(last_with_state.get("positions_after") or []),
        trade_count=len(events),
        source="rebuild",
    )
    logger.info(
        "Ledger agent: rebuilt portfolio from %d ledger trades (cash=%.2f)",
        len(events),
        cash,
    )
    return {
        "rebuilt": True,
        "trades": len(events),
        "cash_pln": cash,
        "positions": len(last_with_state.get("positions_after") or []),
    }


def archive_ledger() -> str | None:
    """Move current trades.jsonl to archive/ and clear for a fresh book."""
    ensure_ledger_dirs()
    path = portfolio_ledger_trades_path()
    if not path.exists() or path.stat().st_size == 0:
        write_state_snapshot(
            cash_pln=INITIAL_CASH_PLN,
            realized_pnl_pln=0.0,
            positions=[],
            trade_count=0,
            source="reset_empty",
        )
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = portfolio_ledger_archive_dir() / f"trades_{stamp}.jsonl"
    path.replace(dest)
    # Fresh empty ledger file
    path.write_text("", encoding="utf-8")
    state = portfolio_ledger_state_path()
    if state.exists():
        state_arch = portfolio_ledger_archive_dir() / f"state_{stamp}.json"
        try:
            state.replace(state_arch)
        except OSError:
            pass
    write_state_snapshot(
        cash_pln=INITIAL_CASH_PLN,
        realized_pnl_pln=0.0,
        positions=[],
        trade_count=0,
        source="reset",
    )
    logger.info("Ledger agent: archived ledger → %s", dest)
    return str(dest)


async def reconcile_on_startup() -> dict[str, Any]:
    """Export if needed; rebuild DB from ledger when empty or behind ledger."""
    ensure_ledger_dirs()
    exported = await export_db_to_ledger_if_empty()

    led_n = ledger_trade_count()
    try:
        db_n = await _db_trade_count()
    except Exception as exc:
        logger.warning("Ledger agent: DB unreadable (%s) — rebuild from ledger", exc)
        db_n = -1

    status = {
        "exported": exported,
        "ledger_trades": led_n,
        "db_trades": db_n,
        "rebuilt": False,
        "ok": True,
        "drift": False,
        "ledger_dir": str(portfolio_ledger_dir()),
    }

    if led_n == 0:
        return status

    need_rebuild = db_n < 0 or db_n == 0 or (led_n > db_n)
    if db_n >= 0 and led_n != db_n and not need_rebuild:
        # DB ahead of ledger (append missed) — backfill export of missing is hard;
        # mark drift and re-export full if ledger empty was already handled.
        status["drift"] = True
        status["ok"] = False
        logger.warning(
            "Ledger agent: drift db_trades=%s ledger_trades=%s",
            db_n,
            led_n,
        )

    if need_rebuild:
        try:
            result = await rebuild_portfolio_from_ledger()
            status["rebuilt"] = True
            status["rebuild"] = result
            status["db_trades"] = result["trades"]
            status["ok"] = True
            status["drift"] = False
        except Exception as exc:
            status["ok"] = False
            status["error"] = str(exc)
            logger.exception("Ledger agent: rebuild failed: %s", exc)

    return status


async def ledger_status() -> dict[str, Any]:
    ensure_ledger_dirs()
    events = load_ledger_events()
    trades = [e for e in events if e.get("event") == "trade"]
    last_ts = trades[-1].get("ts") if trades else None
    try:
        db_n = await _db_trade_count()
    except Exception:
        db_n = None
    state = None
    sp = portfolio_ledger_state_path()
    if sp.exists():
        try:
            state = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = None
    led_n = len(trades)
    drift = db_n is not None and led_n != db_n
    return {
        "ledger_dir": str(portfolio_ledger_dir()),
        "trades_path": str(portfolio_ledger_trades_path()),
        "state_path": str(sp),
        "ledger_trades": led_n,
        "db_trades": db_n,
        "last_ts": last_ts,
        "ok": not drift and db_n is not None,
        "drift": drift,
        "state": state,
    }

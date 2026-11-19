"""Decisions, equity, ticks, health, lessons. No 200-row trim.

Retention: decisions 90 days, ticks 24 hours. Lessons are never deleted.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.sqlite import db_session
from app.solana_desk.real_gate import redact

DEBUG_KINDS = frozenset({"QUOTE", "SEND", "CONFIRM", "RETRY"})

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS solana_desk_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_no INTEGER NOT NULL,
        ts TEXT NOT NULL,
        kind TEXT NOT NULL,
        agent TEXT NOT NULL,
        mint TEXT DEFAULT '',
        symbol TEXT DEFAULT '',
        reason TEXT NOT NULL CHECK(reason <> ''),
        size_pct REAL,
        size_sol REAL,
        size_usd REAL,
        price REAL,
        slip REAL,
        pnl_sol REAL,
        pnl_usd REAL,
        fill_source TEXT,
        parent_id INTEGER,
        detail_json TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_equity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        equity_sol REAL NOT NULL,
        equity_usd REAL,
        cash_sol REAL,
        open_value_sol REAL,
        reason TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_ticks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mint TEXT NOT NULL,
        ts TEXT NOT NULL,
        price REAL NOT NULL,
        liq REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_agent_health (
        agent TEXT PRIMARY KEY,
        last_run_at TEXT,
        last_ok_at TEXT,
        last_latency_ms INTEGER,
        last_error TEXT,
        runs INTEGER NOT NULL DEFAULT 0,
        errors INTEGER NOT NULL DEFAULT 0,
        checks_json TEXT,
        last_quote_ok_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_selftest (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        payload TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent TEXT NOT NULL,
        trade_id INTEGER,
        decision_id INTEGER,
        trigger TEXT NOT NULL,
        evidence_json TEXT,
        diagnosis TEXT,
        lesson_text TEXT NOT NULL,
        rule_json TEXT NOT NULL,
        rule_key TEXT NOT NULL,
        source TEXT NOT NULL,
        model TEXT,
        confidence REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_applied_at TEXT,
        times_applied INTEGER NOT NULL DEFAULT 0,
        times_blocked INTEGER NOT NULL DEFAULT 0,
        outcome_trades INTEGER NOT NULL DEFAULT 0,
        outcome_pnl_sol REAL NOT NULL DEFAULT 0,
        baseline_pnl_sol REAL NOT NULL DEFAULT 0,
        outcome_score REAL,
        retired_at TEXT,
        retired_reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solana_desk_lesson_hits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL,
        decision_id INTEGER,
        ts TEXT NOT NULL,
        effect TEXT NOT NULL,
        counterfactual_json TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_solana_decisions_line ON solana_desk_decisions(line_no)",
    "CREATE INDEX IF NOT EXISTS idx_solana_ticks_mint ON solana_desk_ticks(mint, ts)",
    "CREATE INDEX IF NOT EXISTS idx_solana_lessons_agent ON solana_desk_lessons(agent, status)",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(cols: list[str], values: tuple) -> dict[str, Any]:
    return dict(zip(cols, values))


async def ensure_schema() -> None:
    async with db_session() as db:
        for statement in _SCHEMA:
            await db.execute(statement)
        for statement in (
            "ALTER TABLE solana_desk_trades ADD COLUMN fill_source TEXT",
            "ALTER TABLE solana_desk_trades ADD COLUMN pnl_usd REAL",
            "ALTER TABLE solana_desk_positions ADD COLUMN size_pct REAL",
            "ALTER TABLE solana_desk_positions ADD COLUMN check_decision_id INTEGER",
            "ALTER TABLE solana_desk_positions ADD COLUMN size_decision_id INTEGER",
        ):
            try:
                await db.execute(statement)
            except Exception:
                pass
        await db.commit()
    await migrate_events_once()


async def migrate_events_once() -> None:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = 'events_migrated'")
        if await cur.fetchone():
            return
        cur = await db.execute(
            "SELECT id, ts, agent, mint, symbol, message FROM solana_desk_events ORDER BY id ASC"
        )
        rows = await cur.fetchall()
        for event_id, ts, agent, mint, symbol, message in rows:
            reason = redact(str(message or "")).strip() or "migrated event"
            kind = _event_kind(agent, reason)
            line = await _next_line(db)
            await db.execute(
                """
                INSERT INTO solana_desk_decisions
                    (line_no, ts, kind, agent, mint, symbol, reason, parent_id, detail_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    line,
                    ts,
                    kind,
                    _agent_name(agent),
                    mint or "",
                    symbol or "",
                    reason,
                    json.dumps({"migrated_event_id": event_id}),
                ),
            )
        await db.execute(
            """
            INSERT INTO solana_desk_state (key, value) VALUES ('events_migrated', '1')
            ON CONFLICT(key) DO UPDATE SET value = '1'
            """
        )
        await db.commit()


def _agent_name(agent: str) -> str:
    return {
        "scout": "scanner",
        "checker": "rug_check",
        "sniper": "executor",
        "exit": "executor",
    }.get(agent, agent or "logger")


def _event_kind(agent: str, message: str) -> str:
    text = message.lower()
    if agent == "checker" and "odrzuc" in text:
        return "FILTER"
    if agent == "checker":
        return "PASS"
    if agent == "sniper" and "wejście" in text:
        return "ENTER"
    if agent == "sniper":
        return "SKIP"
    if agent == "exit":
        return "EXIT"
    if agent == "scout":
        return "SCAN"
    return "SKIP"


async def _next_line(db) -> int:
    cur = await db.execute("SELECT COALESCE(MAX(line_no), 0) + 1 FROM solana_desk_decisions")
    row = await cur.fetchone()
    return int(row[0])


async def insert_decision(
    *,
    kind: str,
    agent: str,
    reason: str,
    mint: str = "",
    symbol: str = "",
    size_pct: float | None = None,
    size_sol: float | None = None,
    size_usd: float | None = None,
    price: float | None = None,
    slip: float | None = None,
    pnl_sol: float | None = None,
    pnl_usd: float | None = None,
    fill_source: str | None = None,
    parent_id: int | None = None,
    detail: dict | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    """Single writer. An empty reason is a hard error, not a blank line."""
    text = redact(str(reason or "")).strip()
    if not text:
        raise ValueError("reason required")
    payload = redact(json.dumps(detail or {}, ensure_ascii=False, default=str))
    async with db_session() as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute("PRAGMA foreign_keys=ON")
        if parent_id is not None:
            cur = await db.execute("SELECT id FROM solana_desk_decisions WHERE id = ?", (parent_id,))
            if await cur.fetchone() is None:
                await db.rollback()
                raise ValueError("parent decision missing")
        line = await _next_line(db)
        cur = await db.execute(
            """
            INSERT INTO solana_desk_decisions (
                line_no, ts, kind, agent, mint, symbol, reason, size_pct, size_sol, size_usd,
                price, slip, pnl_sol, pnl_usd, fill_source, parent_id, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                line,
                ts or _now(),
                kind,
                agent,
                mint or "",
                symbol or "",
                text,
                size_pct,
                size_sol,
                size_usd,
                price,
                slip,
                pnl_sol,
                pnl_usd,
                fill_source,
                parent_id,
                payload,
            ),
        )
        decision_id = int(cur.lastrowid)
        await db.commit()
    return await get_decision(decision_id)


async def get_decision(decision_id: int) -> dict[str, Any] | None:
    async with db_session() as db:
        cur = await db.execute("SELECT * FROM solana_desk_decisions WHERE id = ?", (decision_id,))
        row = await cur.fetchone()
        if not row:
            return None
        cols = [item[0] for item in cur.description]
    return _row(cols, row)


async def list_decisions(
    *,
    before_id: int | None = None,
    limit: int = 50,
    include_debug: bool = False,
) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    clauses = ["1 = 1"]
    params: list[Any] = []
    if before_id:
        clauses.append("id < ?")
        params.append(int(before_id))
    if not include_debug:
        clauses.append("kind NOT IN ('QUOTE', 'SEND', 'CONFIRM', 'RETRY')")
    params.append(cap)
    async with db_session() as db:
        cur = await db.execute(
            f"SELECT * FROM solana_desk_decisions WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT ?",
            params,
        )
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    return [_row(cols, row) for row in rows]


async def count_decisions(*, include_debug: bool = False) -> int:
    sql = "SELECT COUNT(*) FROM solana_desk_decisions"
    if not include_debug:
        sql += " WHERE kind NOT IN ('QUOTE', 'SEND', 'CONFIRM', 'RETRY')"
    async with db_session() as db:
        cur = await db.execute(sql)
        row = await cur.fetchone()
    return int(row[0] if row else 0)


async def latest_decision_id() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COALESCE(MAX(id), 0) FROM solana_desk_decisions")
        row = await cur.fetchone()
    return int(row[0] if row else 0)


async def decisions_after(last_id: int, limit: int = 20) -> list[dict[str, Any]]:
    async with db_session() as db:
        cur = await db.execute(
            "SELECT * FROM solana_desk_decisions WHERE id > ? ORDER BY id ASC LIMIT ?",
            (int(last_id), max(1, limit)),
        )
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    return [_row(cols, row) for row in rows]


async def prune_decisions(days: int = 90) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db_session() as db:
        cur = await db.execute("DELETE FROM solana_desk_decisions WHERE ts < ?", (cutoff,))
        await db.commit()
        return int(cur.rowcount or 0)


async def insert_equity(
    *,
    equity_sol: float,
    equity_usd: float | None,
    cash_sol: float,
    open_value_sol: float,
    reason: str,
) -> None:
    text = str(reason or "").strip()
    if not text:
        raise ValueError("reason required")
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_equity (ts, equity_sol, equity_usd, cash_sol, open_value_sol, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_now(), equity_sol, equity_usd, cash_sol, open_value_sol, text),
        )
        await db.commit()


async def latest_equity() -> dict[str, Any] | None:
    async with db_session() as db:
        cur = await db.execute("SELECT * FROM solana_desk_equity ORDER BY id DESC LIMIT 1")
        row = await cur.fetchone()
        if not row:
            return None
        cols = [item[0] for item in cur.description]
    return _row(cols, row)


async def equity_count() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM solana_desk_equity")
        row = await cur.fetchone()
    return int(row[0] if row else 0)


async def insert_tick(mint: str, price: float, liq: float | None = None, ts: str | None = None) -> None:
    async with db_session() as db:
        await db.execute(
            "INSERT INTO solana_desk_ticks (mint, ts, price, liq) VALUES (?, ?, ?, ?)",
            (mint, ts or _now(), price, liq),
        )
        await db.commit()


async def ticks_for(mint: str, *, since_iso: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    params: list[Any] = [mint]
    clause = ""
    if since_iso:
        clause = " AND ts >= ?"
        params.append(since_iso)
    params.append(max(1, min(limit, 500)))
    async with db_session() as db:
        cur = await db.execute(
            f"SELECT ts, price, liq FROM solana_desk_ticks WHERE mint = ?{clause} ORDER BY id ASC LIMIT ?",
            params,
        )
        rows = await cur.fetchall()
    return [{"ts": row[0], "price": row[1], "liq": row[2]} for row in rows]


async def prune_ticks(hours: int = 24) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db_session() as db:
        cur = await db.execute("DELETE FROM solana_desk_ticks WHERE ts < ?", (cutoff,))
        await db.commit()
        return int(cur.rowcount or 0)


async def record_health(
    agent: str,
    *,
    ok: bool,
    latency_ms: int,
    error: str = "",
    checks: list | None = None,
    quote_ok: bool = False,
) -> None:
    now = _now()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_agent_health (
                agent, last_run_at, last_ok_at, last_latency_ms, last_error, runs, errors, checks_json, last_quote_ok_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(agent) DO UPDATE SET
                last_run_at = excluded.last_run_at,
                last_ok_at = CASE WHEN ? THEN excluded.last_ok_at ELSE solana_desk_agent_health.last_ok_at END,
                last_latency_ms = excluded.last_latency_ms,
                last_error = excluded.last_error,
                runs = solana_desk_agent_health.runs + 1,
                errors = solana_desk_agent_health.errors + excluded.errors,
                checks_json = excluded.checks_json,
                last_quote_ok_at = CASE WHEN ? THEN excluded.last_quote_ok_at ELSE solana_desk_agent_health.last_quote_ok_at END
            """,
            (
                agent,
                now,
                now if ok else None,
                int(latency_ms),
                redact(error)[:240],
                0 if ok else 1,
                json.dumps(checks or []),
                now if quote_ok else None,
                1 if ok else 0,
                1 if quote_ok else 0,
            ),
        )
        await db.commit()


async def health_rows() -> dict[str, dict[str, Any]]:
    async with db_session() as db:
        cur = await db.execute("SELECT * FROM solana_desk_agent_health")
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = _row(cols, row)
        raw = item.get("checks_json") or "[]"
        try:
            item["checks"] = json.loads(raw)
        except json.JSONDecodeError:
            item["checks"] = []
        out[str(item["agent"])] = item
    return out


async def save_selftest(payload: dict) -> dict:
    body = redact(json.dumps(payload, ensure_ascii=False, default=str))
    async with db_session() as db:
        await db.execute(
            "INSERT INTO solana_desk_selftest (ts, payload) VALUES (?, ?)",
            (_now(), body),
        )
        await db.commit()
    return json.loads(body)


async def last_selftest() -> dict | None:
    async with db_session() as db:
        cur = await db.execute("SELECT ts, payload FROM solana_desk_selftest ORDER BY id DESC LIMIT 1")
        row = await cur.fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row[1])
    except json.JSONDecodeError:
        payload = {}
    payload["ts"] = row[0]
    return payload


async def read_state(key: str) -> str | None:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = ?", (key,))
        row = await cur.fetchone()
    return None if not row else str(row[0])


async def write_state(key: str, value: str) -> None:
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()

"""SQLite book for Solana Desk. Survives a process restart."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

from app.db.sqlite import db_session
from app.solana_desk.models import fresh_book
from app.solana_desk.real_gate import solscan_tx_url

_TABLES = (
    "solana_desk_positions",
    "solana_desk_trades",
    "solana_desk_events",
    "solana_desk_reports",
)


async def init_solana_desk_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS solana_desk_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS solana_desk_positions (
                mint TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                venue TEXT NOT NULL,
                status TEXT NOT NULL,
                signal_price REAL,
                entry_price REAL,
                last_price REAL,
                peak_price REAL,
                tokens REAL DEFAULT 0,
                size_sol REAL DEFAULT 0,
                entry_fee_sol REAL DEFAULT 0,
                entry_slippage REAL DEFAULT 0,
                entry_reason TEXT DEFAULT '',
                signal_at TEXT,
                opened_at TEXT,
                liquidity_usd REAL DEFAULT 0,
                reserved_sol REAL DEFAULT 0,
                trade_id INTEGER,
                token_atoms TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS solana_desk_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                mint TEXT NOT NULL,
                symbol TEXT NOT NULL,
                venue TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                tokens REAL DEFAULT 0,
                size_sol REAL DEFAULT 0,
                entry_fee_sol REAL DEFAULT 0,
                exit_fee_sol REAL DEFAULT 0,
                entry_slippage REAL DEFAULT 0,
                exit_slippage REAL DEFAULT 0,
                pnl_sol REAL,
                entry_reason TEXT DEFAULT '',
                exit_reason TEXT DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'paper',
                signature TEXT,
                solscan_url TEXT,
                exit_signature TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS solana_desk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                agent TEXT NOT NULL,
                mint TEXT DEFAULT '',
                symbol TEXT DEFAULT '',
                message TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS solana_desk_reports (
                day TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        for statement in (
            "ALTER TABLE solana_desk_positions ADD COLUMN token_atoms TEXT",
            "ALTER TABLE solana_desk_trades ADD COLUMN exit_signature TEXT",
        ):
            try:
                await db.execute(statement)
            except Exception:
                pass
        await db.commit()


def _merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


async def load_book() -> dict:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = 'book'")
        row = await cur.fetchone()
    if not row:
        return fresh_book()
    try:
        stored = json.loads(row[0])
    except json.JSONDecodeError:
        return fresh_book()
    if not isinstance(stored, dict):
        return fresh_book()
    return _merge(fresh_book(), stored)


async def save_book(book: dict) -> None:
    payload = json.dumps(book, ensure_ascii=False)
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_state (key, value) VALUES ('book', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (payload,),
        )
        await db.commit()


async def claim_worker(owner: str, ttl_seconds: float) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    async with db_session() as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = 'lock'")
        row = await cur.fetchone()
        if row:
            try:
                current = json.loads(row[0])
            except json.JSONDecodeError:
                current = {}
            expires = float(current.get("expires") or 0)
            holder = str(current.get("owner") or "")
            if holder and holder != owner and expires > now:
                await db.commit()
                return False
        payload = json.dumps({"owner": owner, "expires": now + ttl_seconds})
        await db.execute(
            """
            INSERT INTO solana_desk_state (key, value) VALUES ('lock', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (payload,),
        )
        await db.commit()
        return True


async def worker_online(grace_seconds: float = 0) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = 'lock'")
        row = await cur.fetchone()
    if not row:
        return False
    try:
        current = json.loads(row[0])
    except json.JSONDecodeError:
        return False
    return float(current.get("expires") or 0) + grace_seconds > now


async def list_positions() -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            "SELECT * FROM solana_desk_positions ORDER BY signal_at ASC"
        )
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    return [dict(zip(cols, row)) for row in rows]


async def upsert_position(row: dict) -> None:
    columns = [
        "mint", "symbol", "venue", "status", "signal_price", "entry_price", "last_price",
        "peak_price", "tokens", "size_sol", "entry_fee_sol", "entry_slippage", "entry_reason",
        "signal_at", "opened_at", "liquidity_usd", "reserved_sol", "trade_id", "token_atoms",
    ]
    values = [row.get(name) for name in columns]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{name} = excluded.{name}" for name in columns if name != "mint")
    async with db_session() as db:
        await db.execute(
            f"""
            INSERT INTO solana_desk_positions ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(mint) DO UPDATE SET {updates}
            """,
            values,
        )
        await db.commit()


async def delete_position(mint: str) -> None:
    async with db_session() as db:
        await db.execute("DELETE FROM solana_desk_positions WHERE mint = ?", (mint,))
        await db.commit()


async def insert_trade(row: dict) -> int:
    columns = [
        "opened_at", "closed_at", "mint", "symbol", "venue", "status", "entry_price",
        "exit_price", "tokens", "size_sol", "entry_fee_sol", "exit_fee_sol", "entry_slippage",
        "exit_slippage", "pnl_sol", "entry_reason", "exit_reason", "mode", "signature",
        "solscan_url", "exit_signature",
    ]
    row = dict(row)
    row["solscan_url"] = solscan_tx_url(row.get("signature"))
    row.setdefault("mode", "paper")
    values = [row.get(name) for name in columns]
    async with db_session() as db:
        cur = await db.execute(
            f"INSERT INTO solana_desk_trades ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            values,
        )
        await db.commit()
        return int(cur.lastrowid)


async def update_trade(trade_id: int, fields: dict) -> None:
    if "signature" in fields:
        fields = dict(fields)
        fields["solscan_url"] = solscan_tx_url(fields.get("signature"))
    keys = list(fields)
    if not keys:
        return
    assignments = ", ".join(f"{key} = ?" for key in keys)
    async with db_session() as db:
        await db.execute(
            f"UPDATE solana_desk_trades SET {assignments} WHERE id = ?",
            [fields[key] for key in keys] + [trade_id],
        )
        await db.commit()


async def list_trades(limit: int = 100) -> list[dict]:
    cap = max(1, min(int(limit), 500))
    async with db_session() as db:
        cur = await db.execute(
            "SELECT * FROM solana_desk_trades ORDER BY id DESC LIMIT ?",
            (cap,),
        )
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    return [dict(zip(cols, row)) for row in rows]


async def count_trades() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM solana_desk_trades")
        row = await cur.fetchone()
    return int(row[0] if row else 0)


async def add_event(agent: str, message: str, mint: str = "", symbol: str = "") -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_events (ts, agent, mint, symbol, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, agent, mint, symbol, message[:400]),
        )
        await db.execute(
            """
            DELETE FROM solana_desk_events
            WHERE id NOT IN (SELECT id FROM solana_desk_events ORDER BY id DESC LIMIT 200)
            """
        )
        await db.commit()


async def list_events(limit: int = 40) -> list[dict]:
    cap = max(1, min(int(limit), 200))
    async with db_session() as db:
        cur = await db.execute(
            "SELECT id, ts, agent, mint, symbol, message FROM solana_desk_events ORDER BY id DESC LIMIT ?",
            (cap,),
        )
        rows = await cur.fetchall()
    return [
        {"id": row[0], "ts": row[1], "agent": row[2], "mint": row[3], "symbol": row[4], "message": row[5]}
        for row in rows
    ]


async def save_report(day: str, payload: dict) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_reports (day, payload, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (day, json.dumps(payload, ensure_ascii=False), now),
        )
        await db.commit()


async def latest_report() -> dict | None:
    async with db_session() as db:
        cur = await db.execute(
            "SELECT day, payload, updated_at FROM solana_desk_reports ORDER BY day DESC LIMIT 1"
        )
        row = await cur.fetchone()
    if not row:
        return None
    try:
        body = json.loads(row[1])
    except json.JSONDecodeError:
        body = {}
    body["day"] = row[0]
    body["updated_at"] = row[2]
    return body


def trades_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "czas_utc",
            "mint",
            "symbol",
            "status",
            "cena_wejscia",
            "cena_wyjscia",
            "oplaty_sol",
            "poslizg_wejscie",
            "poslizg_wyjscie",
            "pnl_sol",
            "powod_wejscia",
            "powod_wyjscia",
            "tryb",
            "solscan",
            "solscan_wyjscie",
        ]
    )
    for row in rows:
        fees = float(row.get("entry_fee_sol") or 0) + float(row.get("exit_fee_sol") or 0)
        opened = row.get("opened_at") or ""
        closed = row.get("closed_at") or ""
        writer.writerow(
            [
                closed or opened,
                row.get("mint") or "",
                row.get("symbol") or "",
                row.get("status") or "",
                row.get("entry_price") if row.get("entry_price") is not None else "",
                row.get("exit_price") if row.get("exit_price") is not None else "",
                f"{fees:.8f}",
                row.get("entry_slippage") if row.get("entry_slippage") is not None else "",
                row.get("exit_slippage") if row.get("exit_slippage") is not None else "",
                row.get("pnl_sol") if row.get("pnl_sol") is not None else "",
                row.get("entry_reason") or "",
                row.get("exit_reason") or "",
            row.get("mode") or "paper",
            row.get("solscan_url") or "",
            solscan_tx_url(row.get("exit_signature")) or "",
        ]
    )
    return buffer.getvalue()


async def read_armed() -> bool:
    """Arm switch. Missing row means disarmed."""
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM solana_desk_state WHERE key = 'armed'")
        row = await cur.fetchone()
    return bool(row and row[0] == "1")


async def write_armed(value: bool) -> None:
    flag = "1" if value else "0"
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_state (key, value) VALUES ('armed', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (flag,),
        )
        await db.commit()


async def disarm() -> None:
    """Every process start clears the arm switch."""
    await init_solana_desk_db()
    await write_armed(False)


async def wipe_solana_desk() -> None:
    """Test helper. Not exposed over HTTP."""
    await init_solana_desk_db()
    async with db_session() as db:
        for table in _TABLES:
            await db.execute(f"DELETE FROM {table}")
        await db.execute("DELETE FROM solana_desk_state")
        await db.commit()

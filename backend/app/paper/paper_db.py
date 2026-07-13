"""Paper trading persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiosqlite

from app.db.sqlite import db_session

logger = logging.getLogger(__name__)

INITIAL_CASH_PLN = 1_000_000.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_paper_db() -> None:
    async with db_session() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash_pln REAL NOT NULL,
                initial_cash_pln REAL NOT NULL,
                realized_pnl_pln REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_price_native REAL NOT NULL,
                currency TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price_native REAL NOT NULL,
                price_pln REAL NOT NULL,
                total_pln REAL NOT NULL,
                fee_pln REAL NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        now = _now()
        await db.execute(
            """INSERT OR IGNORE INTO paper_account
               (id, cash_pln, initial_cash_pln, realized_pnl_pln, created_at, updated_at)
               VALUES (1, ?, ?, 0, ?, ?)""",
            (INITIAL_CASH_PLN, INITIAL_CASH_PLN, now, now),
        )
        await db.commit()
        logger.info("Paper trading DB ready (positions persist across restarts)")


async def get_account() -> dict:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM paper_account WHERE id = 1")).fetchone()
        if not row:
            await init_paper_db()
            return await get_account()
        return dict(row)


async def get_positions() -> list[dict]:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM paper_positions ORDER BY symbol"
        )).fetchall()
        return [dict(r) for r in rows]


async def get_position(symbol: str) -> dict | None:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM paper_positions WHERE symbol = ?", (symbol,)
        )).fetchone()
        return dict(row) if row else None


async def get_trades(limit: int = 50) -> list[dict]:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT ?", (limit,)
        )).fetchall()
        return [dict(r) for r in rows]


async def update_account_cash(cash_pln: float, realized_pnl_delta: float = 0.0) -> None:
    now = _now()
    async with db_session() as db:
        await db.execute(
            """UPDATE paper_account SET cash_pln = ?,
               realized_pnl_pln = realized_pnl_pln + ?,
               updated_at = ? WHERE id = 1""",
            (cash_pln, realized_pnl_delta, now),
        )
        await db.commit()


async def upsert_position(
    symbol: str,
    name: str,
    asset_class: str,
    quantity: float,
    avg_price_native: float,
    currency: str,
) -> None:
    now = _now()
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        existing = await (await db.execute(
            "SELECT symbol FROM paper_positions WHERE symbol = ?", (symbol,)
        )).fetchone()
        if existing:
            await db.execute(
                """UPDATE paper_positions SET quantity = ?, avg_price_native = ?,
                   updated_at = ? WHERE symbol = ?""",
                (quantity, avg_price_native, now, symbol),
            )
        else:
            await db.execute(
                """INSERT INTO paper_positions
                   (symbol, name, asset_class, quantity, avg_price_native, currency, opened_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol, name, asset_class, quantity, avg_price_native, currency, now, now),
            )
        await db.commit()


async def delete_position(symbol: str) -> None:
    async with db_session() as db:
        await db.execute("DELETE FROM paper_positions WHERE symbol = ?", (symbol,))
        await db.commit()


async def insert_trade(trade: dict) -> None:
    async with db_session() as db:
        await db.execute(
            """INSERT INTO paper_trades
               (symbol, name, asset_class, side, quantity, price_native, price_pln,
                total_pln, fee_pln, currency, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade["symbol"], trade["name"], trade["asset_class"], trade["side"],
                trade["quantity"], trade["price_native"], trade["price_pln"],
                trade["total_pln"], trade["fee_pln"], trade["currency"], trade["created_at"],
            ),
        )
        await db.commit()


async def reset_account() -> dict:
    now = _now()
    async with db_session() as db:
        await db.execute("DELETE FROM paper_positions")
        await db.execute("DELETE FROM paper_trades")
        await db.execute(
            """UPDATE paper_account SET cash_pln = ?, initial_cash_pln = ?,
               realized_pnl_pln = 0, updated_at = ? WHERE id = 1""",
            (INITIAL_CASH_PLN, INITIAL_CASH_PLN, now),
        )
        await db.commit()
    return await get_account()

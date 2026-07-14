"""Paper trading persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiosqlite

from app.db.paths import portfolio_database_path
from app.db.sqlite import portfolio_db_session

logger = logging.getLogger(__name__)

INITIAL_CASH_PLN = 1_000_000.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_paper_db() -> None:
    async with portfolio_db_session() as db:
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_limit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL DEFAULT 'limit',
                limit_price_native REAL NOT NULL,
                amount_pln REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                filled_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_closed_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                quantity REAL NOT NULL,
                is_short INTEGER NOT NULL DEFAULT 0,
                entry_price_native REAL NOT NULL,
                exit_price_native REAL NOT NULL,
                entry_price_pln REAL NOT NULL,
                exit_price_pln REAL NOT NULL,
                cost_basis_pln REAL NOT NULL,
                proceeds_pln REAL NOT NULL,
                realized_pnl_pln REAL NOT NULL,
                realized_pnl_pct REAL NOT NULL,
                currency TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT NOT NULL
            )
        """)
        for alter in (
            "ALTER TABLE paper_limit_orders ADD COLUMN order_type TEXT NOT NULL DEFAULT 'limit'",
            "ALTER TABLE paper_positions ADD COLUMN session_realized_pnl_pln REAL NOT NULL DEFAULT 0",
        ):
            try:
                await db.execute(alter)
            except aiosqlite.OperationalError:
                pass
        now = _now()
        await db.execute(
            """INSERT OR IGNORE INTO paper_account
               (id, cash_pln, initial_cash_pln, realized_pnl_pln, created_at, updated_at)
               VALUES (1, ?, ?, 0, ?, ?)""",
            (INITIAL_CASH_PLN, INITIAL_CASH_PLN, now, now),
        )
        await db.commit()
        logger.info(
            "Paper trading DB ready at %s (persists in baza_portfela/)",
            portfolio_database_path(),
        )


async def get_account() -> dict:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM paper_account WHERE id = 1")).fetchone()
        if not row:
            await init_paper_db()
            return await get_account()
        return dict(row)


async def get_positions() -> list[dict]:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM paper_positions ORDER BY symbol"
        )).fetchall()
        return [dict(r) for r in rows]


async def get_position(symbol: str) -> dict | None:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM paper_positions WHERE symbol = ?", (symbol,)
        )).fetchone()
        return dict(row) if row else None


async def get_trades(limit: int = 50) -> list[dict]:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT ?", (limit,)
        )).fetchall()
        return [dict(r) for r in rows]


async def get_trades_for_symbol(symbol: str, limit: int = 200) -> list[dict]:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """SELECT * FROM paper_trades WHERE symbol = ?
               ORDER BY created_at ASC LIMIT ?""",
            (symbol, limit),
        )).fetchall()
        return [dict(r) for r in rows]


async def update_account_cash(cash_pln: float, realized_pnl_delta: float = 0.0) -> None:
    now = _now()
    async with portfolio_db_session() as db:
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
    session_realized_pnl_pln: float | None = None,
) -> None:
    now = _now()
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        existing = await (await db.execute(
            "SELECT * FROM paper_positions WHERE symbol = ?", (symbol,)
        )).fetchone()
        if existing:
            session = (
                session_realized_pnl_pln
                if session_realized_pnl_pln is not None
                else float(existing["session_realized_pnl_pln"] or 0)
            )
            await db.execute(
                """UPDATE paper_positions SET quantity = ?, avg_price_native = ?,
                   session_realized_pnl_pln = ?, updated_at = ? WHERE symbol = ?""",
                (quantity, avg_price_native, session, now, symbol),
            )
        else:
            await db.execute(
                """INSERT INTO paper_positions
                   (symbol, name, asset_class, quantity, avg_price_native, currency,
                    session_realized_pnl_pln, opened_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (symbol, name, asset_class, quantity, avg_price_native, currency, now, now),
            )
        await db.commit()


async def insert_closed_position(record: dict) -> None:
    async with portfolio_db_session() as db:
        await db.execute(
            """INSERT INTO paper_closed_positions
               (symbol, name, asset_class, quantity, is_short,
                entry_price_native, exit_price_native, entry_price_pln, exit_price_pln,
                cost_basis_pln, proceeds_pln, realized_pnl_pln, realized_pnl_pct,
                currency, opened_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["symbol"],
                record["name"],
                record["asset_class"],
                record["quantity"],
                1 if record["is_short"] else 0,
                record["entry_price_native"],
                record["exit_price_native"],
                record["entry_price_pln"],
                record["exit_price_pln"],
                record["cost_basis_pln"],
                record["proceeds_pln"],
                record["realized_pnl_pln"],
                record["realized_pnl_pct"],
                record["currency"],
                record["opened_at"],
                record["closed_at"],
            ),
        )
        await db.commit()


async def get_closed_positions(limit: int = 50) -> list[dict]:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """SELECT * FROM paper_closed_positions
                   ORDER BY closed_at DESC LIMIT ?""",
                (limit,),
            )
        ).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            row["is_short"] = bool(row["is_short"])
            result.append(row)
        return result


async def delete_position(symbol: str) -> None:
    async with portfolio_db_session() as db:
        await db.execute("DELETE FROM paper_positions WHERE symbol = ?", (symbol,))
        await db.commit()


async def insert_trade(trade: dict) -> None:
    async with portfolio_db_session() as db:
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
    return await get_account()


async def insert_limit_order(order: dict) -> dict:
    now = _now()
    async with portfolio_db_session() as db:
        cur = await db.execute(
            """INSERT INTO paper_limit_orders
               (symbol, name, asset_class, side, order_type, limit_price_native, amount_pln, currency, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (
                order["symbol"],
                order["name"],
                order["asset_class"],
                order["side"],
                order.get("order_type", "limit"),
                order["limit_price_native"],
                order["amount_pln"],
                order["currency"],
                now,
            ),
        )
        await db.commit()
        order_id = cur.lastrowid
    row = await get_limit_order(int(order_id))
    return row or {**order, "id": order_id, "status": "pending", "created_at": now}


async def get_limit_order(order_id: int) -> dict | None:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        row = await (
            await db.execute("SELECT * FROM paper_limit_orders WHERE id = ?", (order_id,))
        ).fetchone()
        return dict(row) if row else None


async def get_pending_limit_orders() -> list[dict]:
    async with portfolio_db_session() as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """SELECT * FROM paper_limit_orders WHERE status = 'pending'
                   ORDER BY created_at ASC"""
            )
        ).fetchall()
        return [dict(r) for r in rows]


async def mark_limit_order_filled(order_id: int) -> None:
    now = _now()
    async with portfolio_db_session() as db:
        await db.execute(
            """UPDATE paper_limit_orders SET status = 'filled', filled_at = ?
               WHERE id = ?""",
            (now, order_id),
        )
        await db.commit()


async def cancel_limit_order(order_id: int) -> None:
    now = _now()
    async with portfolio_db_session() as db:
        await db.execute(
            """UPDATE paper_limit_orders SET status = 'cancelled', filled_at = ?
               WHERE id = ? AND status = 'pending'""",
            (now, order_id),
        )
        await db.commit()


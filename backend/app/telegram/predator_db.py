"""SQLite store for Telegram Predator signals."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

from app.config import settings


async def init_predator_db() -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_predator_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_message_id INTEGER,
                chat_id TEXT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL,
                reason TEXT,
                raw_text TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(chat_id, tg_message_id, symbol, action)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_predator_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def get_offset() -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        row = await (
            await db.execute(
                "SELECT value FROM telegram_predator_state WHERE key = 'update_offset'"
            )
        ).fetchone()
    return int(row[0]) if row else 0


async def set_offset(offset: int) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT INTO telegram_predator_state(key, value) VALUES('update_offset', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(offset),),
        )
        await db.commit()


async def upsert_signal(
    *,
    tg_message_id: int | None,
    chat_id: str,
    symbol: str,
    action: str,
    confidence: float,
    reason: str,
    raw_text: str,
) -> bool:
    """Return True if inserted (new)."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            await db.execute(
                """
                INSERT INTO telegram_predator_signals
                (tg_message_id, chat_id, symbol, action, confidence, reason, raw_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tg_message_id,
                    chat_id,
                    symbol,
                    action,
                    confidence,
                    reason,
                    raw_text[:2000],
                    now,
                ),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def list_signals(limit: int = 40) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT id, tg_message_id, chat_id, symbol, action, confidence, reason,
                       raw_text, created_at
                FROM telegram_predator_signals
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        ).fetchall()
    return [dict(r) for r in rows]

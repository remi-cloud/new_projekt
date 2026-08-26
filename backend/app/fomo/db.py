"""SQLite persistence for FOMO Ghost (top traders + bag events)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.sqlite import db_session


async def init_fomo_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fomo_traders (
                handle TEXT PRIMARY KEY,
                rank INTEGER NOT NULL,
                pnl REAL,
                win_rate REAL,
                trades INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fomo_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                handle TEXT NOT NULL,
                action TEXT NOT NULL,
                mint TEXT NOT NULL,
                symbol TEXT NOT NULL,
                chain TEXT NOT NULL,
                usd_amount REAL,
                ts_unix INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fomo_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_fomo_events_ts ON fomo_events(ts_unix DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_fomo_events_action ON fomo_events(action, ts_unix DESC)"
        )
        await db.commit()


async def get_state(key: str, default: str | None = None) -> str | None:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM fomo_state WHERE key = ?", (key,))
        row = await cur.fetchone()
    return row[0] if row else default


async def set_state(key: str, value: str) -> None:
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO fomo_state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


async def replace_top_traders(traders: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM fomo_traders")
        for t in traders:
            await db.execute(
                """
                INSERT INTO fomo_traders(handle, rank, pnl, win_rate, trades, updated_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["handle"],
                    int(t["rank"]),
                    t.get("pnl"),
                    t.get("win_rate"),
                    int(t.get("trades") or 0),
                    now,
                    json.dumps(t.get("raw") or {}, ensure_ascii=False)[:4000],
                ),
            )
        await db.commit()


async def list_top_traders(limit: int = 30) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT handle, rank, pnl, win_rate, trades, updated_at
            FROM fomo_traders
            ORDER BY rank ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    return [
        {
            "handle": r[0],
            "rank": r[1],
            "pnl": r[2],
            "win_rate": r[3],
            "trades": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]


async def top_handles(limit: int = 30) -> set[str]:
    traders = await list_top_traders(limit)
    return {t["handle"].lower() for t in traders if t.get("handle")}


async def insert_event(ev: dict) -> bool:
    """Return True if newly inserted."""
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        try:
            await db.execute(
                """
                INSERT INTO fomo_events(
                    event_id, handle, action, mint, symbol, chain, usd_amount, ts_unix, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev["event_id"],
                    ev["handle"],
                    ev["action"],
                    ev["mint"],
                    ev["symbol"],
                    ev["chain"],
                    ev.get("usd_amount"),
                    int(ev.get("ts_unix") or 0),
                    now,
                    json.dumps(ev.get("raw") or {}, ensure_ascii=False)[:4000],
                ),
            )
            await db.commit()
            return True
        except Exception:
            return False


async def list_events(limit: int = 50, side: str | None = None) -> list[dict]:
    q = """
        SELECT event_id, handle, action, mint, symbol, chain, usd_amount, ts_unix, created_at
        FROM fomo_events
    """
    params: list = []
    if side in ("buy", "sell"):
        q += " WHERE action = ?"
        params.append(side)
    q += " ORDER BY ts_unix DESC, id DESC LIMIT ?"
    params.append(limit)
    async with db_session() as db:
        cur = await db.execute(q, tuple(params))
        rows = await cur.fetchall()
    return [
        {
            "event_id": r[0],
            "handle": r[1],
            "action": r[2],
            "mint": r[3],
            "symbol": r[4],
            "chain": r[5],
            "usd_amount": r[6],
            "ts_unix": r[7],
            "created_at": r[8],
        }
        for r in rows
    ]


async def events_count() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM fomo_events")
        row = await cur.fetchone()
    return int(row[0]) if row else 0

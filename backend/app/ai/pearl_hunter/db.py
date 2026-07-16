"""SQLite persistence for pearl finds."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.sqlite import db_session


async def init_pearl_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pearl_finds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                region TEXT DEFAULT 'global',
                price REAL DEFAULT 0,
                change_pct_24h REAL,
                score REAL DEFAULT 0,
                confidence REAL DEFAULT 0,
                action TEXT DEFAULT 'watch',
                rationale TEXT DEFAULT '',
                source TEXT DEFAULT '',
                broker_json TEXT DEFAULT '{}',
                found_at TEXT NOT NULL,
                UNIQUE(agent_id, symbol)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pearl_agent_runs (
                agent_id TEXT PRIMARY KEY,
                last_run_at TEXT,
                last_count INTEGER DEFAULT 0,
                last_error TEXT DEFAULT ''
            )
            """
        )
        await db.commit()


async def upsert_find(find: dict) -> None:
    broker_json = json.dumps(find.get("broker_info") or {})
    found_at = find.get("found_at") or datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO pearl_finds (
                agent_id, symbol, name, asset_class, region, price, change_pct_24h,
                score, confidence, action, rationale, source, broker_json, found_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, symbol) DO UPDATE SET
                name=excluded.name,
                asset_class=excluded.asset_class,
                region=excluded.region,
                price=excluded.price,
                change_pct_24h=excluded.change_pct_24h,
                score=excluded.score,
                confidence=excluded.confidence,
                action=excluded.action,
                rationale=excluded.rationale,
                source=excluded.source,
                broker_json=excluded.broker_json,
                found_at=excluded.found_at
            """,
            (
                find["agent_id"],
                find["symbol"],
                find["name"],
                find["asset_class"],
                find.get("region", "global"),
                float(find.get("price") or 0),
                find.get("change_pct_24h"),
                float(find.get("score") or 0),
                float(find.get("confidence") or 0),
                find.get("action", "watch"),
                find.get("rationale", ""),
                find.get("source", ""),
                broker_json,
                found_at,
            ),
        )
        await db.commit()


async def list_finds(limit: int = 40, agent_id: str | None = None) -> list[dict]:
    async with db_session() as db:
        if agent_id:
            cur = await db.execute(
                """
                SELECT * FROM pearl_finds
                WHERE agent_id = ?
                ORDER BY score DESC, found_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            )
        else:
            cur = await db.execute(
                """
                SELECT * FROM pearl_finds
                ORDER BY score DESC, found_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]

    out = []
    for row in rows:
        item = dict(zip(cols, row))
        try:
            item["broker_info"] = json.loads(item.pop("broker_json") or "{}")
        except Exception:
            item["broker_info"] = {}
            item.pop("broker_json", None)
        out.append(item)
    return out


async def count_finds() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM pearl_finds")
        row = await cur.fetchone()
        return int(row[0] if row else 0)


async def record_run(agent_id: str, count: int, error: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO pearl_agent_runs (agent_id, last_run_at, last_count, last_error)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                last_run_at=excluded.last_run_at,
                last_count=excluded.last_count,
                last_error=excluded.last_error
            """,
            (agent_id, now, count, error),
        )
        await db.commit()


async def get_runs() -> list[dict]:
    async with db_session() as db:
        cur = await db.execute("SELECT agent_id, last_run_at, last_count, last_error FROM pearl_agent_runs")
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]

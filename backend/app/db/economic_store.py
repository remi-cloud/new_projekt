"""Persist + query economic calendar events (full local DB)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite

from app.config import settings


async def ensure_economic_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS economic_events (
            event_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            country TEXT NOT NULL,
            impact TEXT NOT NULL,
            impact_rank INTEGER NOT NULL DEFAULT 0,
            event_at TEXT NOT NULL,
            forecast TEXT NOT NULL DEFAULT '',
            previous TEXT NOT NULL DEFAULT '',
            actual TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'faireconomy',
            synced_at TEXT NOT NULL
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_econ_event_at ON economic_events(event_at)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_econ_impact ON economic_events(impact_rank DESC, event_at)"
    )


async def upsert_economic_events(events: list[dict]) -> int:
    if not events:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await ensure_economic_tables(db)
        for e in events:
            await db.execute(
                """
                INSERT INTO economic_events (
                    event_id, title, country, impact, impact_rank, event_at,
                    forecast, previous, actual, source, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    title = excluded.title,
                    country = excluded.country,
                    impact = excluded.impact,
                    impact_rank = excluded.impact_rank,
                    event_at = excluded.event_at,
                    forecast = excluded.forecast,
                    previous = excluded.previous,
                    actual = excluded.actual,
                    source = excluded.source,
                    synced_at = excluded.synced_at
                """,
                (
                    e["event_id"],
                    e["title"],
                    e["country"],
                    e["impact"],
                    int(e.get("impact_rank") or 0),
                    e["event_at"],
                    e.get("forecast") or "",
                    e.get("previous") or "",
                    e.get("actual") or "",
                    e.get("source") or "faireconomy",
                    now,
                ),
            )
        await db.commit()
    return len(events)


async def list_economic_events(
    *,
    hours_back: int = 24,
    hours_ahead: int = 168,
    min_impact_rank: int = 0,
    limit: int = 200,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=hours_back)).isoformat()
    end = (now + timedelta(hours=hours_ahead)).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await ensure_economic_tables(db)
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT event_id, title, country, impact, impact_rank, event_at,
                   forecast, previous, actual, source
            FROM economic_events
            WHERE event_at >= ? AND event_at <= ? AND impact_rank >= ?
            ORDER BY event_at ASC
            LIMIT ?
            """,
            (start, end, min_impact_rank, limit),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def count_economic_events() -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        await ensure_economic_tables(db)
        cursor = await db.execute("SELECT COUNT(*) FROM economic_events")
        row = await cursor.fetchone()
        return int(row[0] if row else 0)

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from app.config import settings
from app.models.schemas import Opportunity

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


async def init_db() -> None:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                cycle_source TEXT NOT NULL,
                phase TEXT NOT NULL,
                price REAL NOT NULL,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL,
                scan_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                opportunities_count INTEGER NOT NULL,
                changes_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS signal_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                previous_action TEXT,
                new_action TEXT NOT NULL,
                previous_confidence REAL,
                new_confidence REAL NOT NULL,
                cycle_source TEXT NOT NULL,
                phase TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Lightweight migrations for existing installs
        cursor = await db.execute("PRAGMA table_info(scan_log)")
        scan_cols = {row[1] for row in await cursor.fetchall()}
        if "changes_count" not in scan_cols:
            await db.execute(
                "ALTER TABLE scan_log ADD COLUMN changes_count INTEGER NOT NULL DEFAULT 0"
            )
        cursor = await db.execute("PRAGMA table_info(opportunities)")
        opp_cols = {row[1] for row in await cursor.fetchall()}
        if "scan_id" not in opp_cols:
            await db.execute("ALTER TABLE opportunities ADD COLUMN scan_id INTEGER")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_created_at ON opportunities(created_at DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_symbol ON opportunities(symbol, created_at DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_signal_changes_created_at ON signal_changes(created_at DESC)"
        )
        await db.commit()


async def _latest_actions(db: aiosqlite.Connection) -> dict[str, dict]:
    """Latest known action/confidence per symbol from the most recent scan."""
    cursor = await db.execute(
        "SELECT id FROM scan_log ORDER BY id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    if not row:
        return {}
    last_scan_id = row[0]
    cursor = await db.execute(
        """SELECT symbol, action, confidence, name, asset_class
           FROM opportunities WHERE scan_id = ?""",
        (last_scan_id,),
    )
    rows = await cursor.fetchall()
    return {
        r[0]: {
            "action": r[1],
            "confidence": r[2],
            "name": r[3],
            "asset_class": r[4],
        }
        for r in rows
    }


async def save_opportunities(opportunities: list[Opportunity]) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        previous = await _latest_actions(db)
        changes: list[tuple] = []

        for opp in opportunities:
            prev = previous.get(opp.symbol)
            if prev is None or prev["action"] != opp.action.value:
                changes.append(
                    (
                        opp.symbol,
                        opp.name,
                        opp.asset_class.value,
                        prev["action"] if prev else None,
                        opp.action.value,
                        prev["confidence"] if prev else None,
                        opp.confidence,
                        opp.cycle_source,
                        opp.phase,
                        opp.price,
                        now,
                    )
                )

        cursor = await db.execute(
            "INSERT INTO scan_log (scanned_at, opportunities_count, changes_count) VALUES (?, ?, ?)",
            (now, len(opportunities), len(changes)),
        )
        scan_id = cursor.lastrowid

        for opp in opportunities:
            await db.execute(
                """INSERT INTO opportunities
                   (symbol, name, asset_class, action, confidence, cycle_source,
                    phase, price, rationale, created_at, scan_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp.symbol,
                    opp.name,
                    opp.asset_class.value,
                    opp.action.value,
                    opp.confidence,
                    opp.cycle_source,
                    opp.phase,
                    opp.price,
                    opp.rationale,
                    opp.created_at.isoformat(),
                    scan_id,
                ),
            )

        for change in changes:
            await db.execute(
                """INSERT INTO signal_changes
                   (scan_id, symbol, name, asset_class, previous_action, new_action,
                    previous_confidence, new_confidence, cycle_source, phase, price, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scan_id, *change),
            )

        cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
        await db.execute("DELETE FROM opportunities WHERE created_at < ?", (cutoff,))
        await db.execute("DELETE FROM signal_changes WHERE created_at < ?", (cutoff,))
        await db.execute("DELETE FROM scan_log WHERE scanned_at < ?", (cutoff,))
        await db.commit()

        return {
            "scan_id": scan_id,
            "opportunities_count": len(opportunities),
            "changes_count": len(changes),
        }


async def get_recent_opportunities(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_scan_history(limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM scan_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_signal_changes(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM signal_changes ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

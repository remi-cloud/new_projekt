import aiosqlite
import logging
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models.schemas import Opportunity

logger = logging.getLogger(__name__)


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
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                opportunities_count INTEGER NOT NULL
            )
        """)
        await db.commit()


async def save_opportunities(opportunities: list[Opportunity]) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        for opp in opportunities:
            await db.execute(
                """INSERT INTO opportunities
                   (symbol, name, asset_class, action, confidence, cycle_source,
                    phase, price, rationale, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp.symbol, opp.name, opp.asset_class.value, opp.action.value,
                    opp.confidence, opp.cycle_source, opp.phase, opp.price,
                    opp.rationale, opp.created_at.isoformat(),
                ),
            )
        await db.execute(
            "INSERT INTO scan_log (scanned_at, opportunities_count) VALUES (?, ?)",
            (now, len(opportunities)),
        )
        await db.commit()


async def get_recent_opportunities(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

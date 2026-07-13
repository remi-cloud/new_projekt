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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alert_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                phone TEXT DEFAULT '',
                sms_enabled INTEGER DEFAULT 0,
                push_enabled INTEGER DEFAULT 1,
                min_confidence REAL DEFAULT 60,
                alert_on_signal_change INTEGER DEFAULT 1,
                alert_on_new_opportunity INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                symbol TEXT,
                message TEXT NOT NULL,
                success INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO alert_settings (id, phone, sms_enabled, push_enabled, min_confidence)
            VALUES (1, '', 0, 1, ?)
        """, (settings.alert_min_confidence,))
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


async def save_push_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh, auth=excluded.auth""",
            (endpoint, p256dh, auth, now),
        )
        await db.commit()


async def remove_push_subscription(endpoint: str) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        await db.commit()


async def get_push_subscriptions() -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_alert_settings() -> dict:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM alert_settings WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return {
                "phone": "",
                "sms_enabled": False,
                "push_enabled": True,
                "min_confidence": settings.alert_min_confidence,
                "alert_on_signal_change": True,
                "alert_on_new_opportunity": True,
            }
        return {
            "phone": row["phone"] or "",
            "sms_enabled": bool(row["sms_enabled"]),
            "push_enabled": bool(row["push_enabled"]),
            "min_confidence": float(row["min_confidence"]),
            "alert_on_signal_change": bool(row["alert_on_signal_change"]),
            "alert_on_new_opportunity": bool(row["alert_on_new_opportunity"]),
        }


async def update_alert_settings(data: dict) -> dict:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """UPDATE alert_settings SET
               phone = ?,
               sms_enabled = ?,
               push_enabled = ?,
               min_confidence = ?,
               alert_on_signal_change = ?,
               alert_on_new_opportunity = ?
               WHERE id = 1""",
            (
                data.get("phone", ""),
                1 if data.get("sms_enabled") else 0,
                1 if data.get("push_enabled", True) else 0,
                float(data.get("min_confidence", settings.alert_min_confidence)),
                1 if data.get("alert_on_signal_change", True) else 0,
                1 if data.get("alert_on_new_opportunity", True) else 0,
            ),
        )
        await db.commit()
    return await get_alert_settings()


async def log_notification(channel: str, symbol: str | None, message: str, success: bool) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO notification_log (channel, symbol, message, success, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (channel, symbol, message, 1 if success else 0, now),
        )
        await db.commit()


async def get_notification_log(limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notification_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

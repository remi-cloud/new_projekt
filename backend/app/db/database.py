import aiosqlite
import logging
import secrets
from datetime import datetime

from app.config import settings
from app.db.paths import ensure_data_dir
from app.db.sqlite import db_session
from app.models.schemas import Opportunity

logger = logging.getLogger(__name__)


async def init_db() -> None:
    ensure_data_dir()
    async with db_session() as db:
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
        await _migrate_alert_settings(db)
        default_phone = settings.alert_phone_number or ""
        ntfy_topic = f"cyclical-{secrets.token_hex(8)}"
        await db.execute("""
            INSERT OR IGNORE INTO alert_settings
            (id, phone, sms_enabled, push_enabled, min_confidence, ntfy_enabled, ntfy_topic)
            VALUES (1, ?, 1, 1, ?, 1, ?)
        """, (default_phone, settings.alert_min_confidence, ntfy_topic))
        await db.execute(
            """UPDATE alert_settings SET
               phone = CASE WHEN phone = '' OR phone IS NULL THEN ? ELSE phone END,
               sms_enabled = 1,
               ntfy_enabled = COALESCE(ntfy_enabled, 1),
               ntfy_topic = CASE WHEN ntfy_topic = '' OR ntfy_topic IS NULL THEN ? ELSE ntfy_topic END
               WHERE id = 1""",
            (default_phone, ntfy_topic),
        )
        await db.commit()


async def _migrate_alert_settings(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(alert_settings)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "ntfy_topic" not in cols:
        await db.execute("ALTER TABLE alert_settings ADD COLUMN ntfy_topic TEXT DEFAULT ''")
    if "ntfy_enabled" not in cols:
        await db.execute("ALTER TABLE alert_settings ADD COLUMN ntfy_enabled INTEGER DEFAULT 1")


async def save_opportunities(opportunities: list[Opportunity]) -> None:
    now = datetime.utcnow().isoformat()
    async with db_session() as db:
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
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_push_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    now = datetime.utcnow().isoformat()
    async with db_session() as db:
        await db.execute(
            """INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh, auth=excluded.auth""",
            (endpoint, p256dh, auth, now),
        )
        await db.commit()


async def remove_push_subscription(endpoint: str) -> None:
    async with db_session() as db:
        await db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        await db.commit()


async def get_push_subscriptions() -> list[dict]:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_alert_settings() -> dict:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM alert_settings WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return {
                "phone": settings.alert_phone_number,
                "sms_enabled": True,
                "push_enabled": True,
                "ntfy_enabled": True,
                "ntfy_topic": "",
                "min_confidence": settings.alert_min_confidence,
                "alert_on_signal_change": True,
                "alert_on_new_opportunity": True,
            }
        keys = row.keys() if hasattr(row, "keys") else []
        return {
            "phone": row["phone"] or settings.alert_phone_number,
            "sms_enabled": bool(row["sms_enabled"]),
            "push_enabled": bool(row["push_enabled"]),
            "ntfy_enabled": bool(row["ntfy_enabled"]) if "ntfy_enabled" in keys else True,
            "ntfy_topic": (row["ntfy_topic"] or "") if "ntfy_topic" in keys else "",
            "min_confidence": float(row["min_confidence"]),
            "alert_on_signal_change": bool(row["alert_on_signal_change"]),
            "alert_on_new_opportunity": bool(row["alert_on_new_opportunity"]),
        }


async def update_alert_settings(data: dict) -> dict:
    async with db_session() as db:
        await db.execute(
            """UPDATE alert_settings SET
               phone = ?,
               sms_enabled = ?,
               push_enabled = ?,
               ntfy_enabled = ?,
               min_confidence = ?,
               alert_on_signal_change = ?,
               alert_on_new_opportunity = ?
               WHERE id = 1""",
            (
                data.get("phone", ""),
                1 if data.get("sms_enabled") else 0,
                1 if data.get("push_enabled", True) else 0,
                1 if data.get("ntfy_enabled", True) else 0,
                float(data.get("min_confidence", settings.alert_min_confidence)),
                1 if data.get("alert_on_signal_change", True) else 0,
                1 if data.get("alert_on_new_opportunity", True) else 0,
            ),
        )
        await db.commit()
    return await get_alert_settings()


async def log_notification(channel: str, symbol: str | None, message: str, success: bool) -> None:
    now = datetime.utcnow().isoformat()
    async with db_session() as db:
        await db.execute(
            """INSERT INTO notification_log (channel, symbol, message, success, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (channel, symbol, message, 1 if success else 0, now),
        )
        await db.commit()


async def get_notification_log(limit: int = 30) -> list[dict]:
    async with db_session() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notification_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

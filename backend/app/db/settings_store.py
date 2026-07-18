"""Persistent watchlist + alert settings in SQLite."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.data.assets import DEFAULT_ASSETS, lookup_asset, normalize_symbol


async def ensure_settings_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'yahoo',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cursor = await db.execute("SELECT COUNT(*) FROM watchlist")
    count = (await cursor.fetchone())[0]
    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        for asset in DEFAULT_ASSETS:
            await db.execute(
                """INSERT INTO watchlist (symbol, name, asset_class, source, enabled, created_at)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (
                    asset["symbol"],
                    asset["name"],
                    asset["asset_class"],
                    asset.get("source", "yahoo"),
                    now,
                ),
            )
    # Seed alert settings from env if missing
    defaults = {
        "alerts_enabled": "true" if settings.alerts_enabled else "false",
        "ntfy_server": settings.ntfy_server,
        "ntfy_topic": settings.ntfy_topic,
        "webhook_url": settings.webhook_url,
        "min_confidence": "50",
        "alert_actions": json.dumps(["buy", "sell"]),
        "alert_on_first_seen": "false",
    }
    for key, value in defaults.items():
        await db.execute(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )


async def get_watchlist(enabled_only: bool = False) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        if enabled_only:
            cursor = await db.execute(
                "SELECT * FROM watchlist WHERE enabled = 1 ORDER BY asset_class, symbol"
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM watchlist ORDER BY asset_class, symbol"
            )
        return [dict(row) for row in await cursor.fetchall()]


async def add_watchlist_item(
    symbol: str, name: str | None = None, asset_class: str | None = None
) -> dict:
    symbol = normalize_symbol(symbol)
    catalog = lookup_asset(symbol)
    resolved_name = name or (catalog["name"] if catalog else symbol)
    resolved_class = asset_class or (catalog["asset_class"] if catalog else "stock")
    source = catalog["source"] if catalog else "yahoo"
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO watchlist (symbol, name, asset_class, source, enabled, created_at)
               VALUES (?, ?, ?, ?, 1, ?)
               ON CONFLICT(symbol) DO UPDATE SET
                 name = excluded.name,
                 asset_class = excluded.asset_class,
                 source = excluded.source,
                 enabled = 1""",
            (symbol, resolved_name, resolved_class, source, now),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM watchlist WHERE symbol = ?", (symbol,))
        row = await cursor.fetchone()
        return dict(row)


async def remove_watchlist_item(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
        await db.commit()
        return cursor.rowcount > 0


async def set_watchlist_enabled(symbol: str, enabled: bool) -> dict | None:
    symbol = normalize_symbol(symbol)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE watchlist SET enabled = ? WHERE symbol = ?",
            (1 if enabled else 0, symbol),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM watchlist WHERE symbol = ?", (symbol,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def reset_watchlist() -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("DELETE FROM watchlist")
        now = datetime.now(timezone.utc).isoformat()
        for asset in DEFAULT_ASSETS:
            await db.execute(
                """INSERT INTO watchlist (symbol, name, asset_class, source, enabled, created_at)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (
                    asset["symbol"],
                    asset["name"],
                    asset["asset_class"],
                    asset.get("source", "yahoo"),
                    now,
                ),
            )
        await db.commit()
    return await get_watchlist()


async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO app_settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        await db.commit()


async def get_alert_settings() -> dict:
    keys = [
        "alerts_enabled",
        "ntfy_server",
        "ntfy_topic",
        "webhook_url",
        "min_confidence",
        "alert_actions",
        "alert_on_first_seen",
    ]
    result: dict = {}
    for key in keys:
        result[key] = await get_setting(key)
    return {
        "enabled": result["alerts_enabled"].lower() == "true",
        "ntfy_server": result["ntfy_server"] or "https://ntfy.sh",
        "ntfy_topic": result["ntfy_topic"],
        "webhook_url": result["webhook_url"],
        "min_confidence": float(result["min_confidence"] or 50),
        "actions": json.loads(result["alert_actions"] or '["buy","sell"]'),
        "alert_on_first_seen": result["alert_on_first_seen"].lower() == "true",
    }


async def save_alert_settings(payload: dict) -> dict:
    mapping = {
        "alerts_enabled": "true" if payload.get("enabled") else "false",
        "ntfy_server": payload.get("ntfy_server") or "https://ntfy.sh",
        "ntfy_topic": payload.get("ntfy_topic") or "",
        "webhook_url": payload.get("webhook_url") or "",
        "min_confidence": str(payload.get("min_confidence", 50)),
        "alert_actions": json.dumps(payload.get("actions") or ["buy", "sell"]),
        "alert_on_first_seen": "true" if payload.get("alert_on_first_seen") else "false",
    }
    for key, value in mapping.items():
        await set_setting(key, value)
    return await get_alert_settings()


async def log_alert(
    channel: str, status: str, message: str, detail: str | None = None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO alert_log (channel, status, message, detail, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (channel, status, message, detail, now),
        )
        await db.execute(
            """DELETE FROM alert_log WHERE id NOT IN (
                 SELECT id FROM alert_log ORDER BY id DESC LIMIT 200
               )"""
        )
        await db.commit()


async def get_alert_log(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM alert_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in await cursor.fetchall()]

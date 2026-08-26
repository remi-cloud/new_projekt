"""SQLite persistence for execution proposals."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.sqlite import db_session


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_execution_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                region TEXT DEFAULT 'global',
                broker_id TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                amount_pln REAL NOT NULL,
                rationale TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                broker_order_id TEXT,
                paper_trade_id INTEGER,
                error_message TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_agent_runs (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_run_at TEXT,
                last_processed INTEGER DEFAULT 0,
                last_created INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_runtime_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER,
                dry_run INTEGER,
                mirror_paper INTEGER,
                require_approval INTEGER,
                min_confidence REAL,
                amount_pln REAL,
                max_daily INTEGER,
                cooldown_hours INTEGER
            )
            """
        )
        await db.commit()


async def insert_proposal(row: dict) -> int:
    created_at = row.get("created_at") or _now()
    async with db_session() as db:
        cursor = await db.execute(
            """
            INSERT INTO execution_proposals (
                symbol, name, asset_class, region, broker_id, source, confidence,
                amount_pln, rationale, status, broker_order_id, paper_trade_id,
                error_message, created_at, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["symbol"],
                row["name"],
                row["asset_class"],
                row.get("region", "global"),
                row["broker_id"],
                row["source"],
                float(row["confidence"]),
                float(row["amount_pln"]),
                row.get("rationale", ""),
                row.get("status", "pending"),
                row.get("broker_order_id"),
                row.get("paper_trade_id"),
                row.get("error_message"),
                created_at,
                row.get("executed_at"),
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def update_proposal(proposal_id: int, **fields) -> None:
    allowed = {
        "status", "broker_order_id", "paper_trade_id", "error_message", "executed_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [proposal_id]
    async with db_session() as db:
        await db.execute(f"UPDATE execution_proposals SET {cols} WHERE id=?", vals)
        await db.commit()


async def get_proposal(proposal_id: int) -> dict | None:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        cursor = await db.execute("SELECT * FROM execution_proposals WHERE id=?", (proposal_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_proposals(limit: int = 50, status: str | None = None) -> list[dict]:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM execution_proposals WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM execution_proposals ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def count_proposals_today() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    async with db_session() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM execution_proposals
            WHERE created_at LIKE ? AND status IN ('executed', 'dry_run', 'pending', 'approved')
            """,
            (f"{today}%",),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def recent_symbol_proposal(symbol: str, hours: int) -> dict | None:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        cursor = await db.execute(
            """
            SELECT * FROM execution_proposals
            WHERE symbol=? AND datetime(created_at) >= datetime('now', ?)
            ORDER BY created_at DESC LIMIT 1
            """,
            (symbol, f"-{hours} hours"),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def pending_broker_proposal(symbol: str, broker_id: str) -> dict | None:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        cursor = await db.execute(
            """
            SELECT * FROM execution_proposals
            WHERE symbol=? AND broker_id=? AND status IN ('pending', 'approved', 'dry_run')
            ORDER BY created_at DESC LIMIT 1
            """,
            (symbol, broker_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def record_agent_run(processed: int, created: int) -> None:
    now = _now()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO execution_agent_runs (id, last_run_at, last_processed, last_created)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_run_at=excluded.last_run_at,
                last_processed=excluded.last_processed,
                last_created=excluded.last_created
            """,
            (now, processed, created),
        )
        await db.commit()


async def get_last_run() -> dict | None:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        cursor = await db.execute("SELECT * FROM execution_agent_runs WHERE id=1")
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_runtime_settings() -> dict | None:
    async with db_session() as db:
        db.row_factory = __import__("aiosqlite").Row
        cursor = await db.execute("SELECT * FROM execution_runtime_settings WHERE id=1")
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_runtime_settings(settings: dict) -> None:
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO execution_runtime_settings (
                id, enabled, dry_run, mirror_paper, require_approval,
                min_confidence, amount_pln, max_daily, cooldown_hours
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enabled=excluded.enabled,
                dry_run=excluded.dry_run,
                mirror_paper=excluded.mirror_paper,
                require_approval=excluded.require_approval,
                min_confidence=excluded.min_confidence,
                amount_pln=excluded.amount_pln,
                max_daily=excluded.max_daily,
                cooldown_hours=excluded.cooldown_hours
            """,
            (
                int(settings.get("enabled", 0)),
                int(settings.get("dry_run", 1)),
                int(settings.get("mirror_paper", 0)),
                int(settings.get("require_approval", 1)),
                float(settings.get("min_confidence", 70)),
                float(settings.get("amount_pln", 10000)),
                int(settings.get("max_daily", 5)),
                int(settings.get("cooldown_hours", 24)),
            ),
        )
        await db.commit()

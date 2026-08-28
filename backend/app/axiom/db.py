"""SQLite persistence for Axiom Pulse + position snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.sqlite import db_session


async def init_axiom_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS axiom_pulse (
                mint TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                chain TEXT NOT NULL,
                pair_address TEXT,
                price_usd REAL,
                liquidity_usd REAL,
                market_cap_usd REAL,
                volume_24h REAL,
                change_1h REAL,
                change_24h REAL,
                image_url TEXT,
                url TEXT,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS axiom_positions (
                position_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                owner_kind TEXT NOT NULL,
                mint TEXT NOT NULL,
                symbol TEXT NOT NULL,
                chain TEXT NOT NULL,
                status TEXT NOT NULL,
                usd_size REAL,
                amount REAL,
                last_ts INTEGER,
                url TEXT,
                image_url TEXT,
                updated_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS axiom_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_axiom_pos_owner ON axiom_positions(owner_kind, owner)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_axiom_pos_status ON axiom_positions(status, updated_at DESC)"
        )
        await db.commit()


async def get_state(key: str, default: str | None = None) -> str | None:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM axiom_state WHERE key = ?", (key,))
        row = await cur.fetchone()
    return row[0] if row else default


async def set_state(key: str, value: str) -> None:
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO axiom_state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


async def replace_pulse(rows: list[dict]) -> None:
    # Keep last good snapshot if a tick returns empty (API blip / auth fail).
    if not rows:
        return
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM axiom_pulse")
        for r in rows:
            await db.execute(
                """
                INSERT INTO axiom_pulse(
                    mint, symbol, name, chain, pair_address, price_usd, liquidity_usd,
                    market_cap_usd, volume_24h, change_1h, change_24h, image_url, url,
                    source, updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["mint"],
                    r.get("symbol") or "?",
                    r.get("name"),
                    r.get("chain") or "solana",
                    r.get("pair_address"),
                    r.get("price_usd"),
                    r.get("liquidity_usd"),
                    r.get("market_cap_usd"),
                    r.get("volume_24h"),
                    r.get("change_1h"),
                    r.get("change_24h"),
                    r.get("image_url"),
                    r.get("url"),
                    r.get("source") or "pulse",
                    now,
                    json.dumps(r.get("raw") or {}, ensure_ascii=False)[:4000],
                ),
            )
        await db.commit()


async def list_pulse(limit: int = 80) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT mint, symbol, name, chain, pair_address, price_usd, liquidity_usd,
                   market_cap_usd, volume_24h, change_1h, change_24h, image_url, url,
                   source, updated_at
            FROM axiom_pulse
            ORDER BY COALESCE(volume_24h, 0) DESC, COALESCE(liquidity_usd, 0) DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    return [
        {
            "mint": r[0],
            "symbol": r[1],
            "name": r[2],
            "chain": r[3],
            "pair_address": r[4],
            "price_usd": r[5],
            "liquidity_usd": r[6],
            "market_cap_usd": r[7],
            "volume_24h": r[8],
            "change_1h": r[9],
            "change_24h": r[10],
            "image_url": r[11],
            "url": r[12],
            "source": r[13],
            "updated_at": r[14],
        }
        for r in rows
    ]


async def replace_positions(rows: list[dict]) -> None:
    # Do not wipe open bags when collection fails empty.
    if not rows:
        return
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM axiom_positions")
        for r in rows:
            await db.execute(
                """
                INSERT INTO axiom_positions(
                    position_id, owner, owner_kind, mint, symbol, chain, status,
                    usd_size, amount, last_ts, url, image_url, updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["position_id"],
                    r["owner"],
                    r["owner_kind"],
                    r["mint"],
                    r.get("symbol") or "?",
                    r.get("chain") or "solana",
                    r.get("status") or "open",
                    r.get("usd_size"),
                    r.get("amount"),
                    r.get("last_ts"),
                    r.get("url"),
                    r.get("image_url"),
                    now,
                    json.dumps(r.get("raw") or {}, ensure_ascii=False)[:4000],
                ),
            )
        await db.commit()


async def list_positions(
    *,
    limit: int = 200,
    status: str | None = None,
    owner_kind: str | None = None,
) -> list[dict]:
    q = """
        SELECT position_id, owner, owner_kind, mint, symbol, chain, status,
               usd_size, amount, last_ts, url, image_url, updated_at
        FROM axiom_positions
        WHERE 1=1
    """
    params: list = []
    if status in ("open", "closed", "all"):
        if status != "all":
            q += " AND status = ?"
            params.append(status)
    if owner_kind:
        q += " AND owner_kind = ?"
        params.append(owner_kind)
    q += " ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, COALESCE(usd_size, 0) DESC LIMIT ?"
    params.append(limit)
    async with db_session() as db:
        cur = await db.execute(q, tuple(params))
        rows = await cur.fetchall()
    return [
        {
            "position_id": r[0],
            "owner": r[1],
            "owner_kind": r[2],
            "mint": r[3],
            "symbol": r[4],
            "chain": r[5],
            "status": r[6],
            "usd_size": r[7],
            "amount": r[8],
            "last_ts": r[9],
            "url": r[10],
            "image_url": r[11],
            "updated_at": r[12],
        }
        for r in rows
    ]


async def pulse_count() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM axiom_pulse")
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def positions_count(status: str | None = None) -> int:
    async with db_session() as db:
        if status in ("open", "closed"):
            cur = await db.execute(
                "SELECT COUNT(*) FROM axiom_positions WHERE status = ?", (status,)
            )
        else:
            cur = await db.execute("SELECT COUNT(*) FROM axiom_positions")
        row = await cur.fetchone()
    return int(row[0]) if row else 0

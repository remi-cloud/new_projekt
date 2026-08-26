"""SQLite persistence for Launch Scout candidates."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.sqlite import db_session


async def init_launch_scout_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS launch_candidates (
                candidate_id TEXT PRIMARY KEY,
                mint TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT DEFAULT '',
                chain TEXT NOT NULL,
                dex_id TEXT DEFAULT '',
                pair_address TEXT DEFAULT '',
                market_cap REAL,
                liq_usd REAL,
                pair_created_ms INTEGER,
                age_hours REAL,
                tier TEXT NOT NULL,
                score REAL DEFAULT 0,
                source TEXT DEFAULT 'dex',
                url TEXT DEFAULT '',
                price_usd REAL,
                tags_json TEXT DEFAULT '[]',
                updated_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}',
                image_url TEXT DEFAULT ''
            )
            """
        )
        try:
            await db.execute("ALTER TABLE launch_candidates ADD COLUMN image_url TEXT DEFAULT ''")
        except Exception:
            pass
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS launch_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_launch_tier_score ON launch_candidates(tier, score DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_launch_mc ON launch_candidates(market_cap ASC)"
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meme_whispers (
                id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                url TEXT DEFAULT '',
                ts_unix INTEGER NOT NULL,
                keywords_json TEXT DEFAULT '[]',
                source TEXT DEFAULT 'rss',
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_meme_whispers_ts ON meme_whispers(ts_unix DESC)"
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS launch_traders (
                wallet TEXT PRIMARY KEY,
                rank INTEGER NOT NULL,
                score REAL DEFAULT 0,
                buys INTEGER DEFAULT 0,
                source TEXT DEFAULT 'pump_public',
                updated_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS launch_trader_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                wallet TEXT NOT NULL,
                action TEXT NOT NULL,
                mint TEXT NOT NULL,
                symbol TEXT NOT NULL,
                chain TEXT NOT NULL,
                usd_amount REAL,
                ts_unix INTEGER NOT NULL,
                source TEXT DEFAULT 'pump',
                created_at TEXT NOT NULL,
                raw_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_launch_traders_rank ON launch_traders(rank ASC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_launch_trader_events_ts ON launch_trader_events(ts_unix DESC)"
        )
        await db.commit()


async def get_state(key: str, default: str | None = None) -> str | None:
    async with db_session() as db:
        cur = await db.execute("SELECT value FROM launch_state WHERE key = ?", (key,))
        row = await cur.fetchone()
    return row[0] if row else default


async def set_state(key: str, value: str) -> None:
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO launch_state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


async def replace_candidates(rows: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM launch_candidates")
        for c in rows:
            await db.execute(
                """
                INSERT INTO launch_candidates(
                    candidate_id, mint, symbol, name, chain, dex_id, pair_address,
                    market_cap, liq_usd, pair_created_ms, age_hours, tier, score,
                    source, url, price_usd, tags_json, updated_at, raw_json, image_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["candidate_id"],
                    c["mint"],
                    c.get("symbol") or "?",
                    c.get("name") or "",
                    c.get("chain") or "",
                    c.get("dex_id") or "",
                    c.get("pair_address") or "",
                    c.get("market_cap"),
                    c.get("liq_usd"),
                    c.get("pair_created_ms"),
                    c.get("age_hours"),
                    c.get("tier") or "watch",
                    float(c.get("score") or 0),
                    c.get("source") or "dex",
                    c.get("url") or "",
                    c.get("price_usd"),
                    json.dumps(c.get("tags") or [], ensure_ascii=False),
                    now,
                    json.dumps(c.get("raw") or {}, ensure_ascii=False)[:4000],
                    c.get("image_url") or "",
                ),
            )
        await db.commit()


async def list_candidates(tier: str | None = None, limit: int = 50) -> list[dict]:
    q = """
        SELECT candidate_id, mint, symbol, name, chain, dex_id, pair_address,
               market_cap, liq_usd, pair_created_ms, age_hours, tier, score,
               source, url, price_usd, tags_json, updated_at, image_url
        FROM launch_candidates
    """
    params: list = []
    if tier and tier != "all":
        q += " WHERE tier = ?"
        params.append(tier)
    q += " ORDER BY (market_cap IS NULL), market_cap ASC, score DESC LIMIT ?"
    params.append(max(1, min(200, limit)))
    async with db_session() as db:
        cur = await db.execute(q, tuple(params))
        rows = await cur.fetchall()
    out = []
    for r in rows:
        try:
            tags = json.loads(r[16] or "[]")
        except json.JSONDecodeError:
            tags = []
        out.append(
            {
                "candidate_id": r[0],
                "mint": r[1],
                "symbol": r[2],
                "name": r[3],
                "chain": r[4],
                "dex_id": r[5],
                "pair_address": r[6],
                "market_cap": r[7],
                "liq_usd": r[8],
                "pair_created_ms": r[9],
                "age_hours": r[10],
                "tier": r[11],
                "score": r[12],
                "source": r[13],
                "url": r[14],
                "price_usd": r[15],
                "tags": tags if isinstance(tags, list) else [],
                "updated_at": r[17],
                "image_url": (r[18] if len(r) > 18 else "") or "",
            }
        )
    return out


async def candidates_count(tier: str | None = None) -> int:
    async with db_session() as db:
        if tier and tier != "all":
            cur = await db.execute(
                "SELECT COUNT(*) FROM launch_candidates WHERE tier = ?", (tier,)
            )
        else:
            cur = await db.execute("SELECT COUNT(*) FROM launch_candidates")
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def upsert_whispers(rows: list[dict]) -> int:
    if not rows:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    async with db_session() as db:
        for w in rows:
            await db.execute(
                """
                INSERT INTO meme_whispers(id, author, text, url, ts_unix, keywords_json, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text = excluded.text,
                    url = excluded.url,
                    ts_unix = excluded.ts_unix,
                    keywords_json = excluded.keywords_json,
                    source = excluded.source
                """,
                (
                    w["id"],
                    w.get("author") or "elon",
                    (w.get("text") or "")[:800],
                    w.get("url") or "",
                    int(w.get("ts_unix") or 0),
                    json.dumps(w.get("keywords") or [], ensure_ascii=False),
                    w.get("source") or "rss",
                    now,
                ),
            )
            n += 1
        await db.commit()
    return n


async def list_whispers(limit: int = 20) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT id, author, text, url, ts_unix, keywords_json, source, created_at
            FROM meme_whispers
            ORDER BY ts_unix DESC
            LIMIT ?
            """,
            (max(1, min(100, limit)),),
        )
        rows = await cur.fetchall()
    out = []
    for r in rows:
        try:
            kws = json.loads(r[5] or "[]")
        except json.JSONDecodeError:
            kws = []
        out.append(
            {
                "id": r[0],
                "author": r[1],
                "text": r[2],
                "url": r[3],
                "ts_unix": r[4],
                "keywords": kws if isinstance(kws, list) else [],
                "source": r[6],
                "created_at": r[7],
            }
        )
    return out


async def whispers_count() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM meme_whispers")
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def replace_traders(traders: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM launch_traders")
        for t in traders:
            await db.execute(
                """
                INSERT INTO launch_traders(wallet, rank, score, buys, source, updated_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["wallet"],
                    int(t.get("rank") or 0),
                    float(t.get("score") or 0),
                    int(t.get("buys") or 0),
                    t.get("source") or "pump_public",
                    now,
                    json.dumps(t.get("raw") or {}, ensure_ascii=False)[:4000],
                ),
            )
        await db.commit()


async def list_traders(limit: int = 30) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT wallet, rank, score, buys, source, updated_at
            FROM launch_traders
            ORDER BY rank ASC
            LIMIT ?
            """,
            (max(1, min(50, limit)),),
        )
        rows = await cur.fetchall()
    return [
        {
            "wallet": r[0],
            "rank": r[1],
            "score": r[2],
            "buys": r[3],
            "source": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]


async def replace_trader_events(events: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute("DELETE FROM launch_trader_events")
        for e in events:
            await db.execute(
                """
                INSERT INTO launch_trader_events(
                    event_id, wallet, action, mint, symbol, chain,
                    usd_amount, ts_unix, source, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    usd_amount = excluded.usd_amount,
                    ts_unix = excluded.ts_unix
                """,
                (
                    e["event_id"],
                    e.get("wallet") or "",
                    e.get("action") or "buy",
                    e.get("mint") or "",
                    e.get("symbol") or "?",
                    e.get("chain") or "solana",
                    e.get("usd_amount"),
                    int(e.get("ts_unix") or 0),
                    e.get("source") or "pump",
                    now,
                    json.dumps(e.get("raw") or {}, ensure_ascii=False)[:2000],
                ),
            )
        await db.commit()


async def list_trader_events(limit: int = 40) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT event_id, wallet, action, mint, symbol, chain, usd_amount, ts_unix, source, created_at
            FROM launch_trader_events
            ORDER BY ts_unix DESC
            LIMIT ?
            """,
            (max(1, min(100, limit)),),
        )
        rows = await cur.fetchall()
    return [
        {
            "event_id": r[0],
            "wallet": r[1],
            "action": r[2],
            "mint": r[3],
            "symbol": r[4],
            "chain": r[5],
            "usd_amount": r[6],
            "ts_unix": r[7],
            "source": r[8],
            "created_at": r[9],
        }
        for r in rows
    ]


async def traders_count() -> int:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM launch_traders")
        row = await cur.fetchone()
    return int(row[0]) if row else 0

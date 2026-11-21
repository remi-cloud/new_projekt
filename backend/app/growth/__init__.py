"""Growth funnel: leads, newsletter, public live digest, watchlist."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from app.db.paths import ensure_data_dir
from app.db.sqlite import db_session

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def init_growth_db() -> None:
    ensure_data_dir()
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS newsletter_subs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                locale TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS business_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                package TEXT,
                message TEXT,
                locale TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist_votes (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                votes INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def subscribe_newsletter(email: str, locale: str | None = None, source: str = "web") -> dict:
    email = email.strip().lower()
    locale = (locale or "")[:12] or None
    source = (source or "web")[:40]
    if not EMAIL_RE.match(email) or len(email) > 200:
        raise ValueError("Invalid email")
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO newsletter_subs (email, locale, source, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET locale=excluded.locale, source=excluded.source
            """,
            (email, locale, source, now),
        )
        await db.commit()
    logger.info("Newsletter signup recorded")
    return {"ok": True}


async def create_lead(
    name: str,
    email: str,
    company: str | None = None,
    package: str | None = None,
    message: str | None = None,
    locale: str | None = None,
) -> dict:
    email = email.strip().lower()
    name = (name or "").strip()[:120]
    company = (company or "")[:160] or None
    package = (package or "")[:80] or None
    message = (message or "")[:4000] or None
    locale = (locale or "")[:12] or None
    if len(name) < 2:
        raise ValueError("Name required")
    if not EMAIL_RE.match(email) or len(email) > 200:
        raise ValueError("Invalid email")
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        cur = await db.execute(
            """
            INSERT INTO business_leads (name, email, company, package, message, locale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, email, company, package, message, locale, now),
        )
        await db.commit()
        lead_id = cur.lastrowid
    logger.info("New business lead #%s package=%s", lead_id, package or "—")
    return {"ok": True, "id": lead_id}


async def vote_watchlist(symbol: str, name: str | None = None) -> dict:
    symbol = (symbol or "").strip().upper()
    if not symbol or len(symbol) > 24:
        raise ValueError("Invalid symbol")
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO watchlist_votes (symbol, name, votes, updated_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                votes = votes + 1,
                name = COALESCE(excluded.name, watchlist_votes.name),
                updated_at = excluded.updated_at
            """,
            (symbol, name or symbol, now),
        )
        await db.commit()
        cur = await db.execute("SELECT votes FROM watchlist_votes WHERE symbol = ?", (symbol,))
        row = await cur.fetchone()
    return {"ok": True, "symbol": symbol, "votes": row[0] if row else 1}


async def top_watchlist(limit: int = 12) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT symbol, name, votes, updated_at
            FROM watchlist_votes
            ORDER BY votes DESC, updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    # No seeded "suggested" rows: the ranking shows only real votes (empty → UI empty state).
    return [
        {"symbol": r[0], "name": r[1] or r[0], "votes": r[2], "updated_at": r[3]}
        for r in rows
        if int(r[2] or 0) > 0
    ]


def list_packages() -> list[dict]:
    """Only features that exist in the app today. No invented prices or SLAs:
    pricing is agreed individually after a brief."""
    return [
        {
            "id": "api",
            "name": "API Feed",
            "price": "wycena indywidualna",
            "bullets": [
                "Cykl BTC JSON: /api/embed/cycle",
                "News makro: /api/news/macro",
            ],
        },
        {
            "id": "white-label",
            "name": "Embed",
            "price": "wycena indywidualna",
            "bullets": [
                "Widget cyklu BTC (iframe, /embed)",
                "Publiczny Live digest (/live)",
            ],
        },
        {
            "id": "alerts",
            "name": "Alerty",
            "price": "wycena indywidualna",
            "bullets": [
                "Push w przeglądarce, SMS (Twilio), ntfy",
                "Alerty sygnałów skanera i newsów makro",
            ],
        },
    ]

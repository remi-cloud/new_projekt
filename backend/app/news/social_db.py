"""SQLite store for social desk posts (X / LinkedIn)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.db.sqlite import db_session


def content_key(platform: str, news_id: str, url: str | None) -> str:
    raw = f"{platform}|{news_id}|{(url or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


async def init_social_db() -> None:
    async with db_session() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                news_id TEXT NOT NULL,
                content_key TEXT NOT NULL UNIQUE,
                url TEXT,
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                media_path TEXT,
                status TEXT NOT NULL DEFAULT 'dry_run',
                error TEXT,
                external_id TEXT,
                created_at TEXT NOT NULL,
                posted_at TEXT
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_social_posts_created ON social_posts(created_at DESC)"
        )
        await db.commit()


async def has_content_key(key: str) -> bool:
    async with db_session() as db:
        row = await (
            await db.execute("SELECT 1 FROM social_posts WHERE content_key = ? LIMIT 1", (key,))
        ).fetchone()
    return row is not None


async def insert_post(
    *,
    platform: str,
    news_id: str,
    url: str | None,
    title: str,
    body: str,
    media_path: str | None,
    status: str,
    error: str | None = None,
    external_id: str | None = None,
    posted_at: str | None = None,
) -> int:
    key = content_key(platform, news_id, url)
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        cur = await db.execute(
            """
            INSERT INTO social_posts
            (platform, news_id, content_key, url, title, body, media_path, status, error, external_id, created_at, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                platform,
                news_id,
                key,
                url,
                title[:300],
                body,
                media_path,
                status,
                error,
                external_id,
                now,
                posted_at,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_post(post_id: int) -> dict[str, Any] | None:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT id, platform, news_id, content_key, url, title, body, media_path,
                   status, error, external_id, created_at, posted_at
            FROM social_posts WHERE id = ?
            """,
            (post_id,),
        )
        row = await cur.fetchone()
    if not row:
        return None
    return _row(row)


async def list_posts(limit: int = 40) -> list[dict[str, Any]]:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT id, platform, news_id, content_key, url, title, body, media_path,
                   status, error, external_id, created_at, posted_at
            FROM social_posts
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 200)),),
        )
        rows = await cur.fetchall()
    return [_row(r) for r in rows]


async def update_post_status(
    post_id: int,
    *,
    status: str,
    error: str | None = None,
    external_id: str | None = None,
    posted_at: str | None = None,
) -> None:
    async with db_session() as db:
        await db.execute(
            """
            UPDATE social_posts
            SET status = ?, error = ?, external_id = COALESCE(?, external_id),
                posted_at = COALESCE(?, posted_at)
            WHERE id = ?
            """,
            (status, error, external_id, posted_at, post_id),
        )
        await db.commit()


async def last_posted_at(platform: str) -> datetime | None:
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT posted_at FROM social_posts
            WHERE platform = ? AND status = 'posted' AND posted_at IS NOT NULL
            ORDER BY posted_at DESC LIMIT 1
            """,
            (platform,),
        )
        row = await cur.fetchone()
    if not row or not row[0]:
        return None
    try:
        return datetime.fromisoformat(row[0])
    except ValueError:
        return None


def _row(r) -> dict[str, Any]:
    return {
        "id": r[0],
        "platform": r[1],
        "news_id": r[2],
        "content_key": r[3],
        "url": r[4],
        "title": r[5],
        "body": r[6],
        "media_path": r[7],
        "status": r[8],
        "error": r[9],
        "external_id": r[10],
        "created_at": r[11],
        "posted_at": r[12],
    }

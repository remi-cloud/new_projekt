"""Shared SQLite connection settings for durable persistence."""

from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite

from app.db.paths import database_path, ensure_data_dir


@asynccontextmanager
async def db_session():
    ensure_data_dir()
    async with aiosqlite.connect(str(database_path())) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        yield db

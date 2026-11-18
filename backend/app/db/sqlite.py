"""Shared SQLite connection settings for durable persistence."""

from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite

from app.db.paths import (
    database_path,
    ensure_data_dir,
    ensure_portfolio_dir,
    portfolio_database_path,
)


@asynccontextmanager
async def db_session():
    ensure_data_dir()
    async with aiosqlite.connect(str(database_path())) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        # The API and the Solana desk share this file. Wait instead of failing
        # the request when the other process holds the write lock.
        await db.execute("PRAGMA busy_timeout=5000")
        yield db


@asynccontextmanager
async def portfolio_db_session():
    ensure_portfolio_dir()
    async with aiosqlite.connect(str(portfolio_database_path())) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA busy_timeout=5000")
        yield db

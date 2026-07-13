"""Tests for portfolio agent and baza_portfela folder."""

import asyncio
import json

from app.db.paths import portfolio_snapshot_path
from app.paper.paper_db import get_positions, init_paper_db, reset_account, upsert_position
from app.paper.portfolio_agent import migrate_legacy_portfolio_if_needed, sync_on_startup


def test_sync_on_startup_writes_snapshot():
    async def _run():
        await init_paper_db()
        await reset_account()
        await upsert_position("PKO.WA", "PKO BP", "stock", 50.0, 44.0, "PLN")
        return await sync_on_startup()

    snapshot = asyncio.run(_run())
    assert snapshot["portfolio"]["positions_count"] == 1
    assert portfolio_snapshot_path().exists()
    data = json.loads(portfolio_snapshot_path().read_text(encoding="utf-8"))
    assert data["source"] == "portfolio_agent"
    assert data["portfolio"]["positions_count"] == 1


def test_migrate_legacy_idempotent():
    async def _run():
        await init_paper_db()
        first = await migrate_legacy_portfolio_if_needed()
        second = await migrate_legacy_portfolio_if_needed()
        return first, second

    first, second = asyncio.run(_run())
    assert second is False

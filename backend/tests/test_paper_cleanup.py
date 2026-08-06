"""Paper cleanup — purge execution agent positions."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.execution import db as exec_db
from app.db.database import init_db
from app.paper.cleanup import purge_execution_agent_positions
from app.paper.paper_db import get_position, init_paper_db, reset_account, upsert_position


def test_purge_closes_agent_symbol():
    async def _run():
        await init_db()
        await exec_db.init_execution_db()
        await init_paper_db()
        await reset_account()
        await upsert_position("BTC-USD", "Bitcoin", "crypto", 0.01, 60000.0, "USD")
        await exec_db.insert_proposal({
            "symbol": "BTC-USD",
            "name": "Bitcoin",
            "asset_class": "crypto",
            "region": "global",
            "broker_id": "kraken",
            "source": "opportunity",
            "confidence": 90,
            "amount_pln": 5000,
            "rationale": "agent",
            "status": "dry_run",
        })

        with patch("app.paper.cleanup.close_position", new=AsyncMock(return_value={})) as mock_close:
            result = await purge_execution_agent_positions(force=True)
        return result, mock_close.call_count

    result, calls = asyncio.run(_run())
    assert "BTC-USD" in result["purged"]
    assert calls == 1


def test_purge_skips_user_only_symbol():
    async def _run():
        await init_db()
        await exec_db.init_execution_db()
        await init_paper_db()
        await reset_account()
        await upsert_position("AAPL", "Apple", "stock", 10.0, 180.0, "USD")

        with patch("app.paper.cleanup._proposal_symbols", new=AsyncMock(return_value=set())):
            with patch(
                "app.paper.paper_db.list_symbols_for_trade_source",
                new=AsyncMock(return_value=["AAPL"]),
            ):
                with patch(
                    "app.paper.paper_db.get_trades_for_symbol",
                    new=AsyncMock(return_value=[{"trade_source": "user", "side": "buy"}]),
                ):
                    with patch("app.paper.cleanup.close_position", new=AsyncMock()) as mock_close:
                        result = await purge_execution_agent_positions(force=False)
        return result, mock_close.call_count

    result, calls = asyncio.run(_run())
    assert result["skipped"] and result["skipped"][0]["symbol"] == "AAPL"
    assert calls == 0

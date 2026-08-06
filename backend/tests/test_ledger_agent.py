"""Ledger agent — append, wipe DB, rebuild restores cash/positions/trade count."""

from __future__ import annotations

import asyncio
import json

from app.db.paths import portfolio_ledger_state_path, portfolio_ledger_trades_path
from app.db.sqlite import portfolio_db_session
from app.paper import paper_db
from app.paper.ledger_agent import (
    append_trade,
    export_db_to_ledger_if_empty,
    ledger_status,
    ledger_trade_count,
    rebuild_portfolio_from_ledger,
    reconcile_on_startup,
)
from app.paper.paper_db import INITIAL_CASH_PLN


def test_append_wipe_rebuild_restores_book():
    async def _run():
        await paper_db.init_paper_db()
        await paper_db.reset_account()

        # Seed a small book via DB + ledger append (same path as live trades)
        await paper_db.update_account_cash(950_000.0, realized_pnl_delta=100.0)
        await paper_db.upsert_position("BITO", "BITO", "etf", 100.0, 20.0, "USD")
        await paper_db.upsert_position("BTC-USD", "Bitcoin", "crypto", -0.05, 100_000.0, "USD")
        t1 = {
            "symbol": "BITO",
            "name": "BITO",
            "asset_class": "etf",
            "side": "buy",
            "quantity": 100.0,
            "price_native": 20.0,
            "price_pln": 80.0,
            "total_pln": 8000.0,
            "fee_pln": 5.0,
            "currency": "USD",
            "created_at": "2026-08-01T10:00:00+00:00",
            "trade_source": "user",
        }
        t2 = {
            "symbol": "BTC-USD",
            "name": "Bitcoin",
            "asset_class": "crypto",
            "side": "sell",
            "quantity": 0.05,
            "price_native": 100_000.0,
            "price_pln": 400_000.0,
            "total_pln": 20_000.0,
            "fee_pln": 10.0,
            "currency": "USD",
            "created_at": "2026-08-01T11:00:00+00:00",
            "trade_source": "user",
        }
        await paper_db.insert_trade(t1)
        await append_trade(t1)
        await paper_db.insert_trade(t2)
        await append_trade(t2)

        cash_before = float((await paper_db.get_account())["cash_pln"])
        realized_before = float((await paper_db.get_account())["realized_pnl_pln"])
        positions_before = {p["symbol"]: float(p["quantity"]) for p in await paper_db.get_positions()}
        assert ledger_trade_count() == 2

        # Simulate hard loss of SQLite book
        now = "2026-08-06T00:00:00+00:00"
        async with portfolio_db_session() as db:
            await db.execute("DELETE FROM paper_positions")
            await db.execute("DELETE FROM paper_trades")
            await db.execute(
                """UPDATE paper_account SET cash_pln = ?, initial_cash_pln = ?,
                   realized_pnl_pln = 0, updated_at = ? WHERE id = 1""",
                (INITIAL_CASH_PLN, INITIAL_CASH_PLN, now),
            )
            await db.commit()

        assert len(await paper_db.get_trades(limit=100)) == 0
        result = await rebuild_portfolio_from_ledger()
        assert result["rebuilt"] is True
        assert result["trades"] == 2

        account = await paper_db.get_account()
        positions = {p["symbol"]: float(p["quantity"]) for p in await paper_db.get_positions()}
        trades = await paper_db.get_trades(limit=100)
        assert float(account["cash_pln"]) == cash_before
        assert float(account["realized_pnl_pln"]) == realized_before
        assert positions == positions_before
        assert len(trades) == 2
        assert portfolio_ledger_trades_path().exists()
        assert portfolio_ledger_state_path().exists()
        state = json.loads(portfolio_ledger_state_path().read_text(encoding="utf-8"))
        assert state["trade_count"] == 2
        return True

    assert asyncio.run(_run()) is True


def test_export_then_reconcile_idempotent():
    async def _run():
        await paper_db.init_paper_db()
        await paper_db.reset_account()
        await paper_db.update_account_cash(999_000.0)
        await paper_db.upsert_position("AAPL", "Apple", "stock", 10.0, 150.0, "USD")
        trade = {
            "symbol": "AAPL",
            "name": "Apple",
            "asset_class": "stock",
            "side": "buy",
            "quantity": 10.0,
            "price_native": 150.0,
            "price_pln": 600.0,
            "total_pln": 6000.0,
            "fee_pln": 2.0,
            "currency": "USD",
            "created_at": "2026-08-02T12:00:00+00:00",
            "trade_source": "user",
        }
        await paper_db.insert_trade(trade)

        # Empty ledger → export from DB
        path = portfolio_ledger_trades_path()
        if path.exists():
            path.write_text("", encoding="utf-8")
        exported = await export_db_to_ledger_if_empty()
        assert exported is True
        assert ledger_trade_count() == 1

        status = await reconcile_on_startup()
        assert status["rebuilt"] is False
        assert status["ledger_trades"] == 1
        assert status["db_trades"] == 1
        assert status["ok"] is True

        ls = await ledger_status()
        assert ls["ledger_trades"] == 1
        assert ls["db_trades"] == 1
        assert ls["drift"] is False
        return True

    assert asyncio.run(_run()) is True


def test_reconcile_rebuilds_when_db_empty():
    async def _run():
        await paper_db.init_paper_db()
        await paper_db.reset_account()

        await paper_db.update_account_cash(980_000.0, realized_pnl_delta=50.0)
        await paper_db.upsert_position("MSFT", "Microsoft", "stock", 5.0, 400.0, "USD")
        trade = {
            "symbol": "MSFT",
            "name": "Microsoft",
            "asset_class": "stock",
            "side": "buy",
            "quantity": 5.0,
            "price_native": 400.0,
            "price_pln": 1600.0,
            "total_pln": 8000.0,
            "fee_pln": 3.0,
            "currency": "USD",
            "created_at": "2026-08-03T09:00:00+00:00",
            "trade_source": "execution_agent",
        }
        await paper_db.insert_trade(trade)
        await append_trade(trade)
        cash = float((await paper_db.get_account())["cash_pln"])

        now = "2026-08-06T01:00:00+00:00"
        async with portfolio_db_session() as db:
            await db.execute("DELETE FROM paper_positions")
            await db.execute("DELETE FROM paper_trades")
            await db.execute(
                """UPDATE paper_account SET cash_pln = ?, realized_pnl_pln = 0, updated_at = ?
                   WHERE id = 1""",
                (INITIAL_CASH_PLN, now),
            )
            await db.commit()

        status = await reconcile_on_startup()
        assert status["rebuilt"] is True
        assert status["ok"] is True
        account = await paper_db.get_account()
        assert float(account["cash_pln"]) == cash
        assert len(await paper_db.get_positions()) == 1
        assert len(await paper_db.get_trades(limit=10)) == 1
        return True

    assert asyncio.run(_run()) is True

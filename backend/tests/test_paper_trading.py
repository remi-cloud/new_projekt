"""Paper trading tests."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from app.models.schemas import AssetClass, AssetQuote
from app.paper.currency import native_currency, to_pln
from app.paper.executor import (
    _position_after_buy,
    _position_after_sell,
    close_position,
    place_order,
)
from app.paper.pricing import PaperTradeError
from app.paper.paper_db import (
    get_account,
    get_position,
    get_positions,
    init_paper_db,
    reset_account,
    update_account_cash,
    upsert_position,
)


def test_native_currency_pl():
    assert native_currency("PKO.WA") == "PLN"
    assert native_currency("AAPL") == "USD"


def test_to_pln():
    assert to_pln(100, "PLN", 4.0) == 100
    assert to_pln(100, "USD", 4.0) == 400


def test_paper_account_init_sync():
    async def _run():
        await init_paper_db()
        await reset_account()
        return await get_account()

    acc = asyncio.run(_run())
    assert acc["cash_pln"] == 1_000_000.0
    assert acc["initial_cash_pln"] == 1_000_000.0


def test_position_after_sell_opens_short_from_flat():
    qty, avg = _position_after_sell(0.0, 100.0, 10.0, 95.0)
    assert qty == -10.0
    assert avg == 95.0


def test_position_after_sell_flips_long_to_short():
    qty, avg = _position_after_sell(5.0, 100.0, 10.0, 95.0)
    assert qty == -5.0
    assert avg == 95.0


def test_position_after_buy_covers_short():
    qty, avg = _position_after_buy(-10.0, 100.0, 4.0, 90.0)
    assert qty == -6.0
    assert avg == 100.0


def test_positions_persist_after_reinit():
    """Simulates server restart — same absolute DB path, data survives."""

    async def _run():
        await init_paper_db()
        await reset_account()
        await upsert_position("PKO.WA", "PKO BP", "stock", 100.0, 45.5, "PLN")
        await update_account_cash(950_000.0)
        return await get_positions()

    positions = asyncio.run(_run())
    assert len(positions) == 1
    assert positions[0]["symbol"] == "PKO.WA"
    assert positions[0]["quantity"] == 100.0

    async def _after_restart():
        await init_paper_db()
        return await get_positions(), await get_account()

    positions2, account = asyncio.run(_after_restart())
    assert len(positions2) == 1
    assert positions2[0]["quantity"] == 100.0
    assert account["cash_pln"] == 950_000.0


def test_database_path_is_absolute():
    from app.db.paths import database_path, portfolio_database_path, portfolio_dir

    path = database_path()
    assert path.is_absolute()
    assert path.name == "trader.db"

    pf = portfolio_database_path()
    assert pf.is_absolute()
    assert pf.parent == portfolio_dir()
    assert pf.parent.name == "baza_portfela"


def test_short_sell_without_holding():
    quote = AssetQuote(
        symbol="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        price=150.0,
        change_pct_24h=0.0,
        change_pct_7d=0.0,
        currency="USD",
        updated_at=datetime.now(timezone.utc),
    )

    async def _run():
        await init_paper_db()
        await reset_account()
        with patch("app.paper.pricing.scanner") as mock_scanner, patch(
            "app.paper.executor.get_usd_pln_rate", return_value=4.0
        ):
            mock_scanner.quotes = [quote]
            await place_order("AAPL", "sell", quantity=2.0)
            pos = await get_position("AAPL")
            acc = await get_account()
            return pos, acc

    pos, acc = asyncio.run(_run())
    assert pos is not None
    assert pos["quantity"] == -2.0
    assert acc["cash_pln"] > 1_000_000.0


def test_close_long_position():
    quote = AssetQuote(
        symbol="PKO.WA",
        name="PKO BP",
        asset_class=AssetClass.STOCK,
        price=45.0,
        change_pct_24h=0.0,
        change_pct_7d=0.0,
        currency="PLN",
        updated_at=datetime.now(timezone.utc),
    )

    async def _run():
        await init_paper_db()
        await reset_account()
        with patch("app.paper.pricing.scanner") as mock_scanner, patch(
            "app.paper.executor.get_usd_pln_rate", return_value=4.0
        ):
            mock_scanner.quotes = [quote]
            await place_order("PKO.WA", "buy", quantity=10.0)
            trade = await close_position("PKO.WA")
            pos = await get_position("PKO.WA")
            return trade, pos

    trade, pos = asyncio.run(_run())
    assert trade["side"] == "sell"
    assert trade["quantity"] == 10.0
    assert pos is None


def test_close_short_position():
    quote = AssetQuote(
        symbol="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        price=150.0,
        change_pct_24h=0.0,
        change_pct_7d=0.0,
        currency="USD",
        updated_at=datetime.now(timezone.utc),
    )

    async def _run():
        await init_paper_db()
        await reset_account()
        with patch("app.paper.pricing.scanner") as mock_scanner, patch(
            "app.paper.executor.get_usd_pln_rate", return_value=4.0
        ):
            mock_scanner.quotes = [quote]
            await place_order("AAPL", "sell", quantity=3.0)
            trade = await close_position("AAPL")
            pos = await get_position("AAPL")
            return trade, pos

    trade, pos = asyncio.run(_run())
    assert trade["side"] == "buy"
    assert trade["quantity"] == 3.0
    assert pos is None


def test_close_position_without_holding_raises():
    async def _run():
        await init_paper_db()
        await reset_account()
        with patch("app.paper.pricing.scanner") as mock_scanner:
            mock_scanner.quotes = []
            try:
                await close_position("PKO.WA")
                return False
            except PaperTradeError as exc:
                return exc.code == "no_position"

    assert asyncio.run(_run()) is True

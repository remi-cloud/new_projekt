"""Paper trading tests."""


from app.paper.currency import native_currency, to_pln


def test_native_currency_pl():
    assert native_currency("PKO.WA") == "PLN"
    assert native_currency("AAPL") == "USD"


def test_to_pln():
    assert to_pln(100, "PLN", 4.0) == 100
    assert to_pln(100, "USD", 4.0) == 400


def test_paper_account_init_sync():
    import asyncio
    from app.paper.paper_db import get_account, init_paper_db

    async def _run():
        await init_paper_db()
        return await get_account()

    acc = asyncio.run(_run())
    assert acc["cash_pln"] == 1_000_000.0
    assert acc["initial_cash_pln"] == 1_000_000.0

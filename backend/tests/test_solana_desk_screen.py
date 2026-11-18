"""Dex pre-filter, Rugcheck holder shape, and pending-risk accounting."""

import asyncio

import httpx

from app.solana_desk.market import (
    apply_rugcheck,
    clear_report_cache,
    screen_tokens,
)
from app.solana_desk.models import DEFAULT_SETTINGS, MarketSnapshot, TokenView
from app.solana_desk.service import apply_snapshot, status_view

MINT = "Qb1LTGxhQfRiND2fBmLYpMXVDugPBTnATvYwz7Apump"


def _token(**overrides) -> TokenView:
    base = dict(
        mint=MINT,
        symbol="OK",
        price_usd=0.002,
        liquidity_usd=8_000,
        volume_usd=2_500,
        age_minutes=40,
        venue="pump_fun",
        change_5m_pct=6,
    )
    base.update(overrides)
    return TokenView(**base)


def test_screen_keeps_liquid_names_and_ranks_volume_first():
    loud = _token(mint="Loud111111111111111111111111111pump", volume_usd=50_000, liquidity_usd=9_000)
    quiet = _token(volume_usd=2_000, liquidity_usd=20_000, change_5m_pct=30)
    thin = _token(mint="Thin111111111111111111111111111pump", liquidity_usd=100)
    young = _token(mint="Young11111111111111111111111111pump", age_minutes=0.2)
    blind = _token(mint="Blind11111111111111111111111111pump", price_usd=0)
    ranked = screen_tokens([quiet, thin, young, blind, loud], DEFAULT_SETTINGS)
    assert [item.mint for item in ranked] == [loud.mint, quiet.mint]


def test_rugcheck_fixture_fills_holder_and_dev_pct():
    report = {
        "mint": MINT,
        "creator": "5Voxqwa8y9KRJNY71mrKHHs5MEVwuVVdySCJExrrUA6U",
        "creatorBalance": 0,
        "mintAuthority": None,
        "freezeAuthority": None,
        "rugged": False,
        "price": 0.0021,
        "totalMarketLiquidity": 2683.65,
        "token": {
            "mintAuthority": None,
            "freezeAuthority": None,
            "supply": 1_000_000_000_000_000,
            "decimals": 6,
        },
        "tokenMeta": {"name": "Band", "symbol": "BAND"},
        "transferFee": {"pct": 0, "maxAmount": 0, "authority": "11111111111111111111111111111111"},
        "risks": [{"name": "Single holder ownership", "value": "50.26%", "level": "danger"}],
        "topHolders": [
            {
                "address": "HaCWvgyKuwwD31tqasPhTgZTHtDM2oiF8e2TUSc9YDsw",
                "pct": 50.259200675804806,
                "owner": "BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s",
                "insider": False,
            },
            {
                "address": "5Voxqwa8y9KRJNY71mrKHHs5MEVwuVVdySCJExrrUA6U",
                "pct": "4.5%",
                "owner": "5Voxqwa8y9KRJNY71mrKHHs5MEVwuVVdySCJExrrUA6U",
                "insider": False,
            },
        ],
        "markets": [{"marketType": "pump_fun", "pubkey": "8bwYaGENfZFvCcufQzdeehD7NVWGnHkfRq8rMgJ2mLES"}],
    }
    parsed = apply_rugcheck(_token(risk_ready=False), report)
    assert parsed.risk_ready is True
    assert parsed.top_holder_pct == pytest_approx(50.2592)
    assert parsed.top10_holder_pct > 54
    assert parsed.dev_holder_pct == pytest_approx(4.5)
    assert parsed.mint_authority_active is False
    assert parsed.freeze_authority_active is False


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value, rel=1e-3)


def test_missing_report_is_pending_not_rejected():
    ready = _token(
        risk_ready=True,
        mint_authority_active=True,
        freeze_authority_active=False,
        top_holder_pct=80,
        top10_holder_pct=90,
        dev_holder_pct=1,
        can_sell=True,
    )
    waiting = _token(mint="Wait111111111111111111111111111pump", risk_ready=False)

    async def _run():
        from app.solana_desk.db import wipe_solana_desk

        await wipe_solana_desk()
        await apply_snapshot(
            MarketSnapshot(sol_usd=100, discovered=[ready, waiting], risk_pending=7)
        )
        view = await status_view()
        checker = view["agents"]["checker"]
        assert checker["rejected"] == 1
        assert checker["passed"] == 0
        assert "aktywne uprawnienie mint" in checker["reasons"]
        assert "brak raportu ryzyka" not in checker["reasons"]
        assert view["checker_pending_risk"] >= 7
        assert view["checker_reasons"]["aktywne uprawnienie mint"] == 1

    asyncio.run(_run())


def test_rugcheck_retries_429_then_uses_the_cache():
    from app.solana_desk.market import MarketClient

    class Response:
        def __init__(self, status: int, body: dict | None = None):
            self.status_code = status
            self._body = body or {}

        def json(self):
            return self._body

    class Client:
        def __init__(self):
            self.calls = 0

        async def get(self, url, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return Response(429)
            return Response(200, {"mintAuthority": None, "topHolders": []})

    client = Client()
    desk = MarketClient()

    async def _run():
        import app.solana_desk.market as market

        async def instant(_seconds: float) -> None:
            return None

        market._pause = instant
        clear_report_cache()
        first = await desk._rugcheck_many(client, [MINT], [])
        assert first[MINT] is not None
        assert client.calls == 2
        await desk._rugcheck_many(client, [MINT], [])
        assert client.calls == 2

    asyncio.run(_run())

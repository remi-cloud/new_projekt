"""Paper round trip: delayed entry, then a stop that keeps the gapped price."""

import asyncio
import json

from app.solana_desk.db import list_positions, list_trades, wipe_solana_desk
from app.solana_desk.models import MarketSnapshot, TokenView
from app.solana_desk.real_gate import KEY
from app.solana_desk.service import apply_snapshot, journal_csv, status_view

MINT = "FlowMint111111111111111111111111111pump"


def _token(price: float) -> TokenView:
    return TokenView(
        mint=MINT,
        symbol="FLOW",
        name="Flow",
        price_usd=price,
        liquidity_usd=12_000,
        volume_usd=4_000,
        age_minutes=25,
        venue="pump_fun",
        mint_authority_active=False,
        freeze_authority_active=False,
        top_holder_pct=6,
        top10_holder_pct=30,
        dev_holder_pct=1,
        buy_tax_pct=0,
        sell_tax_pct=0,
        can_sell=True,
        change_5m_pct=9,
        risk_ready=True,
    )


def test_stop_uses_the_next_price_and_keeps_a_journal(monkeypatch):
    monkeypatch.setenv("SOLANA_REAL_TRADING", "false")
    monkeypatch.setenv(KEY, "flow-secret-value-0123456789")
    from app.solana_desk.quotes import RouteQuote, install_router

    class Router:
        async def quote(self, *, input_mint, output_mint, amount, slippage_bps):
            if output_mint == MINT or input_mint != MINT:
                return RouteQuote(input_mint, output_mint, int(amount), int(amount), 0.4, 0, "jupiter", {"outAmount": str(amount)})
            return RouteQuote(input_mint, output_mint, int(amount), 20_000_000, 0.5, 0, "jupiter", {"outAmount": "20000000"})

        async def build_swap(self, quote, user_pubkey, priority_lamports):
            return "tx"

        async def rpc(self, method, params):
            return {"result": {"value": {"err": None}}}

        async def priority_fee_lamports(self, fallback, cap=10_000_000):
            return min(fallback, cap)

    install_router(Router())

    async def _run():
        await wipe_solana_desk()
        await apply_snapshot(MarketSnapshot(sol_usd=100, discovered=[_token(0.001)]))
        opened = await list_positions()
        assert len(opened) == 1
        assert opened[0]["status"] == "open"
        entry = float(opened[0]["entry_price"])
        assert entry > 0

        await apply_snapshot(MarketSnapshot(sol_usd=100, quotes={MINT: _token(0.0004)}))
        assert await list_positions() == []
        trades = await list_trades(10)
        assert len(trades) == 1
        closed = trades[0]
        assert float(closed["exit_price"]) < entry * 0.94
        assert float(closed["pnl_sol"]) < 0
        assert float(closed["entry_fee_sol"]) > 0
        assert float(closed["exit_fee_sol"]) > 0
        assert "kolejnej cenie" in (closed["exit_reason"] or "")
        assert closed["mode"] == "paper"
        assert closed["signature"] is None
        assert closed["fill_source"] in {"quote", "quote+sim", "model"}
        csv_body = await journal_csv()
        assert "mint" in csv_body.splitlines()[0]
        assert MINT in csv_body
        view = await status_view()
        blob = json.dumps(view)
        assert "flow-secret-value-0123456789" not in blob
        assert view["real_trading_active"] is False
        assert view["net_pnl_sol"] < 0
        await wipe_solana_desk()
        install_router(None)

    asyncio.run(_run())


def test_guest_cannot_control_and_status_stays_paper(client, monkeypatch):
    monkeypatch.setenv(KEY, "status-secret-value-0123456789")
    status = client.get("/api/solana/status")
    assert status.status_code == 200
    body = status.json()
    assert body["mode"] == "paper"
    assert body["real_trading_active"] is False
    assert "status-secret-value-0123456789" not in status.text

    blocked = client.post("/api/solana/control", json={"action": "stop"}, headers={"X-Desk-Token": ""})
    assert blocked.status_code == 401

    allowed = client.post("/api/solana/control", json={"action": "start"})
    assert allowed.status_code == 200
    assert allowed.json()["running"] is True

    saved = client.post("/api/solana/settings", json={"position_sol": 0.04, "daily_loss_sol": 0.15})
    assert saved.status_code == 200
    assert saved.json()["settings"]["position_sol"] == 0.04

    csv_res = client.get("/api/solana/trades.csv")
    assert csv_res.status_code == 200
    assert "cena_wejscia" in csv_res.text

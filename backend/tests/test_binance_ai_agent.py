"""Binance AI BOT dedup + broker registry (no network)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.execution.brokers import get_broker_adapter
from app.execution.models import SignalCandidate
from app.integrations.binance_ai_agent import _maybe_propose


@pytest.mark.asyncio
async def test_maybe_propose_skips_pending_broker_proposal():
    candidate = SignalCandidate(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class="crypto",
        source="pearl",
        confidence=80,
    )
    with patch(
        "app.integrations.binance_ai_agent.exec_db.pending_broker_proposal",
        new=AsyncMock(return_value={"id": 1, "status": "pending"}),
    ):
        created = await _maybe_propose(candidate, {"amount_pln": 10000, "cooldown_hours": 24}, True)
    assert created is False


@pytest.mark.asyncio
async def test_maybe_propose_skips_recent_cooldown():
    candidate = SignalCandidate(
        symbol="ETH-USD",
        name="Ethereum",
        asset_class="crypto",
        source="pearl",
        confidence=75,
    )
    with patch(
        "app.integrations.binance_ai_agent.exec_db.pending_broker_proposal",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.integrations.binance_ai_agent.exec_db.recent_symbol_proposal",
        new=AsyncMock(return_value={"broker_id": "binance", "status": "dry_run"}),
    ):
        created = await _maybe_propose(candidate, {"amount_pln": 10000, "cooldown_hours": 24}, True)
    assert created is False


@pytest.mark.asyncio
async def test_maybe_propose_inserts_when_clear():
    candidate = SignalCandidate(
        symbol="SOL-USD",
        name="Solana",
        asset_class="crypto",
        source="pearl",
        confidence=72,
    )
    insert = AsyncMock(return_value=42)
    with patch(
        "app.integrations.binance_ai_agent.exec_db.pending_broker_proposal",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.integrations.binance_ai_agent.exec_db.recent_symbol_proposal",
        new=AsyncMock(return_value=None),
    ), patch("app.integrations.binance_ai_agent.exec_db.insert_proposal", new=insert):
        created = await _maybe_propose(candidate, {"amount_pln": 10000, "cooldown_hours": 24}, True)
    assert created is True
    insert.assert_awaited_once()
    assert insert.await_args.args[0]["broker_id"] == "binance"


def test_binance_broker_registered():
    adapter = get_broker_adapter("binance")
    assert adapter.broker_id == "binance"

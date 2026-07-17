"""Tests for execution agent dry-run."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.execution.agent import run_once
from app.execution.models import SignalCandidate
from app.models.schemas import AssetClass, Opportunity, SignalAction
from datetime import datetime, timezone


def _opp(symbol: str = "AAPL", confidence: float = 85.0) -> Opportunity:
    return Opportunity(
        symbol=symbol,
        name="Apple",
        asset_class=AssetClass.STOCK,
        action=SignalAction.BUY,
        confidence=confidence,
        cycle_source="presidential",
        phase="year_1",
        price=180.0,
        rationale="Test buy",
        created_at=datetime.now(timezone.utc),
    )


def test_run_once_dry_run_creates_proposal():
    async def _run():
        from app.execution import db as exec_db
        from app.db.database import init_db

        await init_db()
        await exec_db.init_execution_db()

        candidate = SignalCandidate(
            symbol="TEST-EXEC",
            name="Test Exec",
            asset_class="stock",
            source="opportunity",
            confidence=90,
        )

        with patch("app.execution.agent.collect_signal_candidates", new=AsyncMock(return_value=[candidate])):
            with patch("app.execution.agent.check_risk", new=AsyncMock(return_value=(True, "ok"))):
                with patch("app.execution.agent.scanner") as mock_scanner:
                    mock_scanner.scan_in_progress = False
                    with patch("app.execution.agent.get_effective_settings", new=AsyncMock(return_value={
                        "enabled": True,
                        "dry_run": True,
                        "mirror_paper": False,
                        "require_approval": False,
                        "min_confidence": 70,
                        "amount_pln": 5000,
                        "max_daily": 10,
                        "cooldown_hours": 24,
                    })):
                        with patch("app.execution.agent.place_order", new=AsyncMock()):
                            return await run_once(force=True)

    result = asyncio.run(_run())
    assert result.created >= 1
    assert result.executed >= 1


def test_execute_proposal_dry_run_never_mirrors_paper():
    async def _run():
        from app.execution.agent import execute_proposal

        proposal = {
            "id": 101,
            "symbol": "BTC-USD",
            "asset_class": "crypto",
            "amount_pln": 10_000.0,
            "broker_id": "kraken",
        }
        eff = {
            "enabled": True,
            "dry_run": True,
            "mirror_paper": True,
            "require_approval": False,
            "min_confidence": 70,
            "amount_pln": 10_000,
            "max_daily": 5,
            "cooldown_hours": 24,
        }
        broker_result = MagicMock(success=True, dry_run=True, order_id="dry-1", message="dry")
        adapter = MagicMock(
            is_configured=AsyncMock(return_value=True),
            place_market_order=AsyncMock(return_value=broker_result),
        )
        with patch("app.execution.agent.exec_db.get_proposal", new=AsyncMock(return_value=proposal)):
            with patch("app.execution.agent.get_broker_adapter", return_value=adapter):
                with patch("app.execution.agent.exec_db.update_proposal", new=AsyncMock()):
                    with patch("app.execution.agent.place_order", new=AsyncMock()) as paper_mirror:
                        ok = await execute_proposal(101, eff)
                        return ok, paper_mirror.await_count

    ok, mirror_calls = asyncio.run(_run())
    assert ok is True
    assert mirror_calls == 0

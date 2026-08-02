"""Scanner facade tests — pipeline covered in test_agents.py."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.types import AgentScanResult
from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    BetaPhase,
    CyclePhase,
    Opportunity,
    SignalAction,
)
from app.scanners.opportunity_scanner import OpportunityScanner


def _alpha() -> AlphaModelStatus:
    return AlphaModelStatus(
        reference_date="2024-01-01",
        reference_price=100_000,
        current_price=80_000,
        days_since_reference=200,
        phase=CyclePhase.BEAR,
        phase_progress_pct=50,
        days_remaining_in_phase=100,
        signal=SignalAction.BUY,
        rationale="test",
    )


def _beta() -> BetaModelStatus:
    return BetaModelStatus(
        period_start="2025-01-20",
        period_end="2029-01-20",
        current_phase=BetaPhase.PHASE_3,
        phase_number=3,
        days_into_phase=100,
        days_remaining_in_phase=265,
        phase_progress_pct=27.0,
        historical_bias="test",
        signal=SignalAction.BUY,
        rationale="test",
    )


@pytest.mark.asyncio
async def test_scanner_facade_delegates_to_orchestrator():
    scanner = OpportunityScanner()
    opp = Opportunity(
        symbol="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        action=SignalAction.BUY,
        confidence=70,
        cycle_source="beta",
        phase="phase_3",
        price=100,
        rationale="t",
        created_at=datetime.now(timezone.utc),
    )
    fake = AgentScanResult(
        opportunities=[opp],
        long_findings=[],
        short_findings=[],
        long_verdicts=[],
        short_verdicts=[],
        alpha_model=_alpha(),
        beta_model=_beta(),
        quotes=[
            AssetQuote(
                symbol="AAPL",
                name="Apple",
                asset_class=AssetClass.STOCK,
                price=100,
                change_pct_24h=0,
                change_pct_7d=-2,
                updated_at=datetime.now(timezone.utc),
            )
        ],
        scanned_at=datetime.now(timezone.utc),
        scout_stats={"merged": 1},
    )
    with patch.object(scanner._orch, "run_pipeline", new=AsyncMock(return_value=fake)):
        # Also set state as pipeline would
        async def _run():
            scanner._orch.opportunities = fake.opportunities
            scanner._orch.alpha_model = fake.alpha_model
            scanner._orch.beta_model = fake.beta_model
            scanner._orch.quotes = fake.quotes
            scanner._orch.last_scan_at = fake.scanned_at
            scanner._orch.last_result = fake
            return fake

        with patch.object(scanner._orch, "run_pipeline", new=AsyncMock(side_effect=_run)):
            opps = await scanner.scan()

    assert len(opps) == 1
    assert opps[0].symbol == "AAPL"
    assert scanner.alpha_model is not None
    assert scanner.beta_model is not None

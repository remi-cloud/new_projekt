"""Tests for multi-agent LONG/SHORT pipeline."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator import AgentOrchestrator
from app.agents.scouts import build_scout_roster
from app.agents.specialists import LongSpecialist, ShortSpecialist
from app.agents.types import ScoutFinding
from app.agents.universes import default_universes
from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    BetaPhase,
    CyclePhase,
    SignalAction,
)


def _alpha(signal=SignalAction.SELL, phase=CyclePhase.BEAR, progress=20) -> AlphaModelStatus:
    return AlphaModelStatus(
        reference_date="2024-01-01",
        reference_price=100_000,
        current_price=80_000,
        days_since_reference=100,
        phase=phase,
        phase_progress_pct=progress,
        days_remaining_in_phase=200,
        signal=signal,
        rationale="test alpha",
    )


def _beta(phase=2, signal=SignalAction.SELL) -> BetaModelStatus:
    return BetaModelStatus(
        period_start="2025-01-20",
        period_end="2029-01-20",
        current_phase=BetaPhase(f"phase_{phase}"),
        phase_number=phase,
        days_into_phase=80,
        days_remaining_in_phase=280,
        phase_progress_pct=30.0,
        historical_bias="weak",
        signal=signal,
        rationale="test beta",
    )


def _q(symbol: str, ac: AssetClass, chg7: float) -> AssetQuote:
    return AssetQuote(
        symbol=symbol,
        name=symbol,
        asset_class=ac,
        price=100.0,
        change_pct_24h=1.0,
        change_pct_7d=chg7,
        updated_at=datetime.now(timezone.utc),
    )


def test_scout_roster_parity():
    roster = build_scout_roster()
    longs = [s for s in roster if s.side == "long"]
    shorts = [s for s in roster if s.side == "short"]
    assert len(roster) == 12
    assert len(longs) == 6
    assert len(shorts) == 6
    assert {s.region for s in longs} == {s.region for s in shorts}


def test_universes_cover_global_indexes():
    uni = default_universes()
    assert uni["us_equity"].symbols
    assert uni["crypto"].symbols
    assert "forex" in uni


@pytest.mark.asyncio
async def test_short_scout_finds_index_rally_in_weak_phase():
    roster = build_scout_roster(
        [
            {"symbol": "^GSPC", "name": "S&P", "asset_class": "index"},
            {"symbol": "QQQ", "name": "QQQ", "asset_class": "index"},
        ]
    )
    short_us = next(s for s in roster if s.scout_id == "short.us_equity")
    findings = await short_us.scout(
        [_q("^GSPC", AssetClass.INDEX, 4.0), _q("QQQ", AssetClass.INDEX, 5.0)],
        alpha=_alpha(),
        beta=_beta(),
    )
    assert len(findings) >= 1
    assert all(f.side == "short" for f in findings)


@pytest.mark.asyncio
async def test_long_scout_does_not_emit_shorts():
    roster = build_scout_roster(
        [{"symbol": "^GSPC", "name": "S&P", "asset_class": "index"}]
    )
    long_us = next(s for s in roster if s.scout_id == "long.us_equity")
    findings = await long_us.scout(
        [_q("^GSPC", AssetClass.INDEX, 4.0)],
        alpha=_alpha(),
        beta=_beta(),
    )
    assert all(f.side == "long" for f in findings)


def test_specialists_accept_and_tag_side():
    now = datetime.now(timezone.utc)
    finding = ScoutFinding(
        scout_id="short.us_equity",
        side="short",
        region="us_equity",
        symbol="QQQ",
        name="QQQ",
        asset_class=AssetClass.INDEX,
        price=400,
        confidence=70,
        phase="phase_2",
        cycle_source="beta",
        rationale="test",
    )
    short = ShortSpecialist().evaluate([finding], alpha=_alpha(), beta=_beta(), now=now)
    assert short and short[0].accepted
    assert short[0].opportunity is not None
    assert short[0].opportunity.action == SignalAction.SELL

    long_f = ScoutFinding(
        scout_id="long.us_equity",
        side="long",
        region="us_equity",
        symbol="AAPL",
        name="Apple",
        asset_class=AssetClass.STOCK,
        price=180,
        confidence=70,
        phase="phase_3",
        cycle_source="beta",
        rationale="test",
    )
    long = LongSpecialist().evaluate(
        [long_f],
        alpha=_alpha(SignalAction.BUY, CyclePhase.BULL, 40),
        beta=_beta(3, SignalAction.BUY),
        now=now,
    )
    assert long and long[0].opportunity.action == SignalAction.BUY


@pytest.mark.asyncio
async def test_orchestrator_pipeline_balanced():
    orch = AgentOrchestrator()
    watch = [
        {"symbol": "^GSPC", "name": "S&P", "asset_class": "index", "source": "yahoo", "enabled": 1},
        {"symbol": "QQQ", "name": "QQQ", "asset_class": "index", "source": "yahoo", "enabled": 1},
        {"symbol": "AAPL", "name": "Apple", "asset_class": "stock", "source": "yahoo", "enabled": 1},
        {"symbol": "TLT", "name": "TLT", "asset_class": "bond", "source": "yahoo", "enabled": 1},
        {"symbol": "BTC-USD", "name": "BTC", "asset_class": "crypto", "source": "yahoo", "enabled": 1},
        {"symbol": "EFA", "name": "EFA", "asset_class": "index", "source": "yahoo", "enabled": 1},
    ]
    quotes = [
        _q("^GSPC", AssetClass.INDEX, 3.5),
        _q("QQQ", AssetClass.INDEX, 4.0),
        _q("AAPL", AssetClass.STOCK, -6.0),
        _q("TLT", AssetClass.BOND, -1.0),
        _q("BTC-USD", AssetClass.CRYPTO, -7.0),
        _q("EFA", AssetClass.INDEX, 2.5),
    ]
    with (
        patch(
            "app.agents.orchestrator.fetch_bitcoin_ath",
            new=AsyncMock(return_value=(datetime(2024, 1, 1).date(), 100_000.0, 80_000.0)),
        ),
        patch("app.agents.orchestrator.analyze_bitcoin_cycle", return_value=_alpha()),
        patch("app.agents.orchestrator.analyze_presidential_cycle", return_value=_beta()),
        patch("app.agents.orchestrator.get_watchlist", new=AsyncMock(return_value=watch)),
        patch("app.agents.orchestrator.fetch_quotes", new=AsyncMock(return_value=quotes)),
    ):
        result = await orch.run_pipeline()

    assert result.scout_stats["scouts_long"] == 6
    assert result.scout_stats["scouts_short"] == 6
    assert result.scout_stats["short_scout_findings"] >= 1
    status = orch.roster_status()
    assert status["counts"]["equal"] is True
    # Must have at least one SHORT opportunity in weak regime with rallies
    shorts = [o for o in result.opportunities if o.action == SignalAction.SELL]
    assert len(shorts) >= 1

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
    Opportunity,
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
    global_syms = {s.upper() for s in uni["global_equity"].symbols}
    # Asia / Russia / Brazil / Europe must land in global_equity, not US
    for must in ("^N225", "^HSI", "^BVSP", "IMOEX.ME", "^GDAXI", "^BSESN", "EWZ"):
        assert must in global_syms, f"{must} missing from global_equity"
    us_syms = {s.upper() for s in uni["us_equity"].symbols}
    assert "^GSPC" in us_syms
    assert "^BVSP" not in us_syms


@pytest.mark.asyncio
async def test_uptrend_is_long_not_short_in_weak_phase():
    """Rising tape → LONG. Must not fade into SHORT only because Beta phase is weak."""
    roster = build_scout_roster(
        [
            {"symbol": "^GSPC", "name": "S&P", "asset_class": "index"},
            {"symbol": "QQQ", "name": "QQQ", "asset_class": "index"},
        ]
    )
    quotes = [
        _q("^GSPC", AssetClass.INDEX, 4.0),
        _q("QQQ", AssetClass.INDEX, 5.0),
    ]
    quotes[0].change_pct_24h = 1.0
    quotes[1].change_pct_24h = 1.2

    long_us = next(s for s in roster if s.scout_id == "long.us_equity")
    short_us = next(s for s in roster if s.scout_id == "short.us_equity")
    long_f = await long_us.scout(quotes, alpha=_alpha(), beta=_beta())
    short_f = await short_us.scout(quotes, alpha=_alpha(), beta=_beta())

    assert len(long_f) >= 1
    assert all(f.side == "long" for f in long_f)
    assert short_f == []


@pytest.mark.asyncio
async def test_downtrend_is_short():
    roster = build_scout_roster(
        [{"symbol": "^GSPC", "name": "S&P", "asset_class": "index"}]
    )
    short_us = next(s for s in roster if s.scout_id == "short.us_equity")
    q = _q("^GSPC", AssetClass.INDEX, -4.5)
    q.change_pct_24h = -1.2
    findings = await short_us.scout([q], alpha=_alpha(), beta=_beta())
    assert len(findings) >= 1
    assert findings[0].side == "short"


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
        change_pct_7d=-4.0,
        change_pct_24h=-1.5,
    )
    short = ShortSpecialist().evaluate([finding], alpha=_alpha(), beta=_beta(), now=now)
    assert short and short[0].accepted
    assert short[0].opportunity is not None
    assert short[0].opportunity.action == SignalAction.SELL

    # Rising tape must be vetoed for SHORT specialist
    rising = ScoutFinding(
        scout_id="short.us_equity",
        side="short",
        region="us_equity",
        symbol="SPY",
        name="SPY",
        asset_class=AssetClass.INDEX,
        price=500,
        confidence=70,
        phase="phase_2",
        cycle_source="beta",
        rationale="bad fade",
        change_pct_7d=4.0,
        change_pct_24h=1.0,
    )
    vetoed = ShortSpecialist().evaluate([rising], alpha=_alpha(), beta=_beta(), now=now)
    assert vetoed == []

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
        change_pct_7d=3.0,
        change_pct_24h=0.8,
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
    quotes[0].change_pct_24h = 0.8
    quotes[1].change_pct_24h = 1.0
    quotes[2].change_pct_24h = -1.5
    quotes[4].change_pct_24h = -2.0
    quotes[5].change_pct_24h = 0.6
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
    status = orch.roster_status()
    assert status["counts"]["equal"] is True
    longs = [o for o in result.opportunities if o.action in (SignalAction.BUY, SignalAction.WATCH)]
    shorts = [o for o in result.opportunities if o.action == SignalAction.SELL]
    assert len(longs) >= 1  # rising indexes → LONG
    assert len(shorts) >= 1  # dumping AAPL/BTC → SHORT
    assert any(o.symbol in ("^GSPC", "QQQ", "EFA") for o in longs)
    # No forced 50/50 — rising tape should not invent equal SHORTs
    assert result.scout_stats["merged_long"] >= result.scout_stats["merged_short"]
    # One symbol → one side only
    syms = [o.symbol for o in result.opportunities]
    assert len(syms) == len(set(syms))


def test_merge_book_trend_resolves_conflict():
    orch = AgentOrchestrator()
    long_o = Opportunity(
        symbol="SPY",
        name="SPY",
        asset_class=AssetClass.INDEX,
        action=SignalAction.BUY,
        confidence=70,
        cycle_source="beta",
        phase="phase_2",
        price=500,
        rationale="long",
        created_at=datetime.now(timezone.utc),
    )
    short_o = Opportunity(
        symbol="SPY",
        name="SPY",
        asset_class=AssetClass.INDEX,
        action=SignalAction.SELL,
        confidence=72,
        cycle_source="beta",
        phase="phase_2",
        price=500,
        rationale="short",
        created_at=datetime.now(timezone.utc),
    )
    q = _q("SPY", AssetClass.INDEX, 4.0)
    q.change_pct_24h = 1.0
    merged = orch._merge_book([long_o], [short_o], quotes=[q])
    assert len(merged) == 1
    assert merged[0].action == SignalAction.BUY
    assert "LONG" in merged[0].rationale or "trend" in merged[0].rationale.lower()

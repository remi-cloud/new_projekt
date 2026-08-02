from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    BetaPhase,
    CyclePhase,
    SignalAction,
)
from app.scanners.opportunity_scanner import OpportunityScanner


def _alpha(phase: CyclePhase, signal: SignalAction, progress: float = 50) -> AlphaModelStatus:
    return AlphaModelStatus(
        reference_date="2024-01-01",
        reference_price=100_000,
        current_price=80_000,
        days_since_reference=200,
        phase=phase,
        phase_progress_pct=progress,
        days_remaining_in_phase=100,
        signal=signal,
        rationale="test",
    )


def _beta(phase: int = 3) -> BetaModelStatus:
    return BetaModelStatus(
        period_start="2025-01-20",
        period_end="2029-01-20",
        current_phase=BetaPhase(f"phase_{phase}"),
        phase_number=phase,
        days_into_phase=100,
        days_remaining_in_phase=265,
        phase_progress_pct=27.0,
        historical_bias="test",
        signal=SignalAction.BUY,
        rationale="test",
    )


def _quote(symbol: str, asset_class: AssetClass, change_7d: float | None = -6) -> AssetQuote:
    return AssetQuote(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        price=100.0,
        change_pct_24h=-1.0,
        change_pct_7d=change_7d,
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_scan_crypto_buy_in_bear():
    scanner = OpportunityScanner()
    with (
        patch(
            "app.scanners.opportunity_scanner.fetch_bitcoin_ath",
            new=AsyncMock(return_value=(datetime(2024, 1, 1).date(), 100_000.0, 80_000.0)),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_bitcoin_cycle",
            return_value=_alpha(CyclePhase.BEAR, SignalAction.BUY, 70),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_presidential_cycle",
            return_value=_beta(3),
        ),
        patch(
            "app.scanners.opportunity_scanner.presidential_buy_weight",
            return_value=1.0,
        ),
        patch(
            "app.scanners.opportunity_scanner.get_watchlist",
            new=AsyncMock(
                return_value=[
                    {
                        "symbol": "BTC-USD",
                        "name": "Bitcoin",
                        "asset_class": "crypto",
                        "source": "yahoo",
                        "enabled": 1,
                    }
                ]
            ),
        ),
        patch(
            "app.scanners.opportunity_scanner.fetch_quotes",
            new=AsyncMock(return_value=[_quote("BTC-USD", AssetClass.CRYPTO)]),
        ),
    ):
        opps = await scanner.scan()

    assert len(opps) == 1
    assert opps[0].action == SignalAction.BUY
    assert opps[0].cycle_source == "alpha"
    assert opps[0].confidence >= 50


@pytest.mark.asyncio
async def test_scan_equity_phase3_boost():
    scanner = OpportunityScanner()
    with (
        patch(
            "app.scanners.opportunity_scanner.fetch_bitcoin_ath",
            new=AsyncMock(return_value=(datetime(2024, 1, 1).date(), 100_000.0, 80_000.0)),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_bitcoin_cycle",
            return_value=_alpha(CyclePhase.BULL, SignalAction.HOLD),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_presidential_cycle",
            return_value=_beta(3),
        ),
        patch(
            "app.scanners.opportunity_scanner.presidential_buy_weight",
            return_value=1.0,
        ),
        patch(
            "app.scanners.opportunity_scanner.get_watchlist",
            new=AsyncMock(
                return_value=[
                    {
                        "symbol": "AAPL",
                        "name": "Apple",
                        "asset_class": "stock",
                        "source": "yahoo",
                        "enabled": 1,
                    }
                ]
            ),
        ),
        patch(
            "app.scanners.opportunity_scanner.fetch_quotes",
            new=AsyncMock(return_value=[_quote("AAPL", AssetClass.STOCK, -4)]),
        ),
    ):
        opps = await scanner.scan()

    assert len(opps) == 1
    assert opps[0].action == SignalAction.BUY
    assert opps[0].confidence >= 60
    assert opps[0].phase == "phase_3"

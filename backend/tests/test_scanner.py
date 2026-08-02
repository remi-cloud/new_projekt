from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import (
    AssetClass,
    AssetQuote,
    BitcoinCycleStatus,
    CyclePhase,
    PresidentialCycleStatus,
    PresidentialYear,
    SignalAction,
)
from app.scanners.opportunity_scanner import OpportunityScanner


def _btc_cycle(phase: CyclePhase, signal: SignalAction, progress: float = 50) -> BitcoinCycleStatus:
    return BitcoinCycleStatus(
        last_ath_date="2024-01-01",
        last_ath_price=100_000,
        current_price=80_000,
        days_since_ath=200,
        phase=phase,
        phase_progress_pct=progress,
        days_remaining_in_phase=100,
        signal=signal,
        rationale="test",
    )


def _pres_cycle(year: int = 3) -> PresidentialCycleStatus:
    return PresidentialCycleStatus(
        term_start="2025-01-20",
        term_end="2029-01-20",
        president="Trump II",
        current_year=PresidentialYear(f"year_{year}"),
        year_number=year,
        days_into_year=100,
        days_remaining_in_year=265,
        year_progress_pct=27.0,
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
            return_value=_btc_cycle(CyclePhase.BEAR, SignalAction.BUY, 70),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_presidential_cycle",
            return_value=_pres_cycle(3),
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
async def test_scan_equity_year3_boost():
    scanner = OpportunityScanner()
    with (
        patch(
            "app.scanners.opportunity_scanner.fetch_bitcoin_ath",
            new=AsyncMock(return_value=(datetime(2024, 1, 1).date(), 100_000.0, 80_000.0)),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_bitcoin_cycle",
            return_value=_btc_cycle(CyclePhase.BULL, SignalAction.HOLD),
        ),
        patch(
            "app.scanners.opportunity_scanner.analyze_presidential_cycle",
            return_value=_pres_cycle(3),
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

"""Unit tests for cycle analysis logic."""

from datetime import date, timedelta

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.models.schemas import CyclePhase, PresidentialYear, SignalAction


def test_bitcoin_bear_phase():
    ath_date = date.today() - timedelta(days=100)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 80_000)
    assert result.phase == CyclePhase.BEAR
    assert result.days_since_ath == 100
    assert result.signal in (SignalAction.BUY, SignalAction.WATCH)


def test_bitcoin_bull_phase_early():
    ath_date = date.today() - timedelta(days=400)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 90_000)
    assert result.phase == CyclePhase.BULL
    assert result.signal == SignalAction.BUY


def test_bitcoin_distribution_late_bull():
    ath_date = date.today() - timedelta(days=1300)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 120_000)
    assert result.phase == CyclePhase.DISTRIBUTION
    assert result.signal == SignalAction.SELL


def test_bitcoin_post_cycle():
    ath_date = date.today() - timedelta(days=1500)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 110_000)
    assert result.phase == CyclePhase.DISTRIBUTION


def test_presidential_cycle_returns_valid_year():
    result = analyze_presidential_cycle()
    assert result.year_number in (1, 2, 3, 4)
    assert result.current_year in (
        PresidentialYear.YEAR_1,
        PresidentialYear.YEAR_2,
        PresidentialYear.YEAR_3,
        PresidentialYear.YEAR_4,
    )
    assert result.signal in (
        SignalAction.BUY,
        SignalAction.SELL,
        SignalAction.HOLD,
        SignalAction.WATCH,
    )


def test_presidential_year_3_is_strongest():
    # Jan 2027 = year 3 of Trump II term (started 2025-01-20)
    result = analyze_presidential_cycle(date(2027, 6, 1))
    assert result.year_number == 3
    assert result.signal == SignalAction.BUY
    assert len(result.year_returns) == 4
    year3 = next(y for y in result.year_returns if y.year_number == 3)
    assert year3.avg_return_pct == 16.0
    assert year3.is_current is True
    assert result.current_year_expected_return_pct == 16.0

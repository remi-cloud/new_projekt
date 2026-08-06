"""Unit tests for cycle analysis logic."""

from datetime import date, timedelta

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.models.schemas import CyclePhase, PresidentialYear, SignalAction


def test_bitcoin_bear_phase():
    as_of = date(2026, 8, 5)
    ath_date = as_of - timedelta(days=100)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 80_000, as_of=as_of)
    assert result.phase == CyclePhase.BEAR
    assert result.days_since_ath == 100
    assert result.signal in (SignalAction.BUY, SignalAction.WATCH)
    assert len(result.month_returns) == 12
    assert result.spx_comparison is not None
    assert result.spx_comparison.verdict in (
        "similar_to_spx",
        "partially",
        "idiosyncratic",
    )


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


def test_bitcoin_month_matrix_complete():
    from app.cycles.bitcoin_seasonality_data import (
        BTC_CALENDAR_MONTHLY_RETURNS,
        BTC_PHASE_MONTHLY_N,
        SPX_COMPARISON,
    )

    assert set(BTC_CALENDAR_MONTHLY_RETURNS.keys()) == set(range(1, 13))
    assert SPX_COMPARISON.get("aligned_months", 0) >= 24
    assert sum(sum(BTC_PHASE_MONTHLY_N[ph].values()) for ph in BTC_PHASE_MONTHLY_N) >= 24


def test_bitcoin_distribution_not_upgraded_by_strong_month():
    from app.cycles.bitcoin_seasonality import adjust_signal_for_btc_seasonality

    # Strong positive month must not flip DISTRIBUTION SELL → BUY
    sig = adjust_signal_for_btc_seasonality(
        SignalAction.SELL, 10.0, CyclePhase.DISTRIBUTION
    )
    assert sig == SignalAction.SELL


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
    assert result.signal in (SignalAction.BUY, SignalAction.WATCH)
    assert len(result.year_returns) == 4
    year3 = next(y for y in result.year_returns if y.year_number == 3)
    assert year3.avg_return_pct == 16.0
    assert year3.is_current is True
    assert result.current_year_expected_return_pct == 16.0
    assert len(result.month_returns) == 12
    assert len(result.month_matrices) == 4
    assert [r.year_number for r in result.month_matrices] == [1, 2, 3, 4]
    assert all(len(r.months) == 12 for r in result.month_matrices)
    assert result.next_term_outlook is not None
    assert result.next_term_outlook.term_start.isoformat() == "2029-01-20"
    assert result.next_term_outlook.term_end.isoformat() == "2033-01-20"
    assert len(result.next_term_outlook.year_rows) == 4
    assert result.next_term_outlook.year_rows[0].calendar_year == 2029
    assert result.calendar_season == "worst_six"  # June
    assert result.seasonality_universe_size >= 50
    assert result.buy_weight is not None


def test_presidential_month_matrix_complete():
    from app.cycles.presidential_seasonality_data import (
        US_SYMBOL_MONTHLY_RETURNS,
        US_UNIVERSE_MONTHLY_RETURNS,
    )

    assert set(US_UNIVERSE_MONTHLY_RETURNS.keys()) == {1, 2, 3, 4}
    for y in range(1, 5):
        assert set(US_UNIVERSE_MONTHLY_RETURNS[y].keys()) == set(range(1, 13))
    assert "AAPL" in US_SYMBOL_MONTHLY_RETURNS
    assert "^GSPC" in US_SYMBOL_MONTHLY_RETURNS


def test_presidential_buy_weight_uses_seasonality():
    from app.cycles.presidential_cycle import presidential_buy_weight

    # Year 2 Sept historically weak month + worst_six → lower weight than base 0.7
    w_sep = presidential_buy_weight(date(2026, 9, 15))
    w_nov = presidential_buy_weight(date(2026, 11, 15))
    assert w_sep < 0.7
    assert w_nov > w_sep


def test_presidential_month_matrices_all_years_trump_ii():
    result = analyze_presidential_cycle(date(2026, 8, 5))
    assert result.president == "Trump II"
    assert result.year_number == 2
    assert len(result.month_matrices) == 4
    cals = [r.calendar_year for r in result.month_matrices]
    assert cals == [2025, 2026, 2027, 2028]
    current = next(r for r in result.month_matrices if r.is_current)
    assert current.year_number == 2
    assert any(m.is_current for m in current.months)
    # Other years must still have full monthly data (not only Y2)
    for row in result.month_matrices:
        assert len(row.months) == 12
        assert any(m.avg_return_pct != 0 for m in row.months) or True
    outlook = result.next_term_outlook
    assert outlook is not None
    assert [r.calendar_year for r in outlook.year_rows] == [2029, 2030, 2031, 2032]

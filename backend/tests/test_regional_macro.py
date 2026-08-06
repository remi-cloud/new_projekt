"""Tests for regional macro cycle analysis."""

from datetime import date

from app.cycles.regional_macro import (
    REGION_MACRO_WEIGHT,
    analyze_europe_cycle,
    analyze_polish_cycle,
    analyze_regional_macro,
    build_regional_cycles_snapshot,
    macro_weight_for_region,
)
from app.models.schemas import SignalAction
from app.scanners.asset_analyzer import _combine_signals, _signals_conflict


def test_polish_mid_term_july_2026():
    result = analyze_polish_cycle(date(2026, 7, 13))
    assert result.cycle_id == "polish_cycle"
    # ~21 months after Oct 2023 elections → mid_term
    assert result.phase == "mid_term"
    assert result.signal in (SignalAction.HOLD, SignalAction.WATCH, SignalAction.BUY)


def test_polish_pre_election():
    result = analyze_polish_cycle(date(2027, 8, 1))
    assert result.phase in ("pre_election_volatility", "pre_election_caution")
    assert result.signal == SignalAction.WATCH


def test_us_region_uses_presidential():
    result = analyze_regional_macro("us", "stock", "AAPL", date(2026, 7, 13))
    assert result.cycle_id == "presidential_cycle"


def test_pl_region_not_presidential():
    result = analyze_regional_macro("pl", "stock", "PKO.WA", date(2026, 7, 13))
    assert result.cycle_id == "polish_cycle"


def test_europe_cycle_valid():
    result = analyze_europe_cycle(date(2026, 7, 13))
    assert result.cycle_id == "europe_cycle"
    assert 0 <= result.buy_weight <= 1


def test_regional_macro_weights():
    assert macro_weight_for_region("us") == REGION_MACRO_WEIGHT["us"]
    assert macro_weight_for_region("pl") < macro_weight_for_region("us")
    assert macro_weight_for_region("unknown") == 0.40


def test_snapshot_has_six_regions():
    snap = build_regional_cycles_snapshot(date(2026, 7, 13))
    assert set(snap.keys()) == {"us", "pl", "eu", "asia", "em", "global"}


def test_signal_conflict_detection():
    assert _signals_conflict(SignalAction.BUY, SignalAction.SELL)
    assert not _signals_conflict(SignalAction.BUY, SignalAction.WATCH)


def test_combine_signals_conflict_favors_price():
    """Macro BUY + price SELL at highs should not always yield BUY."""
    macro_sig, macro_conf = SignalAction.BUY, 75.0
    price_sig, price_conf = SignalAction.SELL, 70.0
    final, _ = _combine_signals(macro_sig, macro_conf, price_sig, price_conf, region="pl")
    assert final in (SignalAction.WATCH, SignalAction.HOLD, SignalAction.SELL)

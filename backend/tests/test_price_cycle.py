"""Tests for price cycle analysis."""

from app.cycles.price_cycle import analyze_price_cycle
from app.models.schemas import CyclePhase, SignalAction


def test_at_highs_distribution():
    phase, signal, conf, _ = analyze_price_cycle(100, 102, 80)
    assert phase == CyclePhase.DISTRIBUTION
    assert signal == SignalAction.SELL


def test_deep_drawdown_buy():
    phase, signal, conf, _ = analyze_price_cycle(65, 100, 50)
    assert phase == CyclePhase.BEAR
    assert signal == SignalAction.BUY
    assert conf > 60


def test_moderate_correction_watch():
    phase, signal, _, _ = analyze_price_cycle(85, 100, 70)
    assert signal in (SignalAction.WATCH, SignalAction.HOLD)

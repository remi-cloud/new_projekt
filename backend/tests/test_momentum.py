"""Unit tests for momentum cycle analysis."""

from app.cycles.momentum_cycle import (
    analyze_momentum,
    compute_momentum_indicators,
    momentum_aligns_with_cycle,
)
from app.models.schemas import SignalAction


def _trending_up_closes(n: int = 60, start: float = 100.0) -> list[float]:
    """Uptrend with small pullbacks — more realistic than linear ramp."""
    closes = [start]
    for i in range(1, n):
        if i % 7 == 0:
            closes.append(closes[-1] * 0.985)
        else:
            closes.append(closes[-1] * 1.008)
    return closes


def _trending_down_closes(n: int = 60, start: float = 200.0) -> list[float]:
    """Downtrend without deep oversold — momentum should read bearish."""
    closes = [start]
    for i in range(1, n):
        if i % 9 == 0:
            closes.append(closes[-1] * 1.008)
        else:
            closes.append(closes[-1] * 0.993)
    return closes


def test_compute_momentum_indicators_returns_rsi():
    closes = _trending_up_closes()
    indicators = compute_momentum_indicators(closes)
    assert indicators["rsi_14"] is not None
    assert indicators["roc_20d"] is not None
    assert indicators["macd_histogram"] is not None


def test_uptrend_momentum_signals_buy():
    closes = _trending_up_closes()
    indicators = compute_momentum_indicators(closes)
    signal, conf, phase, score, _ = analyze_momentum(indicators)
    assert score >= 50
    assert signal in (SignalAction.BUY, SignalAction.WATCH)
    assert conf >= 50


def test_downtrend_momentum_signals_sell():
    closes = _trending_down_closes()
    indicators = compute_momentum_indicators(closes)
    signal, conf, phase, score, _ = analyze_momentum(indicators)
    assert score <= 50
    assert signal in (SignalAction.SELL, SignalAction.WATCH, SignalAction.HOLD)


def test_momentum_aligns_with_cycle():
    assert momentum_aligns_with_cycle(SignalAction.BUY, SignalAction.BUY)
    assert momentum_aligns_with_cycle(SignalAction.BUY, SignalAction.WATCH)
    assert momentum_aligns_with_cycle(SignalAction.SELL, SignalAction.SELL)
    assert not momentum_aligns_with_cycle(SignalAction.BUY, SignalAction.SELL)

"""Tests for alert engine."""

from datetime import datetime, timezone

from app.models.schemas import AssetClass, AssetCycleAssessment, SignalAction
from app.notifications.alert_engine import AlertEngine


def _assessment(symbol: str, signal: SignalAction, conf: float, price: float):
    now = datetime.now(timezone.utc)
    return AssetCycleAssessment(
        symbol=symbol,
        name=symbol,
        asset_class=AssetClass.STOCK,
        region="us",
        price=price,
        macro_cycle="test",
        macro_phase="test",
        price_phase="bull",
        signal=signal,
        confidence=conf,
        rationale="test",
        updated_at=now,
    )


def test_alert_on_signal_change():
    engine = AlertEngine()
    engine.reset([_assessment("AAPL", SignalAction.BUY, 70, 100)])
    events = engine.diff([_assessment("AAPL", SignalAction.SELL, 75, 98)])
    assert len(events) == 1
    assert events[0].previous_action == "buy"


def test_no_alert_below_confidence():
    engine = AlertEngine()
    engine.reset([_assessment("AAPL", SignalAction.BUY, 70, 100)])
    events = engine.diff([_assessment("AAPL", SignalAction.SELL, 50, 98)], min_confidence=60)
    assert len(events) == 0

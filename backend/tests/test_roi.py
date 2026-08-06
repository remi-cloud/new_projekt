"""Unit tests for ROI calculator (synthetic candles)."""

from datetime import date, datetime, timezone

from app.models.schemas import ChartCandle, CyclePhase, SignalAction
from app.roi.calculator import _phase_for_bar, _run_strategy


def _bars(prices: list[float], start: date = date(2018, 1, 1)) -> list[ChartCandle]:
    out: list[ChartCandle] = []
    for i, p in enumerate(prices):
        ts = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp()) + i * 86400 * 7
        out.append(ChartCandle(time=ts, open=p, high=p * 1.02, low=p * 0.98, close=p))
    return out


def test_buy_hold_doubles():
    candles = _bars([100.0] * 2 + [200.0] * 2)
    curve, trades, invested = _run_strategy(candles, 1000.0, "buy_hold", "stock", "us", 4)
    assert invested == 1000.0
    assert trades[0].action == "buy"
    assert curve[-1].equity == 2000.0


def test_cycle_crypto_runs():
    prices = [10 + i * 2 for i in range(40)] + [80 - i for i in range(30)] + [50 + i for i in range(40)]
    candles = _bars(prices, date(2015, 1, 1))
    curve, trades, invested = _run_strategy(candles, 1000.0, "cycle", "crypto", "global", 4)
    assert invested == 1000.0
    assert len(curve) == len(candles)
    assert curve[-1].equity > 0


def test_us_near_high_stays_invested_not_sell():
    """US: within 3% of 52w high → stay invested (BUY/HOLD), never forced SELL."""
    prices = [100.0] * 60 + [99.0]
    candles = _bars(prices, date(2018, 1, 1))
    phase, signal, rationale = _phase_for_bar(candles, len(candles) - 1, "index", "us")
    assert signal != SignalAction.SELL
    assert signal in (SignalAction.BUY, SignalAction.HOLD)
    assert "invested" in rationale.lower() or "stay" in rationale.lower() or "dip" in rationale.lower()
    assert phase in (CyclePhase.BULL, CyclePhase.ACCUMULATION)


def test_us_dip_buys():
    """US: ≥10% off 52w high → BUY dip."""
    prices = [100.0] * 55 + [85.0] * 5
    candles = _bars(prices, date(2018, 1, 1))
    _phase, signal, rationale = _phase_for_bar(candles, len(candles) - 1, "index", "us")
    assert signal == SignalAction.BUY
    assert "dip" in rationale.lower() or "buy" in rationale.lower()

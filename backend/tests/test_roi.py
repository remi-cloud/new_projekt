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


def test_price_cycle_uptrend_is_invested():
    """Non-crypto: price above the 200-session average (+2% band) → growth phase, BUY."""
    prices = [100.0 + i * 0.5 for i in range(260)]
    candles = _bars(prices, date(2018, 1, 1))
    phase, signal, rationale = _phase_for_bar(candles, len(candles) - 1, "index", "us")
    assert signal == SignalAction.BUY
    assert phase == CyclePhase.BULL
    assert "sma200" in rationale.lower()


def test_price_cycle_break_below_average_goes_to_cash():
    """Non-crypto: a close >2% under the long average flips to the decline phase (SELL)."""
    prices = [100.0 + i * 0.5 for i in range(240)] + [150.0] * 5 + [120.0] * 5
    candles = _bars(prices, date(2018, 1, 1))
    phase, signal, _ = _phase_for_bar(candles, len(candles) - 1, "commodity", "global")
    assert signal == SignalAction.SELL
    assert phase == CyclePhase.BEAR


def test_cycle_strategy_differs_from_buy_hold_when_trend_breaks():
    """Regression: the US 'cycle' used to be always-BUY, i.e. identical to buy & hold."""
    up = [100.0 + i for i in range(300)]
    crash = [400.0 - i * 4 for i in range(60)]
    recover = [160.0 + i * 2 for i in range(120)]
    candles = _bars(up + crash + recover, date(2010, 1, 1))
    cyc, trades, _ = _run_strategy(candles, 1000.0, "cycle", "index", "us", 4, sim_start_idx=250)
    bh, _, _ = _run_strategy(candles, 1000.0, "buy_hold", "index", "us", 4, sim_start_idx=250)
    assert any(t.action == "sell" for t in trades)
    assert cyc[-1].equity != bh[-1].equity

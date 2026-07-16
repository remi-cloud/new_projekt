"""Unit tests for ROI calculator (synthetic candles)."""

from datetime import date, datetime, timezone

from app.models.schemas import ChartCandle
from app.roi.calculator import _run_strategy


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
    # Rising then falling path to create ATH and later distribution
    prices = [10 + i * 2 for i in range(40)] + [80 - i for i in range(30)] + [50 + i for i in range(40)]
    candles = _bars(prices, date(2015, 1, 1))
    curve, trades, invested = _run_strategy(candles, 1000.0, "cycle", "crypto", "global", 4)
    assert invested == 1000.0
    assert len(curve) == len(candles)
    assert curve[-1].equity > 0

"""Tests for historical cyclical chart markers."""

from datetime import date, datetime, timezone

from app.cycles.signal_history import compute_cycle_markers
from app.models.schemas import ChartCandle, SignalAction


def _daily_candles(prices: list[float], start: date | None = None) -> list[ChartCandle]:
    start = start or date(2024, 1, 1)
    out: list[ChartCandle] = []
    for i, p in enumerate(prices):
        ts = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp()) + i * 86400
        out.append(
            ChartCandle(
                time=ts,
                open=p,
                high=p * 1.02,
                low=p * 0.98,
                close=p,
            )
        )
    return out


def test_compute_cycle_markers_paired_entry_exit():
    prices = [200.0] * 30 + [200.0 - i * 2.5 for i in range(35)] + [112.5 + i * 2 for i in range(40)] + [192.0 + i * 0.5 for i in range(30)]
    candles = _daily_candles(prices, start=date(2023, 1, 1))
    markers = compute_cycle_markers(
        candles,
        preset="3M",
        asset_class="stock",
        region="us",
        symbol="AAPL",
    )
    assert len(markers) >= 2
    assert markers[0].action == SignalAction.BUY
    assert any(m.action == SignalAction.SELL for m in markers[1:])
    assert "." in markers[0].rationale  # date in rationale


def test_compute_cycle_markers_short_series_empty():
    candles = _daily_candles([100.0] * 20)
    markers = compute_cycle_markers(candles, preset="3M", symbol="AAPL")
    assert markers == []

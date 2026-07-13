"""Chart preset tests."""

from app.data.chart_data import CHART_PRESETS, INTRADAY_PRESETS, _aggregate_candles
from app.models.schemas import ChartCandle


def test_intraday_presets_defined():
    assert INTRADAY_PRESETS == frozenset({"1m", "5m", "15m", "30m", "1H", "4H"})
    for key in INTRADAY_PRESETS:
        assert key in CHART_PRESETS


def test_aggregate_candles_4h():
    raw = [
        ChartCandle(time=i, open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=10)
        for i in range(8)
    ]
    merged = _aggregate_candles(raw, 4)
    assert len(merged) == 2
    assert merged[0].open == raw[0].open
    assert merged[0].close == raw[3].close
    assert merged[0].high == max(c.high for c in raw[0:4])

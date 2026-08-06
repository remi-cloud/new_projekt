"""Tests for Investing.com chart parsing."""

from app.data.investing_com import _parse_quote_from_candles


def test_parse_quote_from_daily_candles():
    candles = [
        [1_700_000_000_000, 90.0, 91.0, 89.0, 90.5, 1000, 0],
        [1_700_086_400_000, 90.5, 92.0, 90.0, 91.0, 1100, 0],
        [1_700_172_800_000, 91.0, 93.0, 90.5, 92.0, 1200, 0],
        [1_700_259_200_000, 92.0, 94.0, 91.5, 93.0, 1300, 0],
        [1_700_345_600_000, 93.0, 95.0, 92.5, 94.0, 1400, 0],
        [1_700_432_000_000, 94.0, 96.0, 93.5, 95.0, 1500, 0],
        [1_700_518_400_000, 95.0, 97.0, 94.5, 96.0, 1600, 0],
    ]
    price, ch24, ch7, stats = _parse_quote_from_candles(candles)
    assert price == 96.0
    assert ch24 is not None
    assert ch7 is not None
    assert stats["high_52w"] == 97.0
    assert stats["low_52w"] == 89.0

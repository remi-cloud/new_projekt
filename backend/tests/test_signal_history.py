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
    # Deep V: long peak → crash ≥25% → bounce lock-in → recovery toward distribution.
    prices = (
        [200.0] * 40
        + [200.0 - i * 3 for i in range(1, 40)]  # down to ~83 (~58% DD)
        + [83.0 + i * 1.5 for i in range(1, 50)]  # bounce + recovery
        + [155.0 + i * 0.8 for i in range(40)]  # push toward highs
    )
    candles = _daily_candles(prices, start=date(2023, 1, 1))
    markers = compute_cycle_markers(
        candles,
        preset="3M",
        asset_class="stock",
        region="us",
        symbol="AAPL",
    )
    buys = [m for m in markers if m.action == SignalAction.BUY]
    sells = [m for m in markers if m.action == SignalAction.SELL]
    assert len(buys) >= 1
    assert "." in buys[0].rationale
    watches = [m for m in markers if m.action == SignalAction.WATCH]
    assert len(watches) >= 1
    assert watches[0].time <= buys[0].time
    assert "short ongoing" in watches[0].rationale.lower()
    if sells:
        assert sells[0].time > buys[0].time


def test_compute_cycle_markers_short_series_empty():
    candles = _daily_candles([100.0] * 20)
    markers = compute_cycle_markers(candles, preset="3M", symbol="AAPL")
    assert markers == []


def test_entry_not_near_local_peak():
    """Shallow pullback from ATH must not paint WEJ on the top."""
    prices = [100.0] * 40 + [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.5]
    candles = _daily_candles(prices, start=date(2023, 1, 1))
    markers = compute_cycle_markers(
        candles,
        preset="3M",
        asset_class="stock",
        region="us",
        symbol="TEST",
    )
    buys = [m for m in markers if m.action == SignalAction.BUY]
    assert buys == []


def test_early_decline_is_short_ongoing_not_wej():
    """Mid-fall without bounce: no WEJ and no orphan SHORT noise."""
    prices = [100.0] * 40 + [100.0 - i for i in range(1, 30)]  # down to ~71, still falling
    candles = _daily_candles(prices, start=date(2023, 1, 1))
    markers = compute_cycle_markers(
        candles,
        preset="3M",
        asset_class="stock",
        region="us",
        symbol="TEST",
    )
    buys = [m for m in markers if m.action == SignalAction.BUY]
    watches = [m for m in markers if m.action == SignalAction.WATCH]
    assert buys == []
    assert watches == []


def test_entry_only_at_confirmed_bottom_after_bounce():
    """WEJ lands on the trough bar after bounce lock-in — not on first decline bars."""
    peak = [100.0] * 45
    crash = [100.0 - i * 1.2 for i in range(1, 36)]  # ~58 at bottom (~42% DD)
    trough = [58.0] * 2
    bounce = [58.0 + i * 1.0 for i in range(1, 12)]  # >2.5% bounce, ≥3 confirm bars
    prices = peak + crash + trough + bounce
    candles = _daily_candles(prices, start=date(2023, 1, 1))
    markers = compute_cycle_markers(
        candles,
        preset="3M",
        asset_class="stock",
        region="us",
        symbol="TEST",
    )
    buys = [m for m in markers if m.action == SignalAction.BUY]
    watches = [m for m in markers if m.action == SignalAction.WATCH]
    assert len(buys) >= 1
    series_low = min(c.low for c in candles)
    assert buys[0].price <= series_low * 1.05
    first_crash_ts = candles[45].time
    assert buys[0].time > first_crash_ts
    assert len(watches) >= 1
    assert watches[0].time < buys[0].time
    assert "short ongoing" in watches[0].rationale.lower()
    assert "potwierdzony dołek" in buys[0].rationale.lower() or "dołek" in buys[0].rationale.lower()

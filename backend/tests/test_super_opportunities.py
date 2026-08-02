from app.data.orderbook import estimate_liquidation_heatmap
from app.models.schemas import AssetClass, Opportunity, SignalAction
from app.scanners.super_opportunities import compute_entry_exit_levels, score_super_opportunity
from datetime import datetime, timezone


def test_liquidation_heatmap_sides():
    highs = [98 + i * 0.2 for i in range(24)]
    lows = [96 + i * 0.2 for i in range(24)]
    volumes = [10 + i for i in range(24)]
    hm = estimate_liquidation_heatmap(100.0, highs=highs, lows=lows, volumes=volumes)
    assert hm["range_low"] < 100 < hm["range_high"]
    assert len(hm["bins"]) == 40
    assert len(hm["columns"]) == 36
    assert len(hm["columns"][0]) == 40
    below = [b for b in hm["bins"] if b["price"] < 100]
    above = [b for b in hm["bins"] if b["price"] > 100]
    assert sum(b["long_intensity"] for b in below) > sum(b["long_intensity"] for b in above)
    assert sum(b["short_intensity"] for b in above) > sum(b["short_intensity"] for b in below)


def test_entry_exit_long_rr():
    hm = estimate_liquidation_heatmap(100.0)
    levels = compute_entry_exit_levels(100.0, SignalAction.BUY, 80, 99.9, 100.1, hm)
    assert levels["side"] == "long"
    assert levels["stop_loss"] < levels["entry"] < levels["take_profit_1"]
    assert levels["risk_reward"] > 0


def test_super_score_prefers_tight_spread():
    opp = Opportunity(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        action=SignalAction.BUY,
        confidence=70,
        cycle_source="alpha",
        phase="bear",
        price=100,
        rationale="test",
        created_at=datetime.now(timezone.utc),
    )
    hm = estimate_liquidation_heatmap(100.0)
    levels = compute_entry_exit_levels(100.0, SignalAction.BUY, 70, 99.98, 100.02, hm)
    tight, _ = score_super_opportunity(
        opp, {"bid": 99.98, "ask": 100.02, "mid": 100, "spread_pct": 0.04}, levels, hm
    )
    wide, _ = score_super_opportunity(
        opp, {"bid": 99.0, "ask": 101.0, "mid": 100, "spread_pct": 2.0}, levels, hm
    )
    assert tight > wide

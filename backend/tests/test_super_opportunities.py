from app.data.orderbook import estimate_liquidation_heatmap
from app.models.schemas import AssetClass, Opportunity, SignalAction
from app.scanners.ai_trade_advisor import consult_trade_signal
from app.scanners.liq_prediction import predict_liq_path
from app.scanners.super_opportunities import compute_entry_exit_levels, score_super_opportunity
from datetime import datetime, timezone


def test_liquidation_heatmap_sides():
    highs = [98 + i * 0.2 for i in range(24)]
    lows = [96 + i * 0.2 for i in range(24)]
    volumes = [10 + i for i in range(24)]
    hm = estimate_liquidation_heatmap(100.0, highs=highs, lows=lows, volumes=volumes)
    assert hm["range_low"] < 100 < hm["range_high"]
    assert len(hm["bins"]) == 48
    assert len(hm["columns"]) == 24
    assert len(hm["columns"][0]) == 48
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


def test_liq_prediction_builds_path_to_target():
    highs = [98 + i * 0.15 for i in range(30)]
    lows = [96 + i * 0.15 for i in range(30)]
    volumes = [8 + i for i in range(30)]
    hm = estimate_liquidation_heatmap(100.0, highs=highs, lows=lows, volumes=volumes)
    levels = compute_entry_exit_levels(100.0, SignalAction.BUY, 80, 99.9, 100.1, hm)
    pred = predict_liq_path(hm, levels, "buy")
    assert pred["direction"] in ("up", "down", "neutral")
    assert 0 < pred["confidence"] <= 98
    assert len(pred["path"]) >= 8
    assert pred["path"][0]["role"] == "entry"
    assert pred["path"][-1]["role"] == "liq_target"
    assert any(a["label"] == "LIQ" for a in pred["anchors"])
    assert any(a["label"] == "IN" for a in pred["anchors"])


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


def test_ai_advisor_kup_when_aligned_long():
    hm = estimate_liquidation_heatmap(100.0)
    levels = compute_entry_exit_levels(100.0, SignalAction.BUY, 85, 99.98, 100.02, hm)
    pred = predict_liq_path(hm, levels, "buy")
    # Force bullish prediction features into consultation via a long-biased prediction
    pred = {**pred, "direction": "up", "confidence": 80, "pull_up": 40, "pull_down": 10, "momentum": 0.4}
    verdict = consult_trade_signal(
        action="buy",
        cycle_confidence=85,
        cycle_source="alpha",
        phase="accumulation",
        super_score=80,
        levels=levels,
        spread_pct=0.04,
        prediction=pred,
    )
    assert verdict["signal"] == "kup"
    assert verdict["label"] == "KUP"
    assert verdict["buy_score"] > verdict["sell_score"]
    assert len(verdict["factors"]) >= 5


def test_ai_advisor_sprzedaj_when_aligned_short():
    hm = estimate_liquidation_heatmap(100.0)
    levels = compute_entry_exit_levels(100.0, SignalAction.SELL, 85, 99.9, 100.1, hm)
    pred = {
        "direction": "down",
        "confidence": 82,
        "pull_up": 8,
        "pull_down": 45,
        "momentum": -0.35,
        "target_price": 97.0,
        "summary": "test",
    }
    verdict = consult_trade_signal(
        action="sell",
        cycle_confidence=85,
        cycle_source="beta",
        phase="distribution",
        super_score=78,
        levels=levels,
        spread_pct=0.05,
        prediction=pred,
    )
    assert verdict["signal"] == "sprzedaj"
    assert verdict["label"] == "SPRZEDAJ"
    assert verdict["sell_score"] > verdict["buy_score"]


def test_ai_advisor_czekaj_on_conflict():
    hm = estimate_liquidation_heatmap(100.0)
    levels = compute_entry_exit_levels(100.0, SignalAction.BUY, 60, 99.9, 100.1, hm)
    pred = {
        "direction": "down",
        "confidence": 75,
        "pull_up": 5,
        "pull_down": 40,
        "momentum": -0.3,
        "target_price": 96.0,
        "summary": "test conflict",
    }
    verdict = consult_trade_signal(
        action="buy",
        cycle_confidence=55,
        cycle_source="alpha",
        phase="bear",
        super_score=52,
        levels=levels,
        spread_pct=0.5,
        prediction=pred,
    )
    assert verdict["signal"] == "czekaj"
    assert verdict["conflict"] is True

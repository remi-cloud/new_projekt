"""Unit tests for liquidation heatmap + whale classify (no network)."""

from app.data.orderbook import estimate_liquidation_heatmap
from app.data.whale_flows import classify_whale_bias
from app.scanners.liq_prediction import predict_liq_path


def test_heatmap_btc_nonempty():
    heat = estimate_liquidation_heatmap(
        65000.0,
        highs=[64000, 65000, 66000, 65500],
        lows=[63000, 64000, 64500, 64800],
        volumes=[100, 120, 90, 110],
        bins=24,
        time_cols=8,
    )
    assert heat["price"] == 65000.0
    assert len(heat["bins"]) == 24
    assert len(heat["columns"]) == 8
    assert heat["max_intensity"] == 1.0
    assert any(b["intensity"] > 0 for b in heat["bins"])


def test_whale_classify_accumulate():
    out = classify_whale_bias(
        {"net_usd": 500_000, "large_buys": 5, "large_sells": 1, "threshold_usd": 150_000},
        {"taker_buy_sell_ratio": 1.3, "accounts_long_short_ratio": 0.9, "source": "test"},
        None,
    )
    assert out["bias"] == "accumulate"
    assert out["side_hint"] == "long"
    assert out["strength"] > 0


def test_liq_prediction_path():
    heat = estimate_liquidation_heatmap(100.0, bins=20, time_cols=6)
    levels = {
        "side": "long",
        "entry": 100.0,
        "stop_loss": 97.0,
        "take_profit_1": 103.0,
        "take_profit_2": 106.0,
    }
    pred = predict_liq_path(heat, levels, "buy")
    assert pred["direction"] in ("up", "down", "neutral")
    assert len(pred["path"]) >= 2
    assert pred["anchors"]

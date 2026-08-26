"""Scoring weights: Superokazje R:R independence + Launch Scout tag cap + sizing bands."""

from app.execution.sizing import compute_amount_pln, confidence_size_mult, reward_risk_size_mult
from app.launch_scout.scorer import TAG_BONUS_CAP, _tag_bonus, data_confidence, score_candidate
from app.models.schemas import SignalAction
from app.scanners.super_opportunities import compute_entry_exit_levels


def test_entry_exit_levels_independent_of_confidence():
    heatmap = {
        "bins": [
            {"price": 95.0, "dominant": "long", "long_intensity": 0.7, "short_intensity": 0.1},
            {"price": 100.0, "dominant": "neutral", "long_intensity": 0.2, "short_intensity": 0.2},
            {"price": 108.0, "dominant": "short", "long_intensity": 0.1, "short_intensity": 0.7},
        ]
    }
    low = compute_entry_exit_levels(100.0, SignalAction.BUY, 40.0, 99.9, 100.1, heatmap)
    high = compute_entry_exit_levels(100.0, SignalAction.BUY, 95.0, 99.9, 100.1, heatmap)
    assert low["risk_reward"] == high["risk_reward"]
    assert low["stop_loss"] == high["stop_loss"]
    assert low["take_profit_1"] == high["take_profit_1"]


def test_launch_tag_bonus_capped():
    many = [
        "dex_paid",
        "migrated",
        "pump",
        "pump_trader",
        "fomo_bag",
        "elon_whisper",
        "value_watch",
        "4meme",
        "boost",
    ]
    assert _tag_bonus(many) == TAG_BONUS_CAP
    stacked = score_candidate(market_cap=500, age_h=1, liq_usd=2000, tags=many)
    base = score_candidate(market_cap=500, age_h=1, liq_usd=2000, tags=["pump"])
    assert stacked > base
    # Cap prevents unbounded explosion vs uncapped sum (~130+)
    assert stacked - base < 120


def test_launch_data_confidence():
    c = data_confidence(
        mint="abc",
        market_cap=1000,
        age_h=2,
        liq_usd=5000,
        tags=["pump", "dex_paid"],
    )
    assert 70 <= c <= 100
    empty = data_confidence(mint=None, market_cap=None, age_h=None, liq_usd=None, tags=[])
    assert empty == 20.0


def test_sizing_confidence_bands():
    assert confidence_size_mult(70) == 0.5
    assert confidence_size_mult(80) == 1.0
    assert confidence_size_mult(90) == 1.25
    assert compute_amount_pln(10_000, confidence=70) == 5_000
    assert compute_amount_pln(10_000, confidence=90) == 12_500
    assert compute_amount_pln(10_000, confidence=90) > compute_amount_pln(10_000, confidence=72)


def test_sizing_rr_gate():
    assert reward_risk_size_mult(0.8) is None
    assert reward_risk_size_mult(1.2) == 0.5
    assert reward_risk_size_mult(2.0) == 1.0
    assert compute_amount_pln(10_000, confidence=90, reward_risk=0.5) == 0.0
    assert compute_amount_pln(10_000, confidence=80, reward_risk=1.2) == 5_000

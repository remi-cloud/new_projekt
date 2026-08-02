"""Whale / large-player flow classification + scout integration."""

from datetime import datetime, timezone

from app.agents.scouts import ScoutAgent
from app.agents.types import ScoutUniverse
from app.data.whale_flows import classify_whale_bias
from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    CyclePhase,
    SignalAction,
)


def test_classify_accumulate_from_net_buys_and_taker():
    prints = {
        "large_buys": 8,
        "large_sells": 1,
        "buy_usd": 2_500_000,
        "sell_usd": 200_000,
        "net_usd": 2_300_000,
        "largest_usd": 600_000,
        "threshold_usd": 250_000,
    }
    futures = {"taker_buy_sell_ratio": 1.4, "accounts_long_short_ratio": 0.9}
    out = classify_whale_bias(prints, futures, None)
    assert out["bias"] == "accumulate"
    assert out["side_hint"] == "long"
    assert out["strength"] >= 40
    assert any("BUY" in f or "akumul" in f.lower() or "WEJŚCIE" in out["summary"] for f in out["factors"]) or "WEJŚCIE" in out["summary"]


def test_classify_distribute_from_net_sells():
    prints = {
        "large_buys": 1,
        "large_sells": 9,
        "buy_usd": 150_000,
        "sell_usd": 2_800_000,
        "net_usd": -2_650_000,
        "largest_usd": 700_000,
        "threshold_usd": 250_000,
    }
    futures = {"taker_buy_sell_ratio": 0.7, "accounts_long_short_ratio": 1.5}
    out = classify_whale_bias(prints, futures, {"ok": True, "large_txs": 4, "total_btc": 40, "threshold_btc": 2.5})
    assert out["bias"] == "distribute"
    assert out["side_hint"] == "short"
    assert "WYJŚCIE" in out["summary"]


def test_scout_whale_opens_short_on_distribute():
    alpha = AlphaModelStatus(
        reference_date="2024-01-01",
        reference_price=100_000,
        current_price=80_000,
        days_since_reference=200,
        phase=CyclePhase.BEAR,
        phase_progress_pct=40.0,
        days_remaining_in_phase=100,
        signal=SignalAction.WATCH,
        rationale="mid bear watch",
    )
    quote = AssetQuote(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        price=80_000,
        change_pct_7d=-1.0,
        change_pct_24h=0.2,
        updated_at=datetime.now(timezone.utc),
    )
    whale = {
        "bias": "distribute",
        "strength": 72,
        "summary": "Wielcy gracze: WYJŚCIE / dystrybucja (siła 72)",
        "factors": ["Whale printy CEX: net SELL"],
    }
    scout = ScoutAgent(
        "short",
        "crypto",
        ScoutUniverse(region="crypto", asset_classes=(AssetClass.CRYPTO,), symbols=("BTC-USD",)),
    )
    # Mid-bear WATCH without dump normally returns None for short — whale should open it
    finding = scout._score_crypto(quote, alpha, -1.0, 0.2, [], whale=whale)
    assert finding is not None
    assert finding.side == "short"
    assert finding.confidence >= 48
    assert any("Whale" in (f.get("name") or "") for f in finding.factors)


def test_scout_whale_boosts_long_on_accumulate():
    alpha = AlphaModelStatus(
        reference_date="2024-01-01",
        reference_price=100_000,
        current_price=90_000,
        days_since_reference=400,
        phase=CyclePhase.BEAR,
        phase_progress_pct=70.0,
        days_remaining_in_phase=50,
        signal=SignalAction.WATCH,
        rationale="late bear",
    )
    quote = AssetQuote(
        symbol="ETH-USD",
        name="Ethereum",
        asset_class=AssetClass.CRYPTO,
        price=3000,
        change_pct_7d=-2.0,
        change_pct_24h=-0.5,
        updated_at=datetime.now(timezone.utc),
    )
    whale = {
        "bias": "accumulate",
        "strength": 65,
        "summary": "Wielcy gracze: WEJŚCIE / akumulacja (siła 65)",
        "factors": ["net BUY"],
    }
    scout = ScoutAgent(
        "long",
        "crypto",
        ScoutUniverse(region="crypto", asset_classes=(AssetClass.CRYPTO,), symbols=("ETH-USD",)),
    )
    base = scout._score_crypto(quote, alpha, -2.0, -0.5, [], whale=None)
    boosted = scout._score_crypto(quote, alpha, -2.0, -0.5, [], whale=whale)
    assert base is not None and boosted is not None
    assert boosted.confidence >= base.confidence

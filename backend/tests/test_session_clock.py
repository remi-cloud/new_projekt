"""Session Clock unit tests."""

from __future__ import annotations

from app.cycles.session_clock import (
    build_meme_hour_heatmap,
    log_return,
    session_boost_for_timestamp,
    session_for_utc_hour,
    sessions_active_at_hour,
)


def test_session_for_utc_hour_map():
    assert session_for_utc_hour(3) == "asia"
    assert session_for_utc_hour(10) == "europe"
    assert session_for_utc_hour(14) == "overlap_eu_us"
    assert session_for_utc_hour(18) == "us"
    assert session_for_utc_hour(23) == "off"


def test_sessions_active_overlap():
    active = sessions_active_at_hour(14)
    assert "overlap_eu_us" in active
    assert "europe" in active
    assert "us" in active


def test_log_return():
    assert log_return(100.0, 110.0) is not None
    assert log_return(100.0, 100.0) == 0.0
    assert log_return(0, 1) is None


def test_meme_heatmap_and_boost():
    # 2024-01-01 14:00 UTC
    ts = 1704117600
    heat = build_meme_hour_heatmap(
        [
            {"ts_unix": ts, "action": "buy", "usd_amount": 50},
            {"ts_unix": ts, "action": "sell", "usd_amount": 10},
        ],
        candidates=[{"pair_created_ms": ts * 1000}],
    )
    assert heat["hours"][14]["buys"] == 1
    assert heat["hours"][14]["creates"] == 1
    boost, tags = session_boost_for_timestamp(
        ts, hottest_session="overlap_eu_us", macro_strongest="us"
    )
    assert boost > 0
    assert "session_us" in tags or "session_eu" in tags

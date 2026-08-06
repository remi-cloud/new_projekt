"""Telemetry: real EW returns helper + portfolio series shape."""

from app.telemetry.agent_vs_spx import _ew_return_nav


def test_ew_return_nav_chains_percent_changes():
    nav1, prices1 = _ew_return_nav({"A": 100.0, "B": 50.0}, prev_prices=None, prev_nav=100.0)
    assert nav1 == 100.0
    nav2, _ = _ew_return_nav(
        {"A": 110.0, "B": 55.0},
        prev_prices=prices1,
        prev_nav=nav1,
    )
    # Both +10% → NAV 110
    assert abs(nav2 - 110.0) < 1e-9


def test_ew_return_nav_ignores_new_names_until_next_tick():
    prev = {"A": 100.0}
    nav, prices = _ew_return_nav(
        {"A": 100.0, "B": 200.0},
        prev_prices=prev,
        prev_nav=100.0,
    )
    # Only A overlaps with 0% change
    assert abs(nav - 100.0) < 1e-9
    assert "B" in prices

"""Seasonality monitor drift / overlay scale."""

from app.cycles.seasonality_monitor import get_overlay_scale, run_seasonality_monitor


def test_seasonality_monitor_runs():
    health = run_seasonality_monitor(persist=True)
    assert "overlay_scale" in health
    assert health["overlay_scale"] in (0.5, 1.0)
    assert get_overlay_scale() == health["overlay_scale"]

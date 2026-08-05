"""Intra-month (day/week) seasonality."""

from app.cycles.intramonth_seasonality import get_intramonth


def test_us_august_has_weeks_and_days():
    data = get_intramonth("us", 8)
    assert data["month"] == 8
    assert len(data["days"]) == 31
    assert len(data["weeks"]) == 4
    assert any(w["avg_return_pct"] is not None for w in data["weeks"])


def test_btc_intramonth():
    data = get_intramonth("btc", 1)
    assert data["universe"] == "btc"
    assert len(data["days"]) == 31

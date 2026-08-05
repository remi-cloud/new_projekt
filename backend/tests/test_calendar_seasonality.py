"""Calendar seasonality / month pumps helpers."""

from __future__ import annotations

from app.cycles.calendar_seasonality import (
    get_instrument_calendar,
    get_month_pumps,
    month_pump_snippet,
    search_catalog,
)


def test_month_pumps_shape():
    data = get_month_pumps(11, limit=10)
    assert data["month"] == 11
    assert "pumped" in data
    assert "drained" in data
    assert isinstance(data["pumped"], list)


def test_month_snippet():
    snip = month_pump_snippet(1, top_n=3)
    assert snip["month"] == 1
    assert "text" in snip


def test_instrument_calendar_fallback_or_data():
    # May be empty before compute; helper must not crash
    data = get_instrument_calendar("AAPL")
    assert data["symbol"]
    assert len(data["months"]) == 12


def test_search_catalog():
    hits = search_catalog("aapl", limit=5)
    assert isinstance(hits, list)

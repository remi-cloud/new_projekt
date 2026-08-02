from datetime import datetime, timezone

from app.data.economic_calendar import normalize_event, pick_headline_events
from app.scanners.broadcast import ticker_window


def test_normalize_high_impact_event():
    raw = {
        "title": "CPI m/m",
        "country": "USD",
        "date": "2026-08-02T08:30:00-04:00",
        "impact": "High",
        "forecast": "0.2%",
        "previous": "0.1%",
    }
    e = normalize_event(raw)
    assert e is not None
    assert e["impact_rank"] == 3
    assert e["country"] == "USD"
    assert "CPI" in e["title"]


def test_ticker_window_math():
    # Align to start of a 20-min cycle: epoch minutes % 20 == 0
    base = datetime(2026, 8, 2, 12, 0, 5, tzinfo=timezone.utc)
    epoch_min = int(base.timestamp() // 60)
    adjust = epoch_min % 20
    ts = base.timestamp() - adjust * 60
    now = datetime.fromtimestamp(ts, tz=timezone.utc)
    w = ticker_window(now)
    assert w["visible"] is True  # always-on live tape
    assert w["breaking"] is True
    assert w["seconds_remaining"] > 0

    # 3 minutes into cycle → still visible, not breaking
    later = datetime.fromtimestamp(ts + 3 * 60, tz=timezone.utc)
    w2 = ticker_window(later)
    assert w2["visible"] is True
    assert w2["breaking"] is False
    assert w2["next_show_in_seconds"] > 0


def test_pick_headline_prefers_high_impact():
    now = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    events = [
        {
            "event_id": "1",
            "title": "Low thing",
            "country": "USD",
            "impact": "Low",
            "impact_rank": 1,
            "event_at": now.isoformat(),
            "forecast": "",
            "previous": "",
            "actual": "",
            "source": "t",
        },
        {
            "event_id": "2",
            "title": "NFP",
            "country": "USD",
            "impact": "High",
            "impact_rank": 3,
            "event_at": now.isoformat(),
            "forecast": "180K",
            "previous": "170K",
            "actual": "",
            "source": "t",
        },
    ]
    top = pick_headline_events(events, now=now, limit=1)
    assert top and top[0]["title"] == "NFP"

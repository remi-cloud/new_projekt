from datetime import date, datetime, timezone

from app.models.schemas import MacroCalendarEvent
from app.news.calendar_ai import _heuristic, _parse_ai_json


def _ev(kind: str = "cpi") -> MacroCalendarEvent:
    return MacroCalendarEvent(
        id="cal-test",
        title="CPI USA",
        event_date=date(2026, 8, 12),
        days_until=9,
        category="usa",
        kind=kind,
        time_utc="13:30",
        region="US",
    )


def test_heuristic_fills_state_and_expectations():
    out = _heuristic(_ev("fomc"), "pl")
    assert out.current_state
    assert out.expectations
    assert out.ai_source == "heuristic"
    assert out.ai_bias
    assert out.ai_assessed_at is not None


def test_parse_ai_json_fenced():
    raw = """```json
{"current_state": "A", "expectations": "B", "bias": "hawkish", "confidence": 70}
```"""
    data = _parse_ai_json(raw)
    assert data is not None
    assert data["bias"] == "hawkish"
    assert data["confidence"] == 70

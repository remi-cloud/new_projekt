"""Upcoming macro calendar — FOMC, CPI, NFP (official / estimated dates)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.models.schemas import MacroCalendarEvent
from app.news.calendar_i18n import event_title, normalize_locale

FOMC_DATES = [
    date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7), date(2025, 6, 18),
    date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
    date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
]

CPI_DATES = [
    (date(2025, 7, 15), 6, 2025), (date(2025, 8, 12), 7, 2025), (date(2025, 9, 11), 8, 2025),
    (date(2025, 10, 15), 9, 2025), (date(2025, 11, 13), 10, 2025), (date(2025, 12, 10), 11, 2025),
    (date(2026, 1, 14), 12, 2025), (date(2026, 2, 12), 1, 2026), (date(2026, 3, 11), 2, 2026),
    (date(2026, 4, 10), 3, 2026), (date(2026, 5, 13), 4, 2026), (date(2026, 6, 10), 5, 2026),
    (date(2026, 7, 14), 6, 2026), (date(2026, 8, 12), 7, 2026), (date(2026, 9, 11), 8, 2026),
    (date(2026, 10, 14), 9, 2026), (date(2026, 11, 12), 10, 2026), (date(2026, 12, 10), 11, 2026),
]

ECB_DATES = [
    date(2025, 7, 24), date(2025, 9, 11), date(2025, 10, 30), date(2025, 12, 18),
    date(2026, 2, 5), date(2026, 3, 19), date(2026, 4, 23), date(2026, 6, 11),
    date(2026, 7, 23), date(2026, 9, 10), date(2026, 10, 22), date(2026, 12, 17),
]

BOE_DATES = [
    date(2025, 8, 7), date(2025, 9, 18), date(2025, 11, 6), date(2025, 12, 18),
    date(2026, 2, 5), date(2026, 3, 19), date(2026, 5, 7), date(2026, 6, 18),
    date(2026, 8, 6), date(2026, 9, 17), date(2026, 11, 5), date(2026, 12, 17),
]

BOJ_DATES = [
    date(2025, 7, 31), date(2025, 9, 19), date(2025, 10, 30), date(2025, 12, 19),
    date(2026, 1, 24), date(2026, 3, 19), date(2026, 4, 28), date(2026, 6, 16),
    date(2026, 7, 31), date(2026, 9, 18), date(2026, 10, 29), date(2026, 12, 18),
]

GLOBAL_EVENTS: list[tuple[date, str]] = [
    (date(2025, 7, 15), "opec"),
    (date(2025, 9, 5), "g7_finance"),
    (date(2025, 11, 30), "opec"),
    (date(2026, 1, 20), "davos"),
    (date(2026, 3, 5), "opec"),
    (date(2026, 6, 15), "g7_summit"),
    (date(2026, 7, 14), "china_gdp"),
    (date(2026, 9, 1), "opec"),
    (date(2026, 11, 15), "g20_summit"),
    (date(2026, 12, 1), "opec"),
]


@dataclass(frozen=True)
class CalendarSpec:
    event_date: date
    kind: str
    period_month: int | None = None
    period_year: int | None = None


def _first_fridays(year: int, months: range) -> list[CalendarSpec]:
    out: list[CalendarSpec] = []
    for month in months:
        d = date(year, month, 1)
        while d.weekday() != 4:
            d += timedelta(days=1)
        out.append(CalendarSpec(d, "nfp", d.month, d.year))
    return out


def _all_specs() -> list[CalendarSpec]:
    specs: list[CalendarSpec] = []
    specs.extend(CalendarSpec(d, "fomc", d.month, d.year) for d in FOMC_DATES)
    specs.extend(CalendarSpec(d, "cpi", pm, py) for d, pm, py in CPI_DATES)
    specs.extend(_first_fridays(2025, range(1, 13)))
    specs.extend(_first_fridays(2026, range(1, 13)))
    specs.extend(CalendarSpec(d, "ecb", d.month, d.year) for d in ECB_DATES)
    specs.extend(CalendarSpec(d, "boe", d.month, d.year) for d in BOE_DATES)
    specs.extend(CalendarSpec(d, "boj", d.month, d.year) for d in BOJ_DATES)
    specs.extend(CalendarSpec(d, kind) for d, kind in GLOBAL_EVENTS)
    specs.sort(key=lambda s: s.event_date)
    return specs


ALL_SPECS = _all_specs()


def _event_category(kind: str) -> str:
    if kind == "fomc":
        return "fed"
    if kind in ("cpi", "nfp", "ecb", "boe", "boj"):
        return "macro"
    return "global"


def _event_region(kind: str) -> str:
    if kind == "ecb":
        return "EU"
    if kind == "boe":
        return "UK"
    if kind == "boj" or kind == "china_gdp":
        return "APAC"
    if kind in ("opec", "g7_finance", "g7_summit", "g20_summit", "davos"):
        return "GLOBAL"
    return "US"


def _event_time(kind: str) -> str:
    if kind in ("cpi", "nfp"):
        return "13:30"
    if kind == "boj":
        return "03:00"
    if kind == "boe":
        return "12:00"
    if kind == "ecb":
        return "13:15"
    if kind == "fomc":
        return "19:00"
    return "12:00"


def _localized_title(spec: CalendarSpec, locale: str | None) -> str:
    if spec.period_month and spec.period_year:
        return event_title(locale, spec.kind, spec.period_month, spec.period_year)
    return event_title(locale, spec.kind)


def _build_event(idx: int, spec: CalendarSpec, as_of: date, locale: str | None) -> MacroCalendarEvent:
    title = _localized_title(spec, locale)
    return MacroCalendarEvent(
        id=f"cal-{spec.event_date.isoformat()}-{idx}",
        title=title,
        event_date=spec.event_date,
        days_until=(spec.event_date - as_of).days,
        category=_event_category(spec.kind),
        impact="high",
        time_utc=_event_time(spec.kind),
        region=_event_region(spec.kind),
    )


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def get_calendar_month(year: int, month: int, as_of: date | None = None, locale: str | None = "pl") -> list[MacroCalendarEvent]:
    loc = normalize_locale(locale)
    as_of = as_of or datetime.now(timezone.utc).date()
    start, end = _month_bounds(year, month)
    events: list[MacroCalendarEvent] = []

    for idx, spec in enumerate(ALL_SPECS):
        if start <= spec.event_date <= end:
            events.append(_build_event(idx, spec, as_of, loc))

    events.sort(key=lambda e: (e.event_date, e.time_utc))
    return events


def get_upcoming_calendar(as_of: date | None = None, days_ahead: int = 120, locale: str | None = "pl") -> list[MacroCalendarEvent]:
    loc = normalize_locale(locale)
    as_of = as_of or datetime.now(timezone.utc).date()
    horizon = as_of + timedelta(days=days_ahead)
    events: list[MacroCalendarEvent] = []

    for idx, spec in enumerate(ALL_SPECS):
        if spec.event_date < as_of or spec.event_date > horizon:
            continue
        events.append(_build_event(idx, spec, as_of, loc))

    events.sort(key=lambda e: e.event_date)
    return events[:48]

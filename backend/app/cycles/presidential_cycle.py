from datetime import date, datetime, timezone

from app.config import settings
from app.models.schemas import (
    PresidentialCycleStatus,
    PresidentialYear,
    PresidentialYearReturn,
    SignalAction,
)

# S&P 500 — średnie roczne zwroty wg lat cyklu prezydenckiego (Stock Trader's Almanac, od 1949)
HISTORICAL_ANNUAL_RETURNS: dict[PresidentialYear, float] = {
    PresidentialYear.YEAR_1: 7.1,
    PresidentialYear.YEAR_2: 3.9,
    PresidentialYear.YEAR_3: 16.0,
    PresidentialYear.YEAR_4: 6.8,
}

CYCLE_AVG_RETURN_PCT = round(
    sum(HISTORICAL_ANNUAL_RETURNS.values()) / len(HISTORICAL_ANNUAL_RETURNS),
    1,
)

# Historical presidential cycle tendencies (Stock Trader's Almanac pattern)
YEAR_PROFILES = {
    PresidentialYear.YEAR_1: {
        "label": "Rok 1 (po wyborach)",
        "short_label": "Rok 1",
        "bias": "Słabszy — adaptacja polityki, często korekty",
        "signal": SignalAction.WATCH,
        "buy_weight": 0.3,
        "tone": "moderate",
    },
    PresidentialYear.YEAR_2: {
        "label": "Rok 2 (midterms)",
        "short_label": "Rok 2",
        "bias": "Najsłabszy historycznie — lata wyborów do Kongresu",
        "signal": SignalAction.BUY,
        "buy_weight": 0.7,
        "tone": "weak",
    },
    PresidentialYear.YEAR_3: {
        "label": "Rok 3 (pre-election)",
        "short_label": "Rok 3",
        "bias": "Najsilniejszy — historycznie najlepszy rok cyklu",
        "signal": SignalAction.BUY,
        "buy_weight": 1.0,
        "tone": "best",
    },
    PresidentialYear.YEAR_4: {
        "label": "Rok 4 (wybory)",
        "short_label": "Rok 4",
        "bias": "Umiarkowanie pozytywny — polityka wspierająca gospodarkę",
        "signal": SignalAction.HOLD,
        "buy_weight": 0.5,
        "tone": "moderate",
    },
}

YEAR_ORDER = (
    PresidentialYear.YEAR_1,
    PresidentialYear.YEAR_2,
    PresidentialYear.YEAR_3,
    PresidentialYear.YEAR_4,
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _find_current_term(as_of: date) -> dict:
    for term in settings.presidential_terms:
        start = _parse_date(term["start"])
        end = _parse_date(term["end"])
        if start <= as_of < end:
            return {**term, "start_date": start, "end_date": end}
    last = settings.presidential_terms[-1]
    return {
        **last,
        "start_date": _parse_date(last["start"]),
        "end_date": _parse_date(last["end"]),
    }


def _year_of_term(term_start: date, as_of: date) -> tuple[PresidentialYear, int]:
    years_elapsed = as_of.year - term_start.year
    if (as_of.month, as_of.day) < (term_start.month, term_start.day):
        years_elapsed -= 1
    year_number = min(max(years_elapsed + 1, 1), 4)
    mapping = {
        1: PresidentialYear.YEAR_1,
        2: PresidentialYear.YEAR_2,
        3: PresidentialYear.YEAR_3,
        4: PresidentialYear.YEAR_4,
    }
    return mapping[year_number], year_number


def _year_boundaries(term_start: date, year_number: int) -> tuple[date, date]:
    year_start = date(term_start.year + year_number - 1, term_start.month, term_start.day)
    year_end = date(term_start.year + year_number, term_start.month, term_start.day)
    return year_start, year_end


def _build_year_returns(current_year: PresidentialYear) -> list[PresidentialYearReturn]:
    returns: list[PresidentialYearReturn] = []
    for idx, year in enumerate(YEAR_ORDER, start=1):
        profile = YEAR_PROFILES[year]
        avg_return = HISTORICAL_ANNUAL_RETURNS[year]
        returns.append(
            PresidentialYearReturn(
                year=year,
                year_number=idx,
                label=profile["short_label"],
                avg_return_pct=avg_return,
                vs_cycle_avg_pct=round(avg_return - CYCLE_AVG_RETURN_PCT, 1),
                bias=profile["bias"].split("—")[0].strip(),
                tone=profile["tone"],
                is_current=year == current_year,
            )
        )
    return returns


def analyze_presidential_cycle(as_of: date | None = None) -> PresidentialCycleStatus:
    as_of = as_of or datetime.now(timezone.utc).date()
    term = _find_current_term(as_of)
    presidential_year, year_number = _year_of_term(term["start_date"], as_of)
    year_start, year_end = _year_boundaries(term["start_date"], year_number)

    days_into = (as_of - year_start).days
    total_days = (year_end - year_start).days
    progress = min(100.0, (days_into / total_days) * 100) if total_days else 0
    days_remaining = max(0, (year_end - as_of).days)

    profile = YEAR_PROFILES[presidential_year]
    expected_return = HISTORICAL_ANNUAL_RETURNS[presidential_year]

    signal = profile["signal"]
    if presidential_year == PresidentialYear.YEAR_2 and progress > 60:
        signal = SignalAction.BUY
    elif presidential_year == PresidentialYear.YEAR_1 and progress > 70:
        signal = SignalAction.BUY
    elif presidential_year == PresidentialYear.YEAR_4 and progress > 75:
        signal = SignalAction.WATCH

    rationale = (
        f"{profile['label']} kadencji {term['president']}. "
        f"{profile['bias']}. "
        f"Historycznie S&P 500: +{expected_return:.1f}%/rok. "
        f"Dzień {days_into}/{total_days} roku ({progress:.0f}%)."
    )

    return PresidentialCycleStatus(
        term_start=term["start_date"],
        term_end=term["end_date"],
        president=term["president"],
        current_year=presidential_year,
        year_number=year_number,
        days_into_year=days_into,
        days_remaining_in_year=days_remaining,
        year_progress_pct=round(progress, 1),
        historical_bias=profile["bias"],
        signal=signal,
        rationale=rationale,
        cycle_avg_return_pct=CYCLE_AVG_RETURN_PCT,
        year_returns=_build_year_returns(presidential_year),
        current_year_expected_return_pct=expected_return,
    )


def presidential_buy_weight(as_of: date | None = None) -> float:
    status = analyze_presidential_cycle(as_of)
    return YEAR_PROFILES[status.current_year]["buy_weight"]

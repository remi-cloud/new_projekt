from datetime import date, datetime, timezone

from app.config import settings
from app.cycles.presidential_seasonality import (
    MONTH_NAMES_PL,
    SEASONALITY_UNIVERSE_SIZE,
    US_UNIVERSE_MONTHLY_RETURNS,
    adjust_signal_for_seasonality,
    calendar_season,
    compute_buy_weight,
    month_bias,
    universe_month_avg,
)
from app.models.schemas import (
    PresidentialCycleStatus,
    PresidentialMonthReturn,
    PresidentialNextTermOutlook,
    PresidentialYear,
    PresidentialYearMonthRow,
    PresidentialYearReturn,
    SignalAction,
)

# S&P 500 — średnie roczne zwroty wg lat cyklu (Stock Trader's Almanac, od 1949)
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

YEAR_TO_NUM = {
    PresidentialYear.YEAR_1: 1,
    PresidentialYear.YEAR_2: 2,
    PresidentialYear.YEAR_3: 3,
    PresidentialYear.YEAR_4: 4,
}


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


def _build_month_returns(
    current_year: PresidentialYear, current_month: int
) -> list[PresidentialMonthReturn]:
    y = YEAR_TO_NUM[current_year]
    row = US_UNIVERSE_MONTHLY_RETURNS.get(y, {})
    out: list[PresidentialMonthReturn] = []
    for m in range(1, 13):
        avg = float(row.get(m, 0.0))
        out.append(
            PresidentialMonthReturn(
                month=m,
                avg_return_pct=avg,
                bias=month_bias(avg),
                is_current=m == current_month,
            )
        )
    return out


def _months_for_year(
    year: PresidentialYear,
    *,
    highlight_month: int | None = None,
) -> list[PresidentialMonthReturn]:
    y = YEAR_TO_NUM[year]
    row = US_UNIVERSE_MONTHLY_RETURNS.get(y, {})
    out: list[PresidentialMonthReturn] = []
    for m in range(1, 13):
        avg = float(row.get(m, 0.0))
        out.append(
            PresidentialMonthReturn(
                month=m,
                avg_return_pct=avg,
                bias=month_bias(avg),
                is_current=highlight_month == m,
            )
        )
    return out


def _calendar_year_for_term_year(term_start: date, year_number: int) -> int:
    """Inauguration year + (year_number - 1); e.g. Trump II 2025 → Y2 = 2026."""
    return term_start.year + year_number - 1


def _build_month_matrices(
    term_start: date,
    current_year: PresidentialYear,
    current_month: int,
) -> list[PresidentialYearMonthRow]:
    rows: list[PresidentialYearMonthRow] = []
    for year in YEAR_ORDER:
        ynum = YEAR_TO_NUM[year]
        profile = YEAR_PROFILES[year]
        highlight = current_month if year == current_year else None
        rows.append(
            PresidentialYearMonthRow(
                year=year,
                year_number=ynum,
                label=profile["short_label"],
                calendar_year=_calendar_year_for_term_year(term_start, ynum),
                is_current=year == current_year,
                months=_months_for_year(year, highlight_month=highlight),
            )
        )
    return rows


def _build_next_term_outlook(current_term_end: date) -> PresidentialNextTermOutlook:
    """Project the same historical Y1–Y4 monthly pattern onto the next 4-year term."""
    next_start = current_term_end
    next_end = date(next_start.year + 4, next_start.month, next_start.day)
    year_rows: list[PresidentialYearMonthRow] = []
    for year in YEAR_ORDER:
        ynum = YEAR_TO_NUM[year]
        profile = YEAR_PROFILES[year]
        year_rows.append(
            PresidentialYearMonthRow(
                year=year,
                year_number=ynum,
                label=profile["short_label"],
                calendar_year=_calendar_year_for_term_year(next_start, ynum),
                is_current=False,
                months=_months_for_year(year, highlight_month=None),
            )
        )
    return PresidentialNextTermOutlook(
        term_start=next_start,
        term_end=next_end,
        label=f"Po obecnej kadencji ({next_start.isoformat()} – {next_end.isoformat()})",
        note=(
            "Historyczny wzorzec sezonowości USA (equal-weight) nałożony na następną "
            "4-letnią kadencję po Trump II. Nie przewiduje zwycięzcy wyborów 2028 — "
            "pokazuje czego spodziewać się w Y1–Y4 niezależnie od prezydenta."
        ),
        year_rows=year_rows,
    )


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

    month_avg = universe_month_avg(presidential_year, as_of.month)
    season = calendar_season(as_of.month)
    m_bias = month_bias(month_avg)
    signal = adjust_signal_for_seasonality(profile["signal"], month_avg, season)
    buy_w = compute_buy_weight(float(profile["buy_weight"]), month_avg, season)

    season_pl = "sezon XI–IV (best six)" if season == "best_six" else "poza sezonem V–X"
    rationale = (
        f"{profile['label']} kadencji {term['president']}. "
        f"{profile['bias']}. "
        f"Historycznie S&P 500: +{expected_return:.1f}%/rok. "
        f"{MONTH_NAMES_PL[as_of.month]} (Y{year_number}) agregat USA "
        f"({SEASONALITY_UNIVERSE_SIZE} tickerów): {month_avg:+.1f}% ({m_bias}). "
        f"{season_pl}. Waga wejścia {buy_w:.2f}. "
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
        benchmark="US universe (equal-weight)",
        benchmark_note=(
            f"Średnie miesięczne equal-weight po {SEASONALITY_UNIVERSE_SIZE} "
            "pozycjach region=us (1985+, Yahoo); lata 1–4: Almanac S&P roczne"
        ),
        cycle_avg_return_pct=CYCLE_AVG_RETURN_PCT,
        year_returns=_build_year_returns(presidential_year),
        current_year_expected_return_pct=expected_return,
        month_returns=_build_month_returns(presidential_year, as_of.month),
        month_matrices=_build_month_matrices(
            term["start_date"], presidential_year, as_of.month
        ),
        current_month_avg_return_pct=round(month_avg, 2),
        current_month_bias=m_bias,
        calendar_season=season,
        seasonality_universe_size=SEASONALITY_UNIVERSE_SIZE,
        buy_weight=buy_w,
        next_term_outlook=_build_next_term_outlook(term["end_date"]),
    )


def presidential_buy_weight(as_of: date | None = None) -> float:
    status = analyze_presidential_cycle(as_of)
    if status.buy_weight is not None:
        return float(status.buy_weight)
    profile = YEAR_PROFILES[status.current_year]
    month_avg = universe_month_avg(status.current_year, (as_of or date.today()).month)
    season = calendar_season((as_of or date.today()).month)
    return compute_buy_weight(float(profile["buy_weight"]), month_avg, season)

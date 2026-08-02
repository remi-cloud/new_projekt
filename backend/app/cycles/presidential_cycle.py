from datetime import date, datetime, timezone

from app.config import settings
from app.models.schemas import (
    BetaModelStatus,
    BetaPhase,
    SignalAction,
)

PHASE_PROFILES = {
    BetaPhase.PHASE_1: {
        "label": "Faza 1",
        "bias": "Słabszy historycznie — częstsze korekty",
        "signal": SignalAction.WATCH,
        "buy_weight": 0.3,
    },
    BetaPhase.PHASE_2: {
        "label": "Faza 2",
        "bias": "Najsłabszy historycznie — preferuj dołki",
        "signal": SignalAction.BUY,
        "buy_weight": 0.7,
    },
    BetaPhase.PHASE_3: {
        "label": "Faza 3",
        "bias": "Najsilniejszy historycznie",
        "signal": SignalAction.BUY,
        "buy_weight": 1.0,
    },
    BetaPhase.PHASE_4: {
        "label": "Faza 4",
        "bias": "Umiarkowanie pozytywny",
        "signal": SignalAction.HOLD,
        "buy_weight": 0.5,
    },
}


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _find_current_period(as_of: date) -> dict:
    for period in settings.beta_periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= as_of < end:
            return {**period, "start_date": start, "end_date": end}
    last = settings.beta_periods[-1]
    return {
        **last,
        "start_date": _parse_date(last["start"]),
        "end_date": _parse_date(last["end"]),
    }


def _phase_of_period(period_start: date, as_of: date) -> tuple[BetaPhase, int]:
    years_elapsed = as_of.year - period_start.year
    if (as_of.month, as_of.day) < (period_start.month, period_start.day):
        years_elapsed -= 1
    phase_number = min(max(years_elapsed + 1, 1), 4)
    mapping = {
        1: BetaPhase.PHASE_1,
        2: BetaPhase.PHASE_2,
        3: BetaPhase.PHASE_3,
        4: BetaPhase.PHASE_4,
    }
    return mapping[phase_number], phase_number


def _phase_boundaries(period_start: date, phase_number: int) -> tuple[date, date]:
    phase_start = date(
        period_start.year + phase_number - 1, period_start.month, period_start.day
    )
    phase_end = date(
        period_start.year + phase_number, period_start.month, period_start.day
    )
    return phase_start, phase_end


def analyze_presidential_cycle(as_of: date | None = None) -> BetaModelStatus:
    """Internal engine for Model Beta. Public output uses neutral field names."""
    as_of = as_of or datetime.now(timezone.utc).date()
    period = _find_current_period(as_of)
    beta_phase, phase_number = _phase_of_period(period["start_date"], as_of)
    phase_start, phase_end = _phase_boundaries(period["start_date"], phase_number)

    days_into = (as_of - phase_start).days
    total_days = (phase_end - phase_start).days
    progress = min(100.0, (days_into / total_days) * 100) if total_days else 0
    days_remaining = max(0, (phase_end - as_of).days)

    profile = PHASE_PROFILES[beta_phase]

    signal = profile["signal"]
    if beta_phase == BetaPhase.PHASE_2 and progress > 60:
        signal = SignalAction.BUY
    elif beta_phase == BetaPhase.PHASE_1 and progress > 70:
        signal = SignalAction.BUY
    elif beta_phase == BetaPhase.PHASE_4 and progress > 75:
        signal = SignalAction.WATCH

    rationale = (
        f"Model Beta — {profile['label']}. "
        f"{profile['bias']}. "
        f"Dzień {days_into}/{total_days} fazy ({progress:.0f}%)."
    )

    return BetaModelStatus(
        period_start=period["start_date"],
        period_end=period["end_date"],
        current_phase=beta_phase,
        phase_number=phase_number,
        days_into_phase=days_into,
        days_remaining_in_phase=days_remaining,
        phase_progress_pct=round(progress, 1),
        historical_bias=profile["bias"],
        signal=signal,
        rationale=rationale,
    )


def presidential_buy_weight(as_of: date | None = None) -> float:
    status = analyze_presidential_cycle(as_of)
    return PHASE_PROFILES[status.current_phase]["buy_weight"]

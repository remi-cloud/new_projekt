"""Map Academy cycle models → Singularity Alpha/Beta scout shapes."""

from __future__ import annotations

from datetime import date

from app.models.schemas import (
    AlphaModelStatus,
    BetaModelStatus,
    BetaPhase,
    BitcoinCycleStatus,
    SignalAction,
)


def bitcoin_as_alpha(btc: BitcoinCycleStatus) -> AlphaModelStatus:
    return AlphaModelStatus(
        reference_date=btc.last_ath_date,
        reference_price=btc.last_ath_price,
        current_price=btc.current_price,
        days_since_reference=btc.days_since_ath,
        phase_a_end_day=btc.bear_phase_end_day,
        phase_b_end_day=btc.bull_phase_end_day,
        phase=btc.phase,
        phase_progress_pct=btc.phase_progress_pct,
        days_remaining_in_phase=btc.days_remaining_in_phase,
        signal=btc.signal,
        rationale=btc.rationale,
    )


def neutral_beta(as_of: date | None = None) -> BetaModelStatus:
    """Beta scout with no presidential tilt (phase 4 + HOLD adds no score)."""
    today = as_of or date.today()
    return BetaModelStatus(
        period_start=today,
        period_end=today,
        current_phase=BetaPhase.PHASE_4,
        phase_number=4,
        days_into_phase=0,
        days_remaining_in_phase=0,
        phase_progress_pct=0.0,
        historical_bias="Brak wpływu",
        signal=SignalAction.HOLD,
        rationale="Cykl prezydencki wyłączony. Beta nie zmienia oceny.",
    )

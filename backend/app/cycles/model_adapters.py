"""Map Academy cycle models → Singularity Alpha/Beta scout shapes."""

from __future__ import annotations

from app.models.schemas import (
    AlphaModelStatus,
    BetaModelStatus,
    BetaPhase,
    BitcoinCycleStatus,
    PresidentialCycleStatus,
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


def presidential_as_beta(pres: PresidentialCycleStatus) -> BetaModelStatus:
    year_n = max(1, min(4, int(pres.year_number)))
    return BetaModelStatus(
        period_start=pres.term_start,
        period_end=pres.term_end,
        current_phase=BetaPhase(f"phase_{year_n}"),
        phase_number=year_n,
        days_into_phase=pres.days_into_year,
        days_remaining_in_phase=pres.days_remaining_in_year,
        phase_progress_pct=pres.year_progress_pct,
        historical_bias=pres.historical_bias,
        signal=pres.signal,
        rationale=pres.rationale,
    )

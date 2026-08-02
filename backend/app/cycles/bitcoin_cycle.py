from datetime import date, datetime, timezone

from app.config import settings
from app.models.schemas import BitcoinCycleStatus, CyclePhase, SignalAction


def _days_between(start: date, end: date) -> int:
    return (end - start).days


def analyze_bitcoin_cycle(
    last_ath_date: date,
    last_ath_price: float,
    current_price: float,
    as_of: date | None = None,
) -> BitcoinCycleStatus:
    as_of = as_of or datetime.now(timezone.utc).date()
    bear_end = settings.btc_bear_phase_days
    bull_end = bear_end + settings.btc_bull_phase_days

    days_since = _days_between(last_ath_date, as_of)
    if days_since < 0:
        days_since = 0

    if days_since < bear_end:
        phase = CyclePhase.BEAR
        phase_start = 0
        phase_length = bear_end
        signal = SignalAction.BUY if days_since > bear_end * 0.5 else SignalAction.WATCH
        rationale = (
            f"Model Alpha — faza spadkowa ({days_since}/{bear_end} d). "
            "Okres preferujący stopniową akumulację."
        )
    elif days_since < bull_end:
        progress_in_bull = days_since - bear_end
        late_bull_start = int(settings.btc_bull_phase_days * 0.75)
        if progress_in_bull > late_bull_start:
            phase = CyclePhase.DISTRIBUTION
            phase_start = bear_end + late_bull_start
            phase_length = max(1, settings.btc_bull_phase_days - late_bull_start)
            signal = SignalAction.SELL
            rationale = (
                f"Model Alpha — końcówka fali wzrostowej ({days_since}/{bull_end} d). "
                "Rozważ redukcję ekspozycji."
            )
        elif progress_in_bull > settings.btc_bull_phase_days * 0.4:
            phase = CyclePhase.BULL
            phase_start = bear_end
            phase_length = settings.btc_bull_phase_days
            signal = SignalAction.HOLD
            rationale = (
                f"Model Alpha — środek fali wzrostowej ({days_since}/{bull_end} d). "
                "Utrzymuj pozycje, unikaj agresywnego dokupywania."
            )
        else:
            phase = CyclePhase.BULL
            phase_start = bear_end
            phase_length = settings.btc_bull_phase_days
            signal = SignalAction.BUY
            rationale = (
                f"Model Alpha — początek fali wzrostowej ({days_since}/{bull_end} d). "
                "Preferowane dokupywanie."
            )
    else:
        phase = CyclePhase.DISTRIBUTION
        phase_start = bull_end
        phase_length = 365
        signal = SignalAction.SELL
        rationale = (
            f"Model Alpha — poza oknem bazowym ({bull_end}+ d). "
            "Faza dystrybucji — ostrożność do nowej referencji."
        )

    elapsed_in_phase = days_since - phase_start
    phase_progress = min(100.0, (elapsed_in_phase / phase_length) * 100)
    days_remaining = max(0, phase_length - elapsed_in_phase)

    return BitcoinCycleStatus(
        last_ath_date=last_ath_date,
        last_ath_price=last_ath_price,
        current_price=current_price,
        days_since_ath=days_since,
        bear_phase_end_day=bear_end,
        bull_phase_end_day=bull_end,
        phase=phase,
        phase_progress_pct=round(phase_progress, 1),
        days_remaining_in_phase=days_remaining,
        signal=signal,
        rationale=rationale,
    )

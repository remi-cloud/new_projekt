from datetime import date, datetime, timezone

from app.config import settings
from app.models.schemas import AlphaModelStatus, CyclePhase, SignalAction


def _days_between(start: date, end: date) -> int:
    return (end - start).days


def analyze_bitcoin_cycle(
    last_ath_date: date,
    last_ath_price: float,
    current_price: float,
    as_of: date | None = None,
) -> AlphaModelStatus:
    """Internal engine for Model Alpha. Public output uses neutral field names."""
    as_of = as_of or datetime.now(timezone.utc).date()
    phase_a_end = settings.alpha_phase_a_days
    phase_b_end = phase_a_end + settings.alpha_phase_b_days

    days_since = _days_between(last_ath_date, as_of)
    if days_since < 0:
        days_since = 0

    if days_since < phase_a_end:
        phase = CyclePhase.BEAR
        phase_start = 0
        phase_length = phase_a_end
        # Early bear = SHORT the decline; mid = watch; late = accumulate (not chase)
        if days_since < phase_a_end * 0.35:
            signal = SignalAction.SELL
            rationale = (
                f"Model Alpha — wczesna faza spadkowa ({days_since}/{phase_a_end} d). "
                "Teraz: SHORT / redukcja. "
                "Później (po ~55% fazy) model przejdzie na akumulację — to nie jest sprzeczność, tylko kolejna faza."
            )
        elif days_since < phase_a_end * 0.55:
            signal = SignalAction.WATCH
            rationale = (
                f"Model Alpha — środek fazy spadkowej ({days_since}/{phase_a_end} d). "
                "Wcześniej był SHORT; teraz CZEKAJ / obserwacja. "
                "LONG (akumulacja) dopiero w późnej części fazy spadkowej — nie graj przeciw trendowi spadku."
            )
        else:
            # Late bear: DCA / scale-in — not an aggressive "all-in LONG" while phase is still bear
            signal = SignalAction.WATCH
            rationale = (
                f"Model Alpha — późna faza spadkowa ({days_since}/{phase_a_end} d). "
                "Oś czasu: wczesny SHORT → środek CZEKAJ → teraz ostrożna akumulacja (DCA). "
                "To NIE jest sygnał „idź all-in long przeciw shortowi”. "
                "Wcześniejszy SHORT już się skończył w kalendarzu modelu; agresywny LONG dopiero po wejściu w falę wzrostową."
            )
    elif days_since < phase_b_end:
        progress_in_b = days_since - phase_a_end
        late_start = int(settings.alpha_phase_b_days * 0.75)
        if progress_in_b > late_start:
            phase = CyclePhase.DISTRIBUTION
            phase_start = phase_a_end + late_start
            phase_length = max(1, settings.alpha_phase_b_days - late_start)
            signal = SignalAction.SELL
            rationale = (
                f"Model Alpha — końcówka fali wzrostowej ({days_since}/{phase_b_end} d). "
                "Rozważ redukcję ekspozycji."
            )
        elif progress_in_b > settings.alpha_phase_b_days * 0.4:
            phase = CyclePhase.BULL
            phase_start = phase_a_end
            phase_length = settings.alpha_phase_b_days
            signal = SignalAction.HOLD
            rationale = (
                f"Model Alpha — środek fali wzrostowej ({days_since}/{phase_b_end} d). "
                "Utrzymuj pozycje, unikaj agresywnego dokupywania."
            )
        else:
            phase = CyclePhase.BULL
            phase_start = phase_a_end
            phase_length = settings.alpha_phase_b_days
            signal = SignalAction.BUY
            rationale = (
                f"Model Alpha — początek fali wzrostowej ({days_since}/{phase_b_end} d). "
                "Preferowane dokupywanie."
            )
    else:
        phase = CyclePhase.DISTRIBUTION
        phase_start = phase_b_end
        phase_length = 365
        signal = SignalAction.SELL
        rationale = (
            f"Model Alpha — poza oknem bazowym ({phase_b_end}+ d). "
            "Faza dystrybucji — ostrożność do nowej referencji."
        )

    elapsed_in_phase = days_since - phase_start
    phase_progress = min(100.0, (elapsed_in_phase / phase_length) * 100)
    days_remaining = max(0, phase_length - elapsed_in_phase)

    return AlphaModelStatus(
        reference_date=last_ath_date,
        reference_price=last_ath_price,
        current_price=current_price,
        days_since_reference=days_since,
        phase_a_end_day=phase_a_end,
        phase_b_end_day=phase_b_end,
        phase=phase,
        phase_progress_pct=round(phase_progress, 1),
        days_remaining_in_phase=days_remaining,
        signal=signal,
        rationale=rationale,
    )

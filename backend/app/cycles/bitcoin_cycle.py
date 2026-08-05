from datetime import date, datetime, timezone

from app.config import settings
from app.cycles.bitcoin_seasonality import (
    adjust_signal_for_btc_seasonality,
    btc_seasonality_desk_brief,
    calendar_season,
    month_bias,
    month_returns_strip,
    resolve_month_avg,
)
from app.cycles.bitcoin_seasonality_data import SPX_COMPARISON
from app.models.schemas import (
    BitcoinCycleStatus,
    BitcoinMonthReturn,
    BtcSpxComparison,
    CyclePhase,
    SignalAction,
)


def _days_between(start: date, end: date) -> int:
    return (end - start).days


def analyze_bitcoin_cycle(
    last_ath_date: date,
    last_ath_price: float,
    current_price: float,
    as_of: date | None = None,
) -> BitcoinCycleStatus:
    """
    Bitcoin cycle based on ATH:
    - Days 0-364 after ATH: bear / decline phase
    - Days 364-1428 (364+1064): bull / growth wave
    - After day 1428: distribution until new ATH establishes next cycle

    Calendar / phase×month seasonality is additive and must not override
    DISTRIBUTION sell via a strong month alone.
    """
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
            f"Faza spadkowa ({days_since}/{bear_end} dni od ATH). "
            "Historycznie okres akumulacji — obserwuj i dokupuj stopniowo."
        )
    elif days_since < bull_end:
        phase = CyclePhase.BULL
        phase_start = bear_end
        phase_length = settings.btc_bull_phase_days
        progress_in_bull = days_since - bear_end
        if progress_in_bull > phase_length * 0.75:
            phase = CyclePhase.DISTRIBUTION
            signal = SignalAction.SELL
            rationale = (
                f"Końcówka fali wzrostowej ({days_since}/{bull_end} dni od ATH). "
                "Rozważ realizację zysków i redukcję ekspozycji."
            )
        elif progress_in_bull > phase_length * 0.4:
            signal = SignalAction.HOLD
            rationale = (
                f"Środek fali wzrostowej ({days_since}/{bull_end} dni od ATH). "
                "Utrzymuj pozycje, unikaj agresywnego dokupywania."
            )
        else:
            signal = SignalAction.BUY
            rationale = (
                f"Początek fali wzrostowej ({days_since}/{bull_end} dni od ATH). "
                "Silna faza wzrostu — preferowane dokupywanie."
            )
    else:
        phase = CyclePhase.DISTRIBUTION
        phase_start = bull_end
        phase_length = 365
        signal = SignalAction.SELL
        rationale = (
            f"Cykl przekroczył {bull_end} dni od ATH. "
            "Faza dystrybucji — ostrożność, czekaj na nowe ATH."
        )

    if phase == CyclePhase.DISTRIBUTION and days_since >= bull_end:
        phase_progress = min(100.0, ((days_since - bull_end) / 365) * 100)
        days_remaining = max(0, 365 - (days_since - bull_end))
    else:
        elapsed_in_phase = days_since - phase_start
        phase_progress = min(100.0, (elapsed_in_phase / phase_length) * 100)
        days_remaining = max(0, phase_length - elapsed_in_phase)

    month_avg, sample_n, _src = resolve_month_avg(
        phase,
        days_since,
        as_of.month,
        bear_end,
        settings.btc_bull_phase_days,
    )
    signal = adjust_signal_for_btc_seasonality(signal, month_avg, phase)

    strip = [
        BitcoinMonthReturn(
            month=row["month"],
            avg_return_pct=row["avg_return_pct"],
            bias=row["bias"],
            is_current=row["is_current"],
            n=row["n"],
        )
        for row in month_returns_strip(as_of)
    ]
    brief = btc_seasonality_desk_brief(
        phase,
        days_since,
        as_of,
        bear_end=bear_end,
        bull_days=settings.btc_bull_phase_days,
    )
    cmp = SPX_COMPARISON
    if month_avg is not None:
        rationale = (
            f"{rationale} Sezonowość: {brief['current_month_name_pl']} "
            f"{month_avg:+.1f}% (n={sample_n}); vs SPX={cmp.get('verdict')}."
        )

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
        month_returns=strip,
        current_month_avg_return_pct=round(month_avg, 2) if month_avg is not None else None,
        current_month_bias=month_bias(month_avg),
        phase_month_bias=month_bias(month_avg),
        seasonality_sample_count=sample_n,
        calendar_season=calendar_season(as_of.month),
        spx_comparison=BtcSpxComparison(
            corr_full=cmp.get("corr_full"),
            corr_rolling_24m_latest=cmp.get("corr_rolling_24m_latest"),
            best_six_delta_pct=cmp.get("best_six_delta_pct"),
            month_sign_agreement=cmp.get("month_sign_agreement"),
            verdict=str(cmp.get("verdict") or "partially"),
            regime=str(cmp.get("regime") or "mixed"),
        ),
    )

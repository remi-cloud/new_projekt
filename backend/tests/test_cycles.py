from datetime import date, timedelta

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.models.schemas import BetaPhase, CyclePhase, SignalAction


def test_alpha_bear_phase():
    ref_date = date.today() - timedelta(days=100)
    result = analyze_bitcoin_cycle(ref_date, 100_000, 80_000)
    assert result.phase == CyclePhase.BEAR
    assert result.days_since_reference == 100
    assert result.signal in (SignalAction.BUY, SignalAction.WATCH)


def test_alpha_bull_phase_early():
    ref_date = date.today() - timedelta(days=400)
    result = analyze_bitcoin_cycle(ref_date, 100_000, 90_000)
    assert result.phase == CyclePhase.BULL
    assert result.signal == SignalAction.BUY


def test_alpha_distribution_late_bull():
    ref_date = date.today() - timedelta(days=1300)
    result = analyze_bitcoin_cycle(ref_date, 100_000, 120_000)
    assert result.phase == CyclePhase.DISTRIBUTION
    assert result.signal == SignalAction.SELL


def test_alpha_post_cycle():
    ref_date = date.today() - timedelta(days=1500)
    result = analyze_bitcoin_cycle(ref_date, 100_000, 110_000)
    assert result.phase == CyclePhase.DISTRIBUTION


def test_beta_returns_valid_phase():
    result = analyze_presidential_cycle()
    assert result.phase_number in (1, 2, 3, 4)
    assert result.current_phase in (
        BetaPhase.PHASE_1,
        BetaPhase.PHASE_2,
        BetaPhase.PHASE_3,
        BetaPhase.PHASE_4,
    )
    assert "Model Beta" in result.rationale
    assert "president" not in result.model_dump()
    assert "ath" not in str(result.model_dump()).lower()


def test_beta_phase_3_is_strongest():
    # Mid of 2025-2029 period phase 3 ≈ 2027
    result = analyze_presidential_cycle(date(2027, 6, 1))
    assert result.phase_number == 3
    assert result.signal == SignalAction.BUY

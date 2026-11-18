"""Unit tests for cycle analysis logic."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.models.schemas import CyclePhase, SignalAction


def test_bitcoin_bear_phase():
    as_of = date(2026, 8, 5)
    ath_date = as_of - timedelta(days=100)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 80_000, as_of=as_of)
    assert result.phase == CyclePhase.BEAR
    assert result.days_since_ath == 100
    assert result.signal in (SignalAction.BUY, SignalAction.WATCH)
    assert len(result.month_returns) == 12
    assert result.spx_comparison is not None
    assert result.spx_comparison.verdict in (
        "similar_to_spx",
        "partially",
        "idiosyncratic",
    )


def test_bitcoin_bull_phase_early():
    # Pin the calendar month. Live "today" in a weak bull-early month
    # (seasonality <= -0.3%) downgrades BUY to WATCH.
    as_of = date(2026, 10, 15)
    ath_date = as_of - timedelta(days=400)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 90_000, as_of=as_of)
    assert result.phase == CyclePhase.BULL
    assert result.signal == SignalAction.BUY


def test_bitcoin_distribution_late_bull():
    ath_date = date.today() - timedelta(days=1300)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 120_000)
    assert result.phase == CyclePhase.DISTRIBUTION
    assert result.signal == SignalAction.SELL


def test_bitcoin_post_cycle():
    ath_date = date.today() - timedelta(days=1500)
    result = analyze_bitcoin_cycle(ath_date, 100_000, 110_000)
    assert result.phase == CyclePhase.DISTRIBUTION


def test_bitcoin_month_matrix_complete():
    from app.cycles.bitcoin_seasonality_data import (
        BTC_CALENDAR_MONTHLY_RETURNS,
        BTC_PHASE_MONTHLY_N,
        SPX_COMPARISON,
    )

    assert set(BTC_CALENDAR_MONTHLY_RETURNS.keys()) == set(range(1, 13))
    assert SPX_COMPARISON.get("aligned_months", 0) >= 24
    assert sum(sum(BTC_PHASE_MONTHLY_N[ph].values()) for ph in BTC_PHASE_MONTHLY_N) >= 24


def test_bitcoin_distribution_not_upgraded_by_strong_month():
    from app.cycles.bitcoin_seasonality import adjust_signal_for_btc_seasonality

    # Strong positive month must not flip DISTRIBUTION SELL → BUY
    sig = adjust_signal_for_btc_seasonality(
        SignalAction.SELL, 10.0, CyclePhase.DISTRIBUTION
    )
    assert sig == SignalAction.SELL


def test_bitcoin_route_returns_the_stored_cycle(client: TestClient, monkeypatch):
    from app.scanners.opportunity_scanner import scanner

    monkeypatch.setattr(scanner, "bitcoin_cycle", {"phase": "test-phase", "month_returns": [0] * 12})
    response = client.get("/api/cycles/bitcoin")
    assert response.status_code == 200
    assert response.json()["phase"] == "test-phase"


def test_bitcoin_route_waits_when_the_feed_is_down(client: TestClient, monkeypatch):
    from app.scanners.opportunity_scanner import scanner

    async def boom() -> None:
        raise RuntimeError("coingecko down")

    monkeypatch.setattr(scanner, "bitcoin_cycle", None)
    monkeypatch.setattr(scanner, "scan", boom)
    monkeypatch.setattr("app.api.cycles.forced_refresh_due", lambda _name: True)
    response = client.get("/api/cycles/bitcoin")
    assert response.status_code == 503
    assert "cykli" in response.json()["detail"]


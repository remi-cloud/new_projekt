"""Regression tests: every displayed market number comes from real, refreshed data.

No network: providers are monkeypatched with deterministic bars, and we assert
the *plumbing* (refresh, provenance, stale flags, 'brak danych') and the
backtest maths against those bars.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.cycles.bitcoin_cycle import BULL_CONFIRM_REBOUND_PCT, analyze_bitcoin_cycle
from app.models.schemas import AssetClass, AssetQuote, ChartCandle, CyclePhase, SignalAction
from app.roi.calculator import _phase_for_bar, _run_strategy, build_bar_contexts, confirmed_cycle_tops


def _daily(prices: list[float], start: date) -> list[ChartCandle]:
    t0 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    return [
        ChartCandle(time=t0 + i * 86400, open=p, high=p, low=p, close=p) for i, p in enumerate(prices)
    ]


# --- scheduler / scanner freshness -------------------------------------------------


@pytest.mark.asyncio
async def test_scheduled_full_scan_forces_a_fresh_scan(monkeypatch):
    from app.scheduler import jobs

    seen: dict = {}

    async def fake_scan(*, force: bool = False):
        seen["force"] = force
        return []

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(jobs.scanner, "scan", fake_scan)
    for name in ("save_opportunities", "_maybe_notify", "_broadcast_state", "_record_agent_telemetry", "_maybe_run_singularity"):
        monkeypatch.setattr(jobs, name, noop)
    await jobs.scheduled_full_scan()
    assert seen.get("force") is True


def _scanner_with_btc(ath_date: date, ath: float, px: float, at: datetime):
    from app.scanners.opportunity_scanner import OpportunityScanner

    sc = OpportunityScanner()
    sc._btc_ath = (ath_date, ath, "CoinGecko", at)
    sc._btc_price = (px, "CoinGecko", at)
    sc._rebuild_bitcoin_cycle()
    return sc


def test_btc_cycle_days_are_computed_for_today_not_scan_time():
    now = datetime.now(timezone.utc)
    ath_day = now.date() - timedelta(days=411)
    sc = _scanner_with_btc(ath_day, 126_080.0, 55_829.0, now)
    b = sc.bitcoin_cycle
    assert b.days_since_ath == 411
    assert b.current_price == 55_829.0
    assert b.price_source == "CoinGecko" and b.price_updated_at == now
    assert b.stale is False
    assert b.drawdown_from_ath_pct == pytest.approx(55.72, abs=0.01)


@pytest.mark.asyncio
async def test_price_tick_refreshes_btc_card_price(monkeypatch):
    now = datetime.now(timezone.utc)
    sc = _scanner_with_btc(now.date() - timedelta(days=400), 126_080.0, 63_699.0, now - timedelta(days=2))
    sc._price_stats = {"BTC-USD": {}}
    assert sc.bitcoin_cycle.stale is True  # 2-day-old price is flagged, not hidden

    async def fake_fast(symbols=None):
        return {
            "BTC-USD": AssetQuote(
                symbol="BTC-USD", name="Bitcoin", asset_class=AssetClass.CRYPTO, price=55_800.0, updated_at=now
            )
        }

    monkeypatch.setattr("app.scanners.opportunity_scanner.fetch_fast_quotes", fake_fast)
    monkeypatch.setattr("app.paper.pricing.merge_fast_quotes", lambda fast: None)
    monkeypatch.setattr(sc, "_reassess", lambda: None)
    await sc.price_tick()
    assert sc.bitcoin_cycle.current_price == 55_800.0
    assert sc.bitcoin_cycle.price_source == "Yahoo Finance (spot)"
    assert sc.bitcoin_cycle.stale is False


@pytest.mark.asyncio
async def test_btc_inputs_fall_back_to_second_real_source(monkeypatch):
    from app.scanners import opportunity_scanner as mod

    async def boom():
        raise RuntimeError("coingecko 429")

    async def yahoo():
        return date(2025, 10, 6), 126_198.07, 55_807.43

    async def low(_ath):
        return 55_659.47, date(2026, 11, 21)

    monkeypatch.setattr(mod, "fetch_bitcoin_ath", boom)
    monkeypatch.setattr(mod, "fetch_bitcoin_ath_yahoo", yahoo)
    monkeypatch.setattr(mod, "fetch_btc_cycle_low", low)
    sc = mod.OpportunityScanner()
    await sc.refresh_bitcoin_inputs()
    assert sc.bitcoin_cycle.ath_source == "Yahoo Finance"
    assert sc.bitcoin_cycle.last_ath_price == 126_198.07
    assert sc.bitcoin_cycle.cycle_low_price == 55_659.47


@pytest.mark.asyncio
async def test_btc_inputs_never_invented_when_all_sources_fail(monkeypatch):
    from app.scanners import opportunity_scanner as mod

    async def boom(*_a):
        raise RuntimeError("down")

    monkeypatch.setattr(mod, "fetch_bitcoin_ath", boom)
    monkeypatch.setattr(mod, "fetch_bitcoin_ath_yahoo", boom)
    sc = mod.OpportunityScanner()
    with pytest.raises(RuntimeError):
        await sc.refresh_bitcoin_inputs()
    assert sc.bitcoin_cycle is None  # → API 503 → UI "brak danych"

    # With a previous real reading we keep it, flagged stale with its real timestamp.
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    sc._btc_ath = (date(2025, 10, 6), 126_080.0, "CoinGecko", old)
    sc._btc_price = (60_000.0, "CoinGecko", old)
    await sc.refresh_bitcoin_inputs()
    assert sc.bitcoin_cycle.current_price == 60_000.0
    assert sc.bitcoin_cycle.stale is True
    assert sc.bitcoin_cycle.price_updated_at == old


# --- BTC cycle phase must match the real market ------------------------------------


def test_bull_window_without_rebound_is_accumulation():
    as_of = date(2026, 11, 21)
    s = analyze_bitcoin_cycle(
        date(2025, 10, 6), 126_080.0, 55_829.0, as_of=as_of,
        cycle_low_price=55_659.0, cycle_low_date=as_of,
    )
    assert s.days_since_ath == 411
    assert s.model_phase == CyclePhase.BULL
    assert s.phase == CyclePhase.ACCUMULATION
    assert s.price_confirmed is False


def test_bull_window_with_real_rebound_is_bull():
    low = 40_000.0
    px = low * (1 + (BULL_CONFIRM_REBOUND_PCT + 5) / 100)
    s = analyze_bitcoin_cycle(
        date(2025, 10, 6), 126_080.0, px, as_of=date(2026, 11, 21),
        cycle_low_price=low, cycle_low_date=date(2026, 6, 1),
    )
    assert s.phase == CyclePhase.BULL and s.price_confirmed is True


# --- backtest maths on real-shaped bars -------------------------------------------


@pytest.mark.asyncio
async def test_backtest_starts_on_requested_day_and_bh_matches_prices(monkeypatch):
    from app.roi import calculator

    start = date(2016, 11, 21)
    warm = date(2015, 9, 1)
    days = (date(2026, 11, 20) - warm).days + 1
    prices = [1000.0 + i for i in range(days)]
    candles = _daily(prices, warm)

    async def fake_hist(symbol, start_=None, end=None, interval=None):
        return candles, warm, date(2026, 11, 20)

    monkeypatch.setattr(calculator, "fetch_long_history", fake_hist)
    r = await calculator.calculate_roi("^GSPC", 10_000, "cycle", start, None, True)
    assert r["data_start"] == start.isoformat()
    sp = prices[(start - warm).days]
    assert r["start_price"] == pytest.approx(sp)
    assert r["buy_hold"]["final_value"] == pytest.approx(10_000 * prices[-1] / sp, rel=1e-6)
    # steady uptrend → the cycle strategy is invested the whole time = B&H here
    assert r["final_value"] == pytest.approx(r["buy_hold"]["final_value"], rel=1e-6)
    assert r["source"].startswith("Yahoo Finance")
    assert r["computed_at"]


def test_btc_cycle_strategy_exits_on_confirmed_top_and_reenters_after_364_days():
    start = date(2019, 1, 1)
    up = [100.0 + i for i in range(100)]  # ATH 199 on day 99
    down = [199.0 * 0.75] * 400  # −25% → top confirmed, no new ATH
    candles = _daily(up + down, start)
    curve, trades, _ = _run_strategy(candles, 1000.0, "cycle", "crypto", "global", 30)
    actions = [(t.action, round(t.price, 2)) for t in trades]
    assert actions[0][0] == "buy"
    assert ("sell", 149.25) in actions
    ctx = build_bar_contexts(candles)
    sell_i = next(i for i, b in enumerate(ctx) if b.top_confirmed)
    _, sig, _ = _phase_for_bar(candles, sell_i + 10, "crypto", "global", ctx)
    assert sig == SignalAction.SELL
    _, sig2, _ = _phase_for_bar(candles, 99 + 364, "crypto", "global", ctx)
    assert sig2 == SignalAction.BUY
    assert trades[-1].action == "buy"


def test_cycle_tops_come_from_bars_not_a_hand_typed_list():
    start = date(2016, 1, 1)
    prices = [50.0] + [100.0 + i for i in range(50)] + [80.0] * 400 + [200.0] * 5
    candles = _daily(prices, start)
    tops = confirmed_cycle_tops(candles, build_bar_contexts(candles))
    assert [t["price"] for t in tops] == [149.0, 200.0]
    assert tops[-1]["label"].endswith("(aktualne)")


# --- showcase: stale / brak danych, never invented ---------------------------------


def _fake_result(symbol: str, final: float) -> dict:
    return {
        "symbol": symbol, "name": symbol, "strategy": "cycle", "amount": 10_000.0,
        "invested": 10_000.0, "final_value": final, "profit": final - 10_000, "roi_pct": final / 100 - 100,
        "cagr_pct": 1.0, "years": 10.0, "data_start": "2016-11-21", "data_end": "2026-11-20",
        "computed_at": "2026-11-21T05:00:00+00:00", "source": "Yahoo Finance",
        "buy_hold": {"final_value": 31_436.87, "roi_pct": 214.37, "cagr_pct": 12.1}, "trades": [],
    }


@pytest.mark.asyncio
async def test_showcase_failure_keeps_last_real_card_flagged_stale(monkeypatch):
    from app.roi import showcase

    showcase._CACHE.update({"expires_at": 0.0, "payload": None, "key": None})
    showcase._LAST_GOOD.clear()

    async def ok(**kw):
        return _fake_result(kw["symbol"], 22_820.52)

    monkeypatch.setattr(showcase, "calculate_roi", ok)
    first = await showcase.get_showcase(years=10, amount=10_000)
    assert all(c["available"] and not c["stale"] for c in first["cards"])

    async def fail(**kw):
        raise RuntimeError("yahoo down")

    showcase._CACHE["expires_at"] = 0.0
    monkeypatch.setattr(showcase, "calculate_roi", fail)
    second = await showcase.get_showcase(years=10, amount=10_000)
    for c in second["cards"]:
        assert c["stale"] is True
        assert c["final_value"] == 22_820.52
        assert c["updated_at"] == "2026-11-21T05:00:00+00:00"


@pytest.mark.asyncio
async def test_showcase_without_any_real_data_reports_brak_danych(monkeypatch):
    from app.roi import showcase

    showcase._CACHE.update({"expires_at": 0.0, "payload": None, "key": None})
    showcase._LAST_GOOD.clear()

    async def fail(**kw):
        raise RuntimeError("yahoo down")

    monkeypatch.setattr(showcase, "calculate_roi", fail)
    out = await showcase.get_showcase(years=10, amount=10_000)
    for c in out["cards"]:
        assert c["available"] is False
        assert c["error"] == "brak danych"
        assert "final_value" not in c and "roi_pct" not in c


# --- seasonality tables refresh from real history -----------------------------------


def test_seasonality_ignores_in_progress_month_and_updates_in_place():
    from app.cycles import bitcoin_seasonality_data as data
    from app.cycles.btc_seasonality_live import apply_tables, complete_months, compute_tables

    rows = []
    for k in range(60):
        y, m = 2021 + k // 12, k % 12 + 1
        px = 100.0 * (1.05 if m % 2 else 0.97) ** k
        rows.append((date(y, m, 1), px, px))
    today = date(2025, 12, 15)
    full = complete_months(rows, today)
    assert full[-1][0] == date(2025, 11, 1)
    snapshot = {k: dict(v) if isinstance(v, dict) else v for k, v in vars(data).items() if k.isupper()}
    ref = data.BTC_CALENDAR_MONTHLY_RETURNS
    try:
        tables = compute_tables(full, full)
        apply_tables(tables)
        assert data.BTC_CALENDAR_MONTHLY_RETURNS is ref  # same object → importers see it
        assert ref == tables["calendar"]
    finally:
        for k, v in snapshot.items():
            cur = getattr(data, k)
            if isinstance(cur, dict):
                cur.clear()
                cur.update(v)


@pytest.mark.asyncio
async def test_seasonality_refresh_failure_keeps_last_real_timestamp(monkeypatch):
    from app.cycles import btc_seasonality_live as live

    before = live.seasonality_state()["updated_at"]

    async def boom(*_a, **_k):
        raise RuntimeError("yahoo down")

    monkeypatch.setattr(live, "_fetch_monthly", boom)
    assert await live.refresh_btc_seasonality() is False
    st = live.seasonality_state()
    assert st["updated_at"] == before
    assert st["last_error"]

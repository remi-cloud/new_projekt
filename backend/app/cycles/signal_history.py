"""Cyclical entry/exit markers anchored to phase transitions in time (point-in-time replay)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.momentum_cycle import analyze_momentum, compute_momentum_indicators
from app.cycles.price_cycle import analyze_price_cycle
from app.cycles.regional_macro import analyze_regional_macro
from app.models.schemas import AssetClass, ChartCandle, CycleMarker, CyclePhase, SignalAction
from app.scanners.asset_analyzer import (
    _apply_traditional_adjustments,
    _class_modifier,
    _combine_signals,
    _combine_three_signals,
)

LOOKBACK_BARS: dict[str, int] = {
    "1m": 60,
    "5m": 80,
    "15m": 96,
    "30m": 96,
    "1H": 120,
    "4H": 126,
    "1D": 90,
    "1W": 52,
    "1M": 60,
    "3M": 126,
    "1Y": 252,
    "MAX": 252,
    "10Y": 252,
}

CHANGE_BARS: dict[str, int] = {
    "1m": 30,
    "5m": 24,
    "15m": 20,
    "30m": 16,
    "1H": 24,
    "4H": 12,
    "1D": 7,
    "1W": 4,
    "1M": 2,
    "3M": 2,
    "1Y": 2,
    "MAX": 2,
    "10Y": 2,
}

MIN_WARMUP = 35
# WEJ only in deep BEAR — ACCUMULATION (10–20% DD) is still "early" on multi-year charts.
ENTRY_PHASES = frozenset({CyclePhase.BEAR})
EXIT_PHASES = frozenset({CyclePhase.DISTRIBUTION})
# Confirmed bottom only: deep DD + near lookback low + bounce lock-in.
ENTRY_MIN_DRAWDOWN_PCT = 25.0
# Mid-decline info (SHORT) only once the move is already deep — not on every 10% chop.
SHORT_ONGOING_MIN_DRAWDOWN_PCT = 25.0
ENTRY_NEAR_LOW_PCT = 3.0
ENTRY_BOUNCE_PCT = 2.5
ENTRY_CONFIRM_BARS = 3
SWING_LOW_LOOKBACK = 12


def _candle_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def _format_date(ts: int) -> str:
    d = _candle_date(ts)
    return d.strftime("%d.%m.%Y")


def _rolling_extremes(candles: list[ChartCandle], idx: int, lookback: int) -> tuple[float, float]:
    start = max(0, idx - lookback + 1)
    window = candles[start : idx + 1]
    return max(c.high for c in window), min(c.low for c in window)


def _rolling_ath(candles: list[ChartCandle], idx: int) -> tuple[date, float]:
    best_price = 0.0
    best_date = _candle_date(candles[0].time)
    for j in range(idx + 1):
        if candles[j].high > best_price:
            best_price = candles[j].high
            best_date = _candle_date(candles[j].time)
    return best_date, best_price


def _pct_change(closes: list[float], bars: int) -> float | None:
    if len(closes) <= bars or bars <= 0:
        return None
    base = closes[-bars - 1]
    if base == 0:
        return None
    return ((closes[-1] - base) / base) * 100


class BarAssessment:
    __slots__ = (
        "price_phase",
        "macro_phase",
        "macro_signal",
        "cycle_signal",
        "final_signal",
        "confidence",
        "rationale",
        "phase_changed",
        "macro_phase_changed",
        "drawdown_pct",
    )

    def __init__(
        self,
        price_phase: CyclePhase,
        macro_phase: str,
        macro_signal: SignalAction,
        cycle_signal: SignalAction,
        final_signal: SignalAction,
        confidence: float,
        rationale: str,
        phase_changed: bool,
        macro_phase_changed: bool,
        drawdown_pct: float,
    ):
        self.price_phase = price_phase
        self.macro_phase = macro_phase
        self.macro_signal = macro_signal
        self.cycle_signal = cycle_signal
        self.final_signal = final_signal
        self.confidence = confidence
        self.rationale = rationale
        self.phase_changed = phase_changed
        self.macro_phase_changed = macro_phase_changed
        self.drawdown_pct = drawdown_pct

def _assess_at_bar(
    candles: list[ChartCandle],
    idx: int,
    *,
    preset: str,
    asset_class: AssetClass,
    region: str,
    symbol: str,
    prev_price_phase: CyclePhase | None,
    prev_macro_phase: str | None,
) -> BarAssessment:
    lookback = LOOKBACK_BARS.get(preset, 126)
    high_52w, low_52w = _rolling_extremes(candles, idx, lookback)
    price = candles[idx].close
    as_of = _candle_date(candles[idx].time)
    drawdown_pct = ((high_52w - price) / high_52w) * 100 if high_52w > 0 else 0.0

    price_phase, price_sig, price_conf, price_rat = analyze_price_cycle(price, high_52w, low_52w)

    closes = [c.close for c in candles[: idx + 1]]
    change_bars = CHANGE_BARS.get(preset, 7)
    change_pct_7d = _pct_change(closes, change_bars)

    if asset_class == AssetClass.CRYPTO:
        ath_date, ath_price = _rolling_ath(candles, idx)
        btc_cycle = analyze_bitcoin_cycle(ath_date, ath_price, price, as_of=as_of)
        macro_sig = btc_cycle.signal
        macro_conf = 50 + btc_cycle.phase_progress_pct * 0.3
        macro_phase = btc_cycle.phase.value
        if symbol == "BTC-USD":
            macro_conf = 60 + btc_cycle.phase_progress_pct * 0.35
        if symbol != "BTC-USD" and change_pct_7d is not None:
            if change_pct_7d < -10 and macro_sig == SignalAction.BUY:
                price_conf += 8
            elif change_pct_7d > 15 and btc_cycle.phase == CyclePhase.DISTRIBUTION:
                macro_sig = SignalAction.SELL
        mom_sig, mom_conf, _, _, mom_rat = analyze_momentum(compute_momentum_indicators(closes))
        cycle_sig2, _ = _combine_signals(macro_sig, macro_conf, price_sig, price_conf, region="global")
        final_sig, final_conf, _ = _combine_three_signals(
            macro_sig, macro_conf, price_sig, price_conf, mom_sig, mom_conf, region="global"
        )
        rationale = f"{_format_date(candles[idx].time)} · cykl BTC {macro_phase} · {price_phase.value} · {mom_rat}"
        macro_phase_str = macro_phase
        cycle_signal = cycle_sig2
        confidence = final_conf
        final_signal = final_sig
    else:
        macro = analyze_regional_macro(
            region=region,
            asset_class=asset_class.value,
            symbol=symbol,
            as_of=as_of,
        )
        macro_phase_str = macro.phase
        class_mod = _class_modifier(asset_class, macro)
        macro_conf = macro.base_confidence * class_mod
        macro_sig = macro.signal

        from app.models.schemas import AssetQuote

        quote = AssetQuote(
            symbol=symbol,
            name=symbol,
            asset_class=asset_class,
            price=price,
            change_pct_24h=None,
            change_pct_7d=change_pct_7d,
            updated_at=datetime.fromtimestamp(candles[idx].time, tz=timezone.utc),
        )
        macro_sig, macro_conf, price_sig, price_conf = _apply_traditional_adjustments(
            quote, macro, macro_sig, macro_conf, price_sig, price_conf
        )
        mom_sig, mom_conf, _, _, mom_rat = analyze_momentum(compute_momentum_indicators(closes))
        cycle_sig2, _ = _combine_signals(macro_sig, macro_conf, price_sig, price_conf, region=region)
        final_sig, final_conf, _ = _combine_three_signals(
            macro_sig, macro_conf, price_sig, price_conf, mom_sig, mom_conf, region=region
        )
        rationale = f"{_format_date(candles[idx].time)} · {macro.cycle_id} {macro_phase_str} · {price_phase.value} · {mom_rat}"
        cycle_signal = cycle_sig2
        confidence = final_conf
        final_signal = final_sig
        macro_sig = macro_sig

    phase_changed = prev_price_phase is not None and price_phase != prev_price_phase
    macro_phase_changed = prev_macro_phase is not None and macro_phase_str != prev_macro_phase

    return BarAssessment(
        price_phase=price_phase,
        macro_phase=macro_phase_str,
        macro_signal=macro_sig,
        cycle_signal=cycle_signal,
        final_signal=final_signal,
        confidence=confidence,
        rationale=rationale,
        phase_changed=phase_changed,
        macro_phase_changed=macro_phase_changed,
        drawdown_pct=drawdown_pct,
    )


def _swing_low(candles: list[ChartCandle], idx: int, lookback: int = SWING_LOW_LOOKBACK) -> float:
    start = max(0, idx - lookback + 1)
    return min(c.low for c in candles[start : idx + 1])


def _is_confirmed_bottom(
    candles: list[ChartCandle],
    idx: int,
    *,
    trough_idx: int,
    trough_price: float,
    trough_drawdown_pct: float,
    assess: BarAssessment,
) -> bool:
    """WEJ only after the absolute swing low is locked in with a bounce — never mid-decline."""
    if trough_idx < 0 or trough_price <= 0:
        return False
    if idx - trough_idx < ENTRY_CONFIRM_BARS:
        return False
    if trough_drawdown_pct < ENTRY_MIN_DRAWDOWN_PCT:
        return False
    candle = candles[idx]
    if candle.close < trough_price * (1.0 + ENTRY_BOUNCE_PCT / 100.0):
        return False
    # Trough must still be the lowest print in the recent swing window.
    if trough_price > _swing_low(candles, idx) * (1.0 + 1e-9):
        return False
    if assess.macro_signal == SignalAction.SELL:
        return False
    if assess.final_signal == SignalAction.SELL:
        return False
    # Bottom geometry is the gate; consensus must not fight the entry.
    return True


def _trough_near_period_low(
    candles: list[ChartCandle],
    trough_idx: int,
    trough_price: float,
    *,
    preset: str,
) -> bool:
    lookback = LOOKBACK_BARS.get(preset, 126)
    _, period_low = _rolling_extremes(candles, trough_idx, lookback)
    if period_low <= 0:
        return False
    return trough_price <= period_low * (1.0 + ENTRY_NEAR_LOW_PCT / 100.0)


def _is_exit_moment(assess: BarAssessment, prev_phase: CyclePhase | None, in_position: bool) -> bool:
    if not in_position or prev_phase is None:
        return False
    if assess.price_phase in EXIT_PHASES and prev_phase not in EXIT_PHASES:
        return True
    if assess.macro_phase_changed and assess.macro_signal == SignalAction.SELL:
        return True
    if assess.phase_changed and prev_phase in (CyclePhase.BULL, CyclePhase.ACCUMULATION) and assess.final_signal == SignalAction.SELL:
        return True
    return False


def _dedupe_markers(markers: list[CycleMarker]) -> list[CycleMarker]:
    """Prefer WEJ over short-ongoing info when both land on the same bar."""
    by_time: dict[int, CycleMarker] = {}
    rank = {SignalAction.BUY: 3, SignalAction.SELL: 2, SignalAction.WATCH: 1, SignalAction.HOLD: 0}
    for m in markers:
        prev = by_time.get(m.time)
        if prev is None or rank.get(m.action, 0) >= rank.get(prev.action, 0):
            by_time[m.time] = m
    return sorted(by_time.values(), key=lambda m: m.time)


def compute_cycle_markers(
    candles: list[ChartCandle],
    *,
    preset: str = "3M",
    asset_class: str = "stock",
    region: str = "global",
    symbol: str = "",
    btc_ath_date: date | None = None,
    btc_ath_price: float | None = None,
) -> list[CycleMarker]:
    del btc_ath_date, btc_ath_price  # point-in-time ATH from candles

    if len(candles) < MIN_WARMUP + 2:
        return []

    try:
        ac = AssetClass(asset_class)
    except ValueError:
        ac = AssetClass.STOCK

    markers: list[CycleMarker] = []
    in_position = False
    prev_price_phase: CyclePhase | None = None
    prev_macro_phase: str | None = None

    # Deferred entry: track trough during decline; WEJ only at confirmed bottom.
    trough_idx: int | None = None
    trough_price: float | None = None
    trough_drawdown_pct = 0.0
    trough_phase: CyclePhase | None = None
    episode_short_time: int | None = None
    episode_short_price: float | None = None
    episode_short_rationale: str | None = None

    for idx in range(MIN_WARMUP, len(candles)):
        assess = _assess_at_bar(
            candles,
            idx,
            preset=preset,
            asset_class=ac,
            region=region,
            symbol=symbol,
            prev_price_phase=prev_price_phase,
            prev_macro_phase=prev_macro_phase,
        )
        candle = candles[idx]
        # Track trough across ACCUMULATION+BEAR so we catch the true low, but never WEJ there early.
        in_drawdown = (
            assess.price_phase in (CyclePhase.BEAR, CyclePhase.ACCUMULATION)
            and assess.drawdown_pct >= 10.0
        )
        in_deep_short = (
            assess.price_phase in ENTRY_PHASES
            and assess.drawdown_pct >= SHORT_ONGOING_MIN_DRAWDOWN_PCT
        )

        if not in_position:
            if in_drawdown:
                if trough_idx is None or candle.low < (trough_price or float("inf")):
                    trough_idx = idx
                    trough_price = candle.low
                    trough_drawdown_pct = assess.drawdown_pct
                    trough_phase = assess.price_phase

                # Remember first deep-BEAR touch — paint as SHORT only if WEJ later confirms.
                if in_deep_short and episode_short_time is None:
                    episode_short_time = candle.time
                    episode_short_price = candle.close
                    episode_short_rationale = assess.rationale

            confirmed = False
            trough_is_entry_phase = trough_phase is not None and trough_phase in ENTRY_PHASES
            if (
                trough_idx is not None
                and trough_price is not None
                and trough_is_entry_phase
                and trough_drawdown_pct >= ENTRY_MIN_DRAWDOWN_PCT
                and _trough_near_period_low(candles, trough_idx, trough_price, preset=preset)
                and _is_confirmed_bottom(
                    candles,
                    idx,
                    trough_idx=trough_idx,
                    trough_price=trough_price,
                    trough_drawdown_pct=trough_drawdown_pct,
                    assess=assess,
                )
            ):
                if episode_short_time is not None and episode_short_time != candles[trough_idx].time:
                    markers.append(
                        CycleMarker(
                            time=episode_short_time,
                            action=SignalAction.WATCH,
                            confidence=45.0,
                            price=round(episode_short_price or 0.0, 6),
                            rationale=(
                                f"{episode_short_rationale or ''} · short ongoing "
                                f"(info — WEJ dopiero na potwierdzonym dołku)"
                            ).strip(),
                        )
                    )
                bottom = candles[trough_idx]
                markers.append(
                    CycleMarker(
                        time=bottom.time,
                        action=SignalAction.BUY,
                        confidence=round(max(assess.confidence, 75.0), 1),
                        price=round(bottom.low, 6),
                        rationale=(
                            f"{_format_date(bottom.time)} · potwierdzony dołek "
                            f"(DD {trough_drawdown_pct:.1f}% · bounce) · {assess.rationale}"
                        ),
                    )
                )
                in_position = True
                confirmed = True
                trough_idx = None
                trough_price = None
                trough_drawdown_pct = 0.0
                trough_phase = None
                episode_short_time = None
                episode_short_price = None
                episode_short_rationale = None

            if not confirmed and not in_drawdown:
                # Abort without painting orphan SHORT markers.
                trough_idx = None
                trough_price = None
                trough_drawdown_pct = 0.0
                trough_phase = None
                episode_short_time = None
                episode_short_price = None
                episode_short_rationale = None
        elif in_position and _is_exit_moment(assess, prev_price_phase, in_position):
            markers.append(
                CycleMarker(
                    time=candle.time,
                    action=SignalAction.SELL,
                    confidence=round(assess.confidence, 1),
                    price=round(candle.close, 6),
                    rationale=assess.rationale,
                )
            )
            in_position = False
            trough_idx = None
            trough_price = None
            trough_drawdown_pct = 0.0
            trough_phase = None
            episode_short_time = None
            episode_short_price = None
            episode_short_rationale = None

        prev_price_phase = assess.price_phase
        prev_macro_phase = assess.macro_phase

    return _dedupe_markers(markers)

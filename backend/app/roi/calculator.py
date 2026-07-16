"""ROI backtest engine: buy & hold vs cycle-timed investing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.cycles.price_cycle import analyze_price_cycle
from app.data.assets import MONITORED_ASSETS
from app.models.schemas import ChartCandle, CyclePhase, SignalAction
from app.roi.history import DEFAULT_FROM, fetch_long_history

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

Strategy = Literal["buy_hold", "cycle", "dca", "cycle_dca"]

# Documented BTC cycle peak ATHs used for UI timeline (informational)
BTC_CYCLE_ATHS: list[dict] = [
    {"date": "2011-06-08", "price": 32.0, "label": "Cycle 2011"},
    {"date": "2013-12-04", "price": 1156.0, "label": "Cycle 2013"},
    {"date": "2017-12-17", "price": 19783.0, "label": "Cycle 2017"},
    {"date": "2021-11-10", "price": 69000.0, "label": "Cycle 2021"},
]


@dataclass
class EquityPoint:
    time: int
    equity: float
    price: float
    invested: float
    phase: str | None = None


@dataclass
class TradeEvent:
    time: int
    action: str  # buy | sell
    price: float
    amount: float
    units: float
    rationale: str
    phase: str


def _candle_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def _rolling_ath(candles: list[ChartCandle], idx: int) -> tuple[date, float]:
    best_price = 0.0
    best_date = _candle_date(candles[0].time)
    for j in range(idx + 1):
        if candles[j].high > best_price:
            best_price = candles[j].high
            best_date = _candle_date(candles[j].time)
    return best_date, best_price


def _rolling_52w(candles: list[ChartCandle], idx: int, lookback: int = 52) -> tuple[float, float]:
    start = max(0, idx - lookback + 1)
    window = candles[start : idx + 1]
    return max(c.high for c in window), min(c.low for c in window)


def _phase_for_bar(
    candles: list[ChartCandle],
    idx: int,
    asset_class: str,
    region: str,
) -> tuple[CyclePhase, SignalAction, str]:
    """Point-in-time cycle signal for one bar."""
    c = candles[idx]
    as_of = _candle_date(c.time)

    if asset_class == "crypto":
        ath_date, ath_price = _rolling_ath(candles, idx)
        status = analyze_bitcoin_cycle(ath_date, ath_price, c.close, as_of=as_of)
        dd = ((ath_price - c.close) / ath_price * 100) if ath_price > 0 else 0.0
        # Deep crash from ATH → sell (cycle peak has broken)
        if dd >= 40:
            return CyclePhase.DISTRIBUTION, SignalAction.SELL, f"Drawdown {dd:.0f}% from ATH"
        # Accumulation only after a real post-ATH washout (not day-0 of a fresh ATH)
        if dd >= 25 and status.days_since_ath >= 90:
            return CyclePhase.BEAR, SignalAction.BUY, f"Accumulation −{dd:.0f}% · day {status.days_since_ath}"
        if status.days_since_ath < 60 and dd < 15:
            # Fresh ATH / euphoria — avoid new buys
            return CyclePhase.DISTRIBUTION, SignalAction.HOLD, f"Near ATH ({dd:.0f}%) · hold"
        return status.phase, status.signal, f"BTC cycle · {status.phase.value} · day {status.days_since_ath}"

    high_52, low_52 = _rolling_52w(candles, idx)
    phase, signal, _conf, _rationale = analyze_price_cycle(c.close, high_52, low_52)

    if region == "us" and asset_class in ("stock", "etf", "index"):
        pres = analyze_presidential_cycle(as_of)
        if phase in (CyclePhase.BEAR, CyclePhase.ACCUMULATION) or pres.signal == SignalAction.BUY:
            if phase == CyclePhase.DISTRIBUTION:
                return CyclePhase.DISTRIBUTION, SignalAction.SELL, f"Price peak + {pres.current_year.value}"
            return phase, SignalAction.BUY, f"Pres. {pres.current_year.value} · {phase.value}"
        if phase == CyclePhase.DISTRIBUTION or pres.signal == SignalAction.SELL:
            return CyclePhase.DISTRIBUTION, SignalAction.SELL, f"Exit · {pres.current_year.value}"
        return phase, SignalAction.HOLD, f"Pres. {pres.current_year.value}"

    return phase, signal, f"Price cycle · {phase.value}"


def _should_buy(signal: SignalAction, phase: CyclePhase) -> bool:
    if signal == SignalAction.BUY:
        return True
    return phase in (CyclePhase.BEAR, CyclePhase.ACCUMULATION) and signal == SignalAction.WATCH


def _should_sell(signal: SignalAction, phase: CyclePhase) -> bool:
    return signal == SignalAction.SELL


def _cagr(start_equity: float, end_equity: float, years: float) -> float:
    if start_equity <= 0 or end_equity <= 0 or years <= 0:
        return 0.0
    return (math.pow(end_equity / start_equity, 1 / years) - 1) * 100


def _max_drawdown(curve: list[EquityPoint]) -> float:
    peak = 0.0
    max_dd = 0.0
    for p in curve:
        peak = max(peak, p.equity)
        if peak > 0:
            dd = (peak - p.equity) / peak * 100
            max_dd = max(max_dd, dd)
    return max_dd


def _downsample(curve: list[EquityPoint], max_points: int = 400) -> list[EquityPoint]:
    if len(curve) <= max_points:
        return curve
    step = math.ceil(len(curve) / max_points)
    out = curve[::step]
    if out[-1] is not curve[-1]:
        out.append(curve[-1])
    return out


def _run_strategy(
    candles: list[ChartCandle],
    amount: float,
    strategy: Strategy,
    asset_class: str,
    region: str,
    dca_interval_bars: int,
) -> tuple[list[EquityPoint], list[TradeEvent], float]:
    """
    Returns equity curve, trades, total invested.
    Cycle strategies: cash → buy on accumulation/bear, sell on distribution → cash again.
    """
    cash = amount if strategy in ("buy_hold", "cycle") else 0.0
    units = 0.0
    invested = 0.0
    dca_cash_reserve = amount if strategy in ("dca", "cycle_dca") else 0.0
    installment = amount / max(1, (len(candles) // max(1, dca_interval_bars)))

    curve: list[EquityPoint] = []
    trades: list[TradeEvent] = []
    last_buy_bar = -999
    last_sell_bar = -999
    prev_phase: CyclePhase | None = None

    for i, c in enumerate(candles):
        phase, signal, rationale = _phase_for_bar(candles, i, asset_class, region)
        price = c.close

        if strategy == "buy_hold":
            if i == 0 and cash > 0 and price > 0:
                units = cash / price
                invested = cash
                trades.append(
                    TradeEvent(c.time, "buy", price, cash, units, "Buy & hold — entry", phase.value)
                )
                cash = 0.0

        elif strategy == "dca":
            if i % dca_interval_bars == 0 and dca_cash_reserve > 0 and price > 0:
                put = min(installment, dca_cash_reserve)
                if put > 0:
                    bought = put / price
                    units += bought
                    invested += put
                    dca_cash_reserve -= put
                    trades.append(
                        TradeEvent(c.time, "buy", price, put, bought, "DCA installment", phase.value)
                    )

        elif strategy == "cycle":
            # Lump sum: deploy when buy zone, exit when distribution
            if cash > 0 and units == 0 and _should_buy(signal, phase) and price > 0 and i - last_sell_bar > 2:
                units = cash / price
                invested = amount
                trades.append(
                    TradeEvent(c.time, "buy", price, cash, units, rationale, phase.value)
                )
                cash = 0.0
                last_buy_bar = i
            elif units > 0 and _should_sell(signal, phase) and i - last_buy_bar > 3:
                proceeds = units * price
                trades.append(
                    TradeEvent(c.time, "sell", price, proceeds, units, rationale, phase.value)
                )
                cash = proceeds
                units = 0.0
                last_sell_bar = i
            # Warm-up buy only in clear buy zones (not euphoria / fresh ATH)
            if (
                i == 4
                and cash > 0
                and units == 0
                and signal == SignalAction.BUY
                and phase in (CyclePhase.BEAR, CyclePhase.ACCUMULATION)
                and price > 0
            ):
                units = cash / price
                invested = amount
                trades.append(
                    TradeEvent(c.time, "buy", price, cash, units, "Cycle entry (warmup)", phase.value)
                )
                cash = 0.0
                last_buy_bar = i

        elif strategy == "cycle_dca":
            if (
                i % dca_interval_bars == 0
                and dca_cash_reserve > 0
                and price > 0
                and _should_buy(signal, phase)
            ):
                put = min(installment, dca_cash_reserve)
                if put > 0:
                    bought = put / price
                    units += bought
                    invested += put
                    dca_cash_reserve -= put
                    trades.append(
                        TradeEvent(c.time, "buy", price, put, bought, rationale, phase.value)
                    )
            # Optionally trim in distribution
            if units > 0 and _should_sell(signal, phase) and prev_phase != phase and i - last_buy_bar > 5:
                sell_units = units * 0.5
                proceeds = sell_units * price
                units -= sell_units
                dca_cash_reserve += proceeds
                trades.append(
                    TradeEvent(c.time, "sell", price, proceeds, sell_units, rationale, phase.value)
                )
                last_sell_bar = i

        equity = cash + units * price + (dca_cash_reserve if strategy in ("dca", "cycle_dca") else 0.0)
        # For cycle lump-sum not yet invested, equity stays as cash
        if strategy == "cycle" and units == 0 and cash == 0:
            equity = 0.0

        # Track invested properly for cycle (initial capital always "at risk" as cash)
        display_invested = amount if strategy in ("buy_hold", "cycle") else invested
        if strategy == "cycle":
            display_invested = amount

        curve.append(
            EquityPoint(
                time=c.time,
                equity=round(equity, 2),
                price=round(price, 6),
                invested=round(display_invested if display_invested else amount, 2),
                phase=phase.value,
            )
        )
        prev_phase = phase

    # Remaining DCA cash is part of equity already
    total_invested = amount if strategy in ("buy_hold", "cycle") else invested
    if strategy in ("dca", "cycle_dca") and total_invested <= 0:
        total_invested = amount - dca_cash_reserve
    return curve, trades, total_invested


async def calculate_roi(
    symbol: str,
    amount: float,
    strategy: Strategy = "buy_hold",
    start: date | None = None,
    end: date | None = None,
    compare_buy_hold: bool = True,
) -> dict:
    meta = ASSET_MAP.get(symbol)
    if not meta:
        raise ValueError(f"Unknown symbol: {symbol}")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if strategy not in ("buy_hold", "cycle", "dca", "cycle_dca"):
        raise ValueError("Invalid strategy")

    asset_class = meta["asset_class"]
    region = meta.get("region", "global")
    default_start = DEFAULT_FROM.get(asset_class, date(2000, 1, 1))
    start = start or default_start

    candles, data_start, data_end = await fetch_long_history(symbol, start, end)
    if len(candles) < 10:
        raise ValueError(f"Not enough history for {symbol}")

    # DCA interval: ~monthly on weekly bars (~4), ~monthly on daily (~21)
    span_days = (data_end - data_start).days if data_start and data_end else 365
    bars_per_year = max(12, len(candles) / max(1, span_days / 365))
    dca_interval = max(1, int(round(bars_per_year / 12)))

    curve, trades, invested = _run_strategy(
        candles, amount, strategy, asset_class, region, dca_interval
    )
    final = curve[-1].equity if curve else 0.0
    years = max(span_days / 365.25, 0.01)
    roi_pct = ((final - invested) / invested * 100) if invested > 0 else 0.0
    cagr = _cagr(invested, final, years) if invested > 0 else 0.0
    mdd = _max_drawdown(curve)

    result: dict = {
        "mode": "backtest",
        "symbol": symbol,
        "name": meta["name"],
        "asset_class": asset_class,
        "region": region,
        "strategy": strategy,
        "amount": amount,
        "invested": round(invested, 2),
        "final_value": round(final, 2),
        "profit": round(final - invested, 2),
        "roi_pct": round(roi_pct, 2),
        "cagr_pct": round(cagr, 2),
        "max_drawdown_pct": round(mdd, 2),
        "years": round(years, 2),
        "data_start": data_start.isoformat() if data_start else None,
        "data_end": data_end.isoformat() if data_end else None,
        "bars": len(candles),
        "cycle_source": (
            "bitcoin_ath"
            if asset_class == "crypto"
            else ("presidential+price" if region == "us" else "price_cycle")
        ),
        "equity_curve": [
            {"time": p.time, "equity": p.equity, "price": p.price, "phase": p.phase}
            for p in _downsample(curve)
        ],
        "trades": [
            {
                "time": t.time,
                "action": t.action,
                "price": round(t.price, 6),
                "amount": round(t.amount, 2),
                "units": round(t.units, 6),
                "rationale": t.rationale,
                "phase": t.phase,
            }
            for t in trades[:80]
        ],
        "price_series": [
            {"time": c.time, "value": c.close}
            for c in candles[:: max(1, len(candles) // 400)]
        ],
        "btc_cycle_aths": BTC_CYCLE_ATHS if symbol == "BTC-USD" else [],
        "disclaimer": (
            "Symulacja historyczna na cenach Yahoo Finance. Cykle BTC: 364 dni spadek + 1064 wzrost od ATH. "
            "Przeszłość ≠ przyszłość. To nie rekomendacja inwestycyjna."
        ),
    }

    if compare_buy_hold and strategy != "buy_hold":
        bh_curve, _, bh_invested = _run_strategy(
            candles, amount, "buy_hold", asset_class, region, dca_interval
        )
        bh_final = bh_curve[-1].equity if bh_curve else 0.0
        bh_roi = ((bh_final - bh_invested) / bh_invested * 100) if bh_invested else 0.0
        result["buy_hold"] = {
            "final_value": round(bh_final, 2),
            "roi_pct": round(bh_roi, 2),
            "cagr_pct": round(_cagr(bh_invested, bh_final, years), 2),
            "max_drawdown_pct": round(_max_drawdown(bh_curve), 2),
            "equity_curve": [
                {"time": p.time, "equity": p.equity}
                for p in _downsample(bh_curve)
            ],
        }

    return result


def list_roi_assets() -> list[dict]:
    out = []
    for a in MONITORED_ASSETS:
        ac = a["asset_class"]
        out.append(
            {
                "symbol": a["symbol"],
                "name": a["name"],
                "asset_class": ac,
                "region": a.get("region", "global"),
                "history_from": DEFAULT_FROM.get(ac, date(2000, 1, 1)).isoformat(),
            }
        )
    return out

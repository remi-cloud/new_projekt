"""Forward ROI projection: invest today → value in N years via cycle + sentiment."""

from __future__ import annotations

import math
from calendar import monthrange
from datetime import date, datetime, timezone

from app.config import settings
from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.momentum_cycle import analyze_momentum, compute_momentum_indicators
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.cycles.price_cycle import analyze_price_cycle
from app.data.assets import MONITORED_ASSETS
from app.data.market_data import fetch_bitcoin_ath
from app.models.schemas import SignalAction
from app.roi.history import DEFAULT_FROM, fetch_long_history

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

# Historical phase returns (annualized) calibrated from multi-cycle experience.
# Used as forward priors; scaled by asset-specific historical CAGR.
CRYPTO_PHASE_ANNUAL: dict[str, float] = {
    "bear": -35.0,  # early washout after ATH
    "accumulation": 55.0,  # late bear / buy zone
    "bull": 95.0,  # primary advance
    "distribution": -15.0,  # late cycle / near peak
    "neutral": 25.0,
}

# Long-run mean-reversion priors (annual %) for multi-decade horizons
TERMINAL_CAGR = {
    "crypto": 15.0,
    "stock": 9.0,
    "etf": 9.0,
    "index": 8.5,
    "bond": 4.0,
    "commodity": 5.0,
    "forex": 2.0,
}

EQUITY_BASE_ANNUAL = 8.5
PRESIDENTIAL_ANNUAL = {
    "year_1": 7.1,
    "year_2": 3.9,
    "year_3": 16.0,
    "year_4": 6.8,
}


def _blend_to_terminal(phase_annual: float, terminal: float, month_index: int, total_months: int) -> float:
    """Early years follow cycle phases; later years mean-revert to sustainable CAGR."""
    progress = month_index / max(total_months, 1)
    # first ~8 years keep cycle color; then blend hard toward terminal
    if progress < 0.25:
        w_phase = 0.85
    elif progress < 0.5:
        w_phase = 0.55
    else:
        w_phase = 0.25
    return w_phase * phase_annual + (1 - w_phase) * terminal


PRICE_PHASE_ADJ: dict[str, float] = {
    "bear": 1.25,  # buy low → higher expected forward
    "accumulation": 1.15,
    "bull": 1.0,
    "distribution": 0.55,
    "neutral": 0.9,
}


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def _cagr_from_prices(start: float, end: float, years: float) -> float:
    if start <= 0 or end <= 0 or years <= 0:
        return EQUITY_BASE_ANNUAL
    return (math.pow(end / start, 1 / years) - 1) * 100


def _monthly_factor(annual_pct: float) -> float:
    return math.pow(1 + annual_pct / 100, 1 / 12)


def _sentiment_from_momentum(score: float) -> tuple[float, str]:
    """
    Map momentum 0–100 → sentiment multiplier around 1.0 and a label.
    Bullish >1 amplifies growth phases; bearish dampens.
    """
    # score 50 = neutral 1.0; 80 → ~1.18; 20 → ~0.82
    mult = 0.7 + (score / 100) * 0.6
    mult = max(0.65, min(1.35, mult))
    if score >= 70:
        label = "bullish"
    elif score >= 55:
        label = "constructive"
    elif score >= 45:
        label = "neutral"
    elif score >= 30:
        label = "cautious"
    else:
        label = "bearish"
    return mult, label


def _historical_cagr(candles) -> float:
    if len(candles) < 24:
        return EQUITY_BASE_ANNUAL
    years = max((_candle_years(candles[0].time, candles[-1].time)), 0.5)
    return _cagr_from_prices(candles[0].close, candles[-1].close, years)


def _candle_years(t0: int, t1: int) -> float:
    return max((t1 - t0) / (365.25 * 86400), 0.01)


def _crypto_phase_at(days_since_ath: int) -> tuple[str, float]:
    """Return (phase_key, annual_expected) for a day position in BTC cycle."""
    bear = settings.btc_bear_phase_days
    bull = settings.btc_bull_phase_days
    cycle = bear + bull
    d = days_since_ath % cycle
    if d < bear * 0.45:
        return "bear", CRYPTO_PHASE_ANNUAL["bear"]
    if d < bear:
        return "accumulation", CRYPTO_PHASE_ANNUAL["accumulation"]
    progress_bull = d - bear
    if progress_bull > bull * 0.75:
        return "distribution", CRYPTO_PHASE_ANNUAL["distribution"]
    return "bull", CRYPTO_PHASE_ANNUAL["bull"]


def _scale_crypto_returns(hist_cagr: float) -> float:
    """Scale crypto phase priors relative to observed historical CAGR."""
    # If asset compounded ~60%/yr historically, scale phases up vs BTC prior (~40% blended).
    blend_prior = 40.0
    return max(0.35, min(2.5, abs(hist_cagr) / blend_prior)) if hist_cagr else 1.0


async def project_forward(
    symbol: str,
    amount: float,
    years: int = 30,
    strategy: str = "buy_hold",
    monthly_contribution: float = 0.0,
) -> dict:
    """
    Project investment opened TODAY for `years` ahead.
    Walks month-by-month through cycle phases + applies live market sentiment.
    """
    meta = ASSET_MAP.get(symbol)
    if not meta:
        raise ValueError(f"Unknown symbol: {symbol}")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    years = max(1, min(50, int(years)))
    strategy = strategy if strategy in ("buy_hold", "cycle", "dca", "cycle_dca") else "buy_hold"
    monthly_contribution = max(0.0, float(monthly_contribution or 0))

    asset_class = meta["asset_class"]
    region = meta.get("region", "global")
    today = datetime.now(timezone.utc).date()

    # History for CAGR + momentum sentiment
    hist_start = DEFAULT_FROM.get(asset_class, date(2000, 1, 1))
    candles, data_start, data_end = await fetch_long_history(symbol, hist_start, today)
    if len(candles) < 10:
        raise ValueError(f"Not enough history for {symbol}")

    hist_cagr = _historical_cagr(candles)
    closes = [c.close for c in candles[-120:]]
    mom_sig, mom_conf, mom_phase, mom_score, mom_rat = analyze_momentum(
        compute_momentum_indicators(closes)
    )
    sentiment_mult, sentiment_label = _sentiment_from_momentum(mom_score)

    current_price = candles[-1].close
    high_52 = max(c.high for c in candles[-52:]) if len(candles) >= 12 else current_price
    low_52 = min(c.low for c in candles[-52:]) if len(candles) >= 12 else current_price
    price_phase, price_sig, _, price_rat = analyze_price_cycle(current_price, high_52, low_52)

    # Current cycle position
    days_since_ath = 0
    ath_date = today
    ath_price = current_price
    cycle_phase = price_phase.value
    cycle_rationale = price_rat
    cycle_source = "price_cycle"

    if asset_class == "crypto":
        cycle_source = "bitcoin_ath"
        try:
            if symbol == "BTC-USD":
                ath_date, ath_price, btc_px = await fetch_bitcoin_ath()
                current_price = btc_px or current_price
            else:
                # Approximate ATH from local history peak
                ath_price = max(c.high for c in candles)
                for c in candles:
                    if c.high >= ath_price:
                        ath_date = datetime.fromtimestamp(c.time, tz=timezone.utc).date()
            status = analyze_bitcoin_cycle(ath_date, ath_price, current_price, as_of=today)
            days_since_ath = status.days_since_ath
            cycle_phase = status.phase.value
            cycle_rationale = status.rationale
        except Exception:
            days_since_ath = 400  # mid-cycle fallback
            cycle_phase = "bull"
            cycle_rationale = "Fallback mid-cycle (ATH fetch failed)"
    elif region == "us" and asset_class in ("stock", "etf", "index", "tokenized"):
        cycle_source = "presidential+price"
        pres = analyze_presidential_cycle(today)
        cycle_phase = f"{pres.current_year.value}+{price_phase.value}"
        cycle_rationale = pres.rationale

    # Portfolio state
    months = years * 12
    crypto_scale = _scale_crypto_returns(hist_cagr) if asset_class == "crypto" else 1.0

    base_curve: list[dict] = []
    opt_curve: list[dict] = []
    pes_curve: list[dict] = []
    milestones: list[dict] = []
    phase_log: list[dict] = []

    equity_b = amount
    equity_o = amount
    equity_p = amount
    invested_total = amount
    last_logged_phase = ""

    for m in range(months + 1):
        as_of = _add_months(today, m)
        ts = int(datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc).timestamp())

        # Determine month's expected annual return
        terminal = TERMINAL_CAGR.get(asset_class, EQUITY_BASE_ANNUAL)
        if asset_class == "crypto":
            d_ath = days_since_ath + m * 30
            phase_key, phase_ann = _crypto_phase_at(d_ath)
            annual = phase_ann * crypto_scale
            annual = max(-45.0, min(120.0, annual))
            annual = _blend_to_terminal(annual, terminal, m, months)
            # Soft floor using observed hist CAGR for near-term realism
            if m < 36:
                annual = 0.7 * annual + 0.3 * min(hist_cagr, 80.0)
        elif region == "us" and asset_class in ("stock", "etf", "index", "tokenized"):
            pres = analyze_presidential_cycle(as_of)
            annual = PRESIDENTIAL_ANNUAL.get(pres.current_year.value, EQUITY_BASE_ANNUAL)
            annual *= PRICE_PHASE_ADJ.get(price_phase.value, 1.0)
            annual = 0.55 * annual + 0.45 * hist_cagr
            annual = _blend_to_terminal(annual, terminal, m, months)
            phase_key = f"{pres.current_year.value}"
        else:
            annual = hist_cagr * PRICE_PHASE_ADJ.get(price_phase.value, 1.0)
            annual = max(-15.0, min(22.0, annual))
            annual = _blend_to_terminal(annual, terminal, m, months)
            phase_key = price_phase.value

        # Sentiment: stronger effect early years, fades toward long-run mean
        fade = max(0.15, 1.0 - m / max(months, 1) * 0.85)
        sent = 1.0 + (sentiment_mult - 1.0) * fade
        annual_b = annual * sent
        annual_o = annual * (1.0 + 0.35 * fade) * (sent if annual >= 0 else 1 / max(sent, 0.7))
        annual_p = annual * (1.0 - 0.35 * fade) * (sent if annual >= 0 else min(1.2, 1 / max(sent, 0.7)))
        # Hard caps on scenario annual returns
        annual_b = max(-40.0, min(40.0 if asset_class == "crypto" else 20.0, annual_b))
        annual_o = max(-30.0, min(55.0 if asset_class == "crypto" else 26.0, annual_o))
        annual_p = max(-50.0, min(28.0 if asset_class == "crypto" else 12.0, annual_p))

        # Cycle strategy: stay out / reduce exposure in distribution & early deep bear
        exposure = 1.0
        if strategy in ("cycle", "cycle_dca"):
            if phase_key == "distribution":
                exposure = 0.25
            elif phase_key == "bear":
                exposure = 0.55
            elif phase_key == "accumulation":
                exposure = 1.0
            else:
                exposure = 0.95

        # Apply monthly growth (only to market portion)
        if m > 0:
            for eq_name, ann in (("b", annual_b), ("o", annual_o), ("p", annual_p)):
                factor = 1 + (_monthly_factor(ann) - 1) * exposure
                if eq_name == "b":
                    equity_b *= factor
                elif eq_name == "o":
                    equity_o *= factor
                else:
                    equity_p *= factor

            # DCA contributions
            if strategy in ("dca", "cycle_dca") and monthly_contribution > 0:
                put = monthly_contribution
                if strategy == "cycle_dca" and phase_key == "distribution":
                    put = 0.0
                elif strategy == "cycle_dca" and phase_key == "bear":
                    put = monthly_contribution * 1.25  # buy more in washout
                equity_b += put
                equity_o += put
                equity_p += put
                invested_total += put

        point = {"time": ts, "equity": round(equity_b, 2), "phase": phase_key}
        base_curve.append(point)
        opt_curve.append({"time": ts, "equity": round(equity_o, 2)})
        pes_curve.append({"time": ts, "equity": round(equity_p, 2)})

        if phase_key != last_logged_phase and m % 3 == 0:
            phase_log.append(
                {
                    "time": ts,
                    "date": as_of.isoformat(),
                    "phase": phase_key,
                    "annual_expected_pct": round(annual_b, 1),
                }
            )
            last_logged_phase = phase_key

        if m > 0 and m % 12 == 0:
            y = m // 12
            milestones.append(
                {
                    "year": y,
                    "date": as_of.isoformat(),
                    "base": round(equity_b, 2),
                    "optimistic": round(equity_o, 2),
                    "pessimistic": round(equity_p, 2),
                    "roi_pct": round((equity_b - invested_total) / invested_total * 100, 1)
                    if invested_total
                    else 0,
                }
            )

    final_b = equity_b
    roi_b = ((final_b - invested_total) / invested_total * 100) if invested_total else 0.0
    cagr_b = _cagr_from_prices(invested_total, final_b, years) if invested_total > 0 else 0.0

    # Downsample curves for chart (~years*2 points is fine; keep yearly + monthly first years)
    def _down(curve: list[dict], step: int = 3) -> list[dict]:
        if len(curve) <= 200:
            return curve
        out = curve[::step]
        if out[-1] is not curve[-1]:
            out.append(curve[-1])
        return out

    return {
        "mode": "forward",
        "symbol": symbol,
        "name": meta["name"],
        "asset_class": asset_class,
        "region": region,
        "strategy": strategy,
        "amount": amount,
        "monthly_contribution": monthly_contribution,
        "invested": round(invested_total, 2),
        "final_value": round(final_b, 2),
        "final_optimistic": round(equity_o, 2),
        "final_pessimistic": round(equity_p, 2),
        "profit": round(final_b - invested_total, 2),
        "roi_pct": round(roi_b, 2),
        "cagr_pct": round(cagr_b, 2),
        "max_drawdown_pct": 0.0,
        "years": years,
        "data_start": today.isoformat(),
        "data_end": _add_months(today, months).isoformat(),
        "bars": months + 1,
        "cycle_source": cycle_source,
        "equity_curve": _down(base_curve),
        "optimistic_curve": _down(opt_curve),
        "pessimistic_curve": _down(pes_curve),
        "trades": [],
        "price_series": [],
        "btc_cycle_aths": [],
        "milestones": milestones,
        "phase_log": phase_log[:40],
        "sentiment": {
            "label": sentiment_label,
            "score": round(mom_score, 1),
            "multiplier": round(sentiment_mult, 3),
            "momentum_signal": mom_sig.value,
            "momentum_phase": mom_phase,
            "rationale": mom_rat,
        },
        "current_cycle": {
            "phase": cycle_phase,
            "days_since_ath": days_since_ath if asset_class == "crypto" else None,
            "ath_date": ath_date.isoformat() if asset_class == "crypto" else None,
            "ath_price": ath_price if asset_class == "crypto" else None,
            "price": current_price,
            "historical_cagr_pct": round(hist_cagr, 2),
            "rationale": cycle_rationale,
            "price_phase": price_phase.value,
        },
        "buy_hold": None,
        "disclaimer": (
            f"Projekcja na {years} lat od dziś. Model łączy historyczny CAGR instrumentu "
            f"({hist_cagr:.1f}%), fazy cyklu ({cycle_source}) i bieżący sentyment rynku ({sentiment_label}). "
            "Scenariusze: bazowy / optymistyczny / pesymistyczny. To nie gwarancja ani rekomendacja."
        ),
    }

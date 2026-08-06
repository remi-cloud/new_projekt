"""Trend analysis from OHLCV candles."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import ChartCandle


@dataclass
class TrendAnalysis:
    symbol: str
    direction: str  # uptrend, downtrend, sideways
    strength: float  # 0-100
    sma20: float | None
    sma50: float | None
    price_vs_sma20_pct: float | None
    rsi14: float | None
    change_7d_pct: float | None
    change_30d_pct: float | None
    structure: str  # HH/HL, LH/LL, mixed
    summary: str


def _sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _pct_change(from_p: float, to_p: float) -> float:
    if from_p == 0:
        return 0.0
    return ((to_p - from_p) / from_p) * 100


def _market_structure(closes: list[float], window: int = 5) -> str:
    if len(closes) < window * 2 + 2:
        return "mixed"
    recent = closes[-window * 2 :]
    mid = len(recent) // 2
    first_half_high = max(recent[:mid])
    second_half_high = max(recent[mid:])
    first_half_low = min(recent[:mid])
    second_half_low = min(recent[mid:])
    hh = second_half_high > first_half_high
    hl = second_half_low > first_half_low
    lh = second_half_high < first_half_high
    ll = second_half_low < first_half_low
    if hh and hl:
        return "HH/HL (uptrend structure)"
    if lh and ll:
        return "LH/LL (downtrend structure)"
    return "mixed / range"


def analyze_trend(symbol: str, candles: list[ChartCandle]) -> TrendAnalysis:
    if len(candles) < 10:
        return TrendAnalysis(
            symbol=symbol,
            direction="unknown",
            strength=0,
            sma20=None,
            sma50=None,
            price_vs_sma20_pct=None,
            rsi14=None,
            change_7d_pct=None,
            change_30d_pct=None,
            structure="insufficient data",
            summary="Za mało danych do analizy trendu.",
        )

    closes = [c.close for c in candles]
    price = closes[-1]
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, min(50, len(closes)))
    rsi = _rsi(closes, 14)
    structure = _market_structure(closes)

    ch7 = _pct_change(closes[-8], price) if len(closes) >= 8 else None
    ch30 = _pct_change(closes[-31], price) if len(closes) >= 31 else _pct_change(closes[0], price)

    direction = "sideways"
    strength = 40.0
    if sma20 and sma50:
        if price > sma20 > sma50:
            direction = "uptrend"
            strength = min(95, 55 + (price - sma50) / sma50 * 200)
        elif price < sma20 < sma50:
            direction = "downtrend"
            strength = min(95, 55 + (sma50 - price) / sma50 * 200)
        elif price > sma20:
            direction = "uptrend"
            strength = 55
        elif price < sma20:
            direction = "downtrend"
            strength = 55

    if rsi is not None:
        if rsi > 65 and direction == "uptrend":
            strength = min(95, strength + 5)
        if rsi < 35 and direction == "downtrend":
            strength = min(95, strength + 5)

    vs20 = _pct_change(sma20, price) if sma20 else None
    summary_parts = [
        f"Trend: {direction} (siła ~{strength:.0f}%)",
        f"Struktura: {structure}",
    ]
    if rsi is not None:
        summary_parts.append(f"RSI(14): {rsi:.1f}")
    if ch7 is not None:
        summary_parts.append(f"Zmiana ~7d: {ch7:+.1f}%")
    if ch30 is not None:
        summary_parts.append(f"Zmiana ~30d: {ch30:+.1f}%")

    return TrendAnalysis(
        symbol=symbol,
        direction=direction,
        strength=round(strength, 1),
        sma20=round(sma20, 4) if sma20 else None,
        sma50=round(sma50, 4) if sma50 else None,
        price_vs_sma20_pct=round(vs20, 2) if vs20 is not None else None,
        rsi14=round(rsi, 1) if rsi is not None else None,
        change_7d_pct=round(ch7, 2) if ch7 is not None else None,
        change_30d_pct=round(ch30, 2) if ch30 is not None else None,
        structure=structure,
        summary=" · ".join(summary_parts),
    )

"""Momentum analysis — RSI, ROC, MACD aligned with cyclical context."""

from app.models.schemas import SignalAction


def _ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _roc(closes: list[float], period: int = 20) -> float | None:
    if len(closes) <= period:
        return None
    base = closes[-period - 1]
    if base == 0:
        return None
    return ((closes[-1] - base) / base) * 100


def _macd(closes: list[float]) -> tuple[float | None, float | None, float | None]:
    if len(closes) < 35:
        return None, None, None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    if not ema12 or not ema26:
        return None, None, None
    offset = len(ema12) - len(ema26)
    macd_line = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
    signal_line = _ema(macd_line, 9)
    if not signal_line:
        return None, None, None
    macd_val = macd_line[-1]
    signal_val = signal_line[-1]
    histogram = macd_val - signal_val
    return macd_val, signal_val, histogram


def compute_momentum_indicators(closes: list[float]) -> dict:
    """Compute RSI, ROC, MACD and composite momentum score from daily closes."""
    rsi = _rsi(closes)
    roc = _roc(closes)
    macd, macd_signal, macd_hist = _macd(closes)

    return {
        "rsi_14": round(rsi, 1) if rsi is not None else None,
        "roc_20d": round(roc, 2) if roc is not None else None,
        "macd": round(macd, 4) if macd is not None else None,
        "macd_signal": round(macd_signal, 4) if macd_signal is not None else None,
        "macd_histogram": round(macd_hist, 4) if macd_hist is not None else None,
    }


def _momentum_score(rsi: float | None, roc: float | None, macd_hist: float | None) -> float:
    """0–100 score: high = strong upward momentum, low = strong downward."""
    score = 50.0
    if rsi is not None:
        if rsi < 30:
            if roc is not None and roc < -5:
                score += 6
            else:
                score += 22
        elif rsi < 40:
            if roc is not None and roc < -3:
                score -= 4
            else:
                score += 14
        elif rsi < 50:
            score += 8
        elif rsi <= 65:
            score += 12
        elif rsi <= 72:
            score += 4
        elif rsi <= 80:
            score -= 6
        else:
            score -= 14

    if roc is not None:
        if roc > 10:
            score += 16
        elif roc > 5:
            score += 10
        elif roc > 2:
            score += 5
        elif roc < -10:
            score -= 16
        elif roc < -5:
            score -= 10
        elif roc < -2:
            score -= 5

    if macd_hist is not None:
        if macd_hist > 0.5:
            score += min(14, macd_hist * 8)
        elif macd_hist > 0:
            score += min(8, macd_hist * 12)
        elif macd_hist < -0.5:
            score += max(-14, macd_hist * 8)
        else:
            score += max(-8, macd_hist * 12)

    return round(min(100, max(0, score)), 1)


def _momentum_phase(score: float) -> str:
    if score >= 70:
        return "silne_wzrost"
    if score >= 53:
        return "wzrost"
    if score <= 30:
        return "silne_spadk"
    if score <= 46:
        return "spadek"
    return "neutralne"


def analyze_momentum(indicators: dict) -> tuple[SignalAction, float, str, float, str]:
    """
    Derive momentum signal from indicators.
    Returns (signal, confidence, phase, momentum_score, rationale).
    """
    rsi = indicators.get("rsi_14")
    roc = indicators.get("roc_20d")
    macd_hist = indicators.get("macd_histogram")

    if rsi is None and roc is None:
        return SignalAction.WATCH, 40.0, "neutralne", 50.0, "Brak danych momentum."

    score = _momentum_score(rsi, roc, macd_hist)
    phase = _momentum_phase(score)
    parts: list[str] = []

    if rsi is not None:
        parts.append(f"RSI {rsi:.0f}")
    if roc is not None:
        parts.append(f"ROC20 {roc:+.1f}%")
    if macd_hist is not None:
        parts.append(f"MACD {'↑' if macd_hist > 0 else '↓'}")

    if score >= 70:
        signal = SignalAction.BUY
        conf = min(88, 62 + (score - 70) * 0.8)
        rationale = f"Silne momentum wzrostowe ({', '.join(parts)})."
    elif score >= 53:
        signal = SignalAction.BUY if score >= 58 else SignalAction.WATCH
        conf = 52 + (score - 53) * 1.2
        rationale = f"Momentum wzrostowe ({', '.join(parts)})."
    elif score <= 30:
        signal = SignalAction.SELL
        conf = min(88, 62 + (30 - score) * 0.8)
        rationale = f"Silne momentum spadkowe ({', '.join(parts)})."
    elif score <= 46:
        signal = SignalAction.SELL if score <= 40 else SignalAction.WATCH
        conf = 52 + (46 - score) * 1.2
        rationale = f"Momentum spadkowe ({', '.join(parts)})."
    else:
        signal = SignalAction.HOLD
        conf = 48.0
        rationale = f"Momentum neutralne ({', '.join(parts)})."

    return signal, round(conf, 1), phase, score, rationale


def momentum_aligns_with_cycle(
    momentum_signal: SignalAction,
    cycle_signal: SignalAction,
) -> bool:
    """True when momentum and cyclical signal point the same actionable direction."""
    buy_set = {SignalAction.BUY, SignalAction.WATCH}
    sell_set = {SignalAction.SELL}
    if momentum_signal == SignalAction.BUY and cycle_signal in buy_set:
        return True
    if momentum_signal == SignalAction.SELL and cycle_signal in sell_set:
        return True
    if momentum_signal == cycle_signal:
        return True
    return False

"""Price-based mini-cycle from 52-week high drawdown."""

from app.models.schemas import CyclePhase, SignalAction


def analyze_price_cycle(
    price: float,
    high_52w: float | None,
    low_52w: float | None = None,
) -> tuple[CyclePhase, SignalAction, float, str]:
    """
    Per-asset price cycle based on distance from 52-week high.
    Returns (phase, signal, confidence 0-100, rationale).
    """
    if not high_52w or high_52w <= 0 or price <= 0:
        return CyclePhase.NEUTRAL, SignalAction.WATCH, 40.0, "Brak danych o szczytach rocznych."

    drawdown_pct = ((high_52w - price) / high_52w) * 100

    if low_52w and price > 0:
        range_pct = ((price - low_52w) / (high_52w - low_52w)) * 100 if high_52w > low_52w else 50
    else:
        range_pct = 100 - drawdown_pct

    if drawdown_pct <= 3:
        phase = CyclePhase.DISTRIBUTION
        signal = SignalAction.SELL
        conf = 55 + (3 - drawdown_pct) * 5
        rationale = f"Blisko 52-tyg. ATH (spadek {drawdown_pct:.1f}%). Strefa szczytu — ostrożność."
    elif drawdown_pct <= 10:
        phase = CyclePhase.BULL
        signal = SignalAction.HOLD
        conf = 60
        rationale = f"Niedaleko szczytu (spadek {drawdown_pct:.1f}%). Trend wzrostowy, utrzymuj pozycje."
    elif drawdown_pct <= 20:
        phase = CyclePhase.ACCUMULATION
        signal = SignalAction.WATCH
        conf = 55 + (20 - drawdown_pct)
        rationale = f"Korekta {drawdown_pct:.1f}% od 52-tyg. max. Obserwuj strefę akumulacji."
    elif drawdown_pct <= 35:
        phase = CyclePhase.BEAR
        signal = SignalAction.BUY
        conf = 65 + (35 - drawdown_pct) * 0.5
        rationale = f"Głębsza korekta {drawdown_pct:.1f}% od szczytu. Historycznie strefa dokupowania."
    else:
        phase = CyclePhase.BEAR
        signal = SignalAction.BUY
        conf = min(85, 70 + (drawdown_pct - 35) * 0.3)
        rationale = f"Silny spadek {drawdown_pct:.1f}% od 52-tyg. max. Potencjalna strefa odwrócenia."

    # Position within annual range bonus
    if range_pct < 25 and signal != SignalAction.SELL:
        conf += 5

    return phase, signal, min(conf, 92), rationale

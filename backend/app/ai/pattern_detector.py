"""Classic chart pattern detection (heuristic)."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import ChartCandle


@dataclass
class PatternHit:
    name: str
    confidence: float
    description: str
    levels: dict[str, float]


@dataclass
class PatternAnalysis:
    symbol: str
    patterns: list[PatternHit]
    support_levels: list[float]
    resistance_levels: list[float]
    summary: str


def _local_extrema(closes: list[float], window: int = 3) -> tuple[list[int], list[int]]:
    peaks, troughs = [], []
    for i in range(window, len(closes) - window):
        seg = closes[i - window : i + window + 1]
        if closes[i] == max(seg):
            peaks.append(i)
        if closes[i] == min(seg):
            troughs.append(i)
    return peaks, troughs


def _cluster_levels(prices: list[float], tolerance_pct: float = 1.5) -> list[float]:
    if not prices:
        return []
    prices = sorted(prices)
    clusters: list[list[float]] = [[prices[0]]]
    for p in prices[1:]:
        if abs(p - clusters[-1][-1]) / clusters[-1][-1] * 100 <= tolerance_pct:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [round(sum(c) / len(c), 4) for c in clusters if len(c) >= 1]


def detect_patterns(symbol: str, candles: list[ChartCandle]) -> PatternAnalysis:
    if len(candles) < 20:
        return PatternAnalysis(symbol, [], [], [], "Za mało świec do rozpoznania wzorców.")

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    price = closes[-1]
    peaks, troughs = _local_extrema(closes, 3)
    patterns: list[PatternHit] = []

    resistance = _cluster_levels([highs[i] for i in peaks[-6:]]) if peaks else []
    support = _cluster_levels([lows[i] for i in troughs[-6:]]) if troughs else []

    # Double top
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        h1, h2 = highs[p1], highs[p2]
        if abs(h1 - h2) / h1 * 100 < 2.5 and p2 - p1 >= 5:
            neck = min(closes[p1:p2]) if p2 > p1 else closes[-1]
            patterns.append(
                PatternHit(
                    "double_top",
                    62.0,
                    f"Dwa zbliżone szczyty (~{h1:.2f} / {h2:.2f}). Potencjalny sygnał słabości jeśli cena spadnie poniżej ~{neck:.2f}.",
                    {"peak1": h1, "peak2": h2, "neckline": neck},
                )
            )

    # Double bottom
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        l1, l2 = lows[t1], lows[t2]
        if abs(l1 - l2) / l1 * 100 < 2.5 and t2 - t1 >= 5:
            neck = max(closes[t1:t2]) if t2 > t1 else closes[-1]
            patterns.append(
                PatternHit(
                    "double_bottom",
                    62.0,
                    f"Dwa zbliżone dołki (~{l1:.2f} / {l2:.2f}). Potencjalne odbicie jeśli cena wybije ~{neck:.2f}.",
                    {"trough1": l1, "trough2": l2, "neckline": neck},
                )
            )

    # Near support / resistance
    for r in resistance[-3:]:
        dist = (r - price) / price * 100
        if 0 < dist < 3:
            patterns.append(
                PatternHit(
                    "near_resistance",
                    55.0,
                    f"Cena ~{dist:.1f}% poniżej oporu {r:.2f} — obserwuj wybicie lub odrzucenie.",
                    {"resistance": r},
                )
            )
    for s in support[-3:]:
        dist = (price - s) / price * 100
        if 0 < dist < 3:
            patterns.append(
                PatternHit(
                    "near_support",
                    55.0,
                    f"Cena ~{dist:.1f}% powyżej wsparcia {s:.2f} — obserwuj odbicie lub przebicie.",
                    {"support": s},
                )
            )

    # Higher highs / lower lows recent
    if len(peaks) >= 3 and len(troughs) >= 3:
        recent_peaks = [highs[i] for i in peaks[-3:]]
        recent_troughs = [lows[i] for i in troughs[-3:]]
        if recent_peaks[-1] > recent_peaks[0] and recent_troughs[-1] > recent_troughs[0]:
            patterns.append(
                PatternHit(
                    "ascending_structure",
                    58.0,
                    "Seria wyższych szczytów i dołków — struktura wzrostowa.",
                    {},
                )
            )
        elif recent_peaks[-1] < recent_peaks[0] and recent_troughs[-1] < recent_troughs[0]:
            patterns.append(
                PatternHit(
                    "descending_structure",
                    58.0,
                    "Seria niższych szczytów i dołków — struktura spadkowa.",
                    {},
                )
            )

    if not patterns:
        summary = f"Brak wyraźnych klasycznych wzorców. Wsparcia: {support[-2:] or '—'}, opory: {resistance[-2:] or '—'}."
    else:
        summary = " · ".join(f"{p.name} ({p.confidence:.0f}%)" for p in patterns[:4])

    return PatternAnalysis(
        symbol=symbol,
        patterns=patterns,
        support_levels=support[-5:],
        resistance_levels=resistance[-5:],
        summary=summary,
    )

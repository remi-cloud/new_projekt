"""Classic chart pattern detection with drawable geometry (heuristic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.models.schemas import ChartCandle

LineStyle = Literal["solid", "dashed", "dotted"]


@dataclass
class ChartPoint:
    time: int
    price: float
    label: str = ""


@dataclass
class ChartLine:
    t1: int
    p1: float
    t2: int
    p2: float
    style: LineStyle = "solid"
    label: str = ""


@dataclass
class PatternHit:
    name: str
    confidence: float
    description: str
    levels: dict[str, float]
    kind: str = "pattern"
    points: list[ChartPoint] = field(default_factory=list)
    lines: list[ChartLine] = field(default_factory=list)


@dataclass
class PatternAnalysis:
    symbol: str
    patterns: list[PatternHit]
    support_levels: list[float]
    resistance_levels: list[float]
    summary: str

    def to_geometry(self) -> dict[str, Any]:
        return {
            "patterns": [
                {
                    "name": p.name,
                    "kind": p.kind,
                    "confidence": p.confidence,
                    "description": p.description,
                    "levels": p.levels,
                    "points": [
                        {"time": pt.time, "price": pt.price, "label": pt.label} for pt in p.points
                    ],
                    "lines": [
                        {
                            "t1": ln.t1,
                            "p1": ln.p1,
                            "t2": ln.t2,
                            "p2": ln.p2,
                            "style": ln.style,
                            "label": ln.label,
                        }
                        for ln in p.lines
                    ],
                }
                for p in self.patterns
            ],
            "support": self.support_levels,
            "resistance": self.resistance_levels,
        }


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


def _t(candles: list[ChartCandle], i: int) -> int:
    return int(candles[i].time)


def _linreg(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    intercept = my - slope * mx
    return slope, intercept


def _candlestick_flags(candles: list[ChartCandle]) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if len(candles) < 2:
        return hits
    c0, c1 = candles[-2], candles[-1]
    body1 = abs(c1.close - c1.open)
    range1 = max(c1.high - c1.low, 1e-12)
    if body1 / range1 < 0.12:
        hits.append(
            PatternHit(
                name="doji",
                confidence=52.0,
                description="Ostatnia świeca doji — równowaga; czekaj na potwierdzenie.",
                levels={"open": c1.open, "close": c1.close},
                kind="candle",
                points=[ChartPoint(_t(candles, -1), c1.close, "doji")],
            )
        )
    if (
        c0.close < c0.open
        and c1.close > c1.open
        and c1.open <= c0.close
        and c1.close >= c0.open
        and body1 > abs(c0.close - c0.open) * 1.05
    ):
        hits.append(
            PatternHit(
                name="bullish_engulfing",
                confidence=60.0,
                description="Bullish engulfing — świeca wzrostowa obejmuje poprzednią spadkową.",
                levels={"low": c1.low, "high": c1.high},
                kind="candle",
                points=[
                    ChartPoint(_t(candles, -2), c0.close, "prev"),
                    ChartPoint(_t(candles, -1), c1.close, "engulf"),
                ],
                lines=[
                    ChartLine(_t(candles, -2), c0.low, _t(candles, -1), c1.high, "dashed", "engulf")
                ],
            )
        )
    if (
        c0.close > c0.open
        and c1.close < c1.open
        and c1.open >= c0.close
        and c1.close <= c0.open
        and body1 > abs(c0.close - c0.open) * 1.05
    ):
        hits.append(
            PatternHit(
                name="bearish_engulfing",
                confidence=60.0,
                description="Bearish engulfing — świeca spadkowa obejmuje poprzednią wzrostową.",
                levels={"low": c1.low, "high": c1.high},
                kind="candle",
                points=[
                    ChartPoint(_t(candles, -2), c0.close, "prev"),
                    ChartPoint(_t(candles, -1), c1.close, "engulf"),
                ],
                lines=[
                    ChartLine(_t(candles, -2), c0.high, _t(candles, -1), c1.low, "dashed", "engulf")
                ],
            )
        )
    return hits


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
    t_start, t_end = _t(candles, 0), _t(candles, -1)

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        h1, h2 = highs[p1], highs[p2]
        if abs(h1 - h2) / h1 * 100 < 2.5 and p2 - p1 >= 5:
            neck = min(closes[p1:p2]) if p2 > p1 else closes[-1]
            patterns.append(
                PatternHit(
                    "double_top",
                    62.0,
                    f"Dwa zbliżone szczyty (~{h1:.2f} / {h2:.2f}). Słabość poniżej ~{neck:.2f}.",
                    {"peak1": h1, "peak2": h2, "neckline": neck},
                    kind="reversal",
                    points=[
                        ChartPoint(_t(candles, p1), h1, "P1"),
                        ChartPoint(_t(candles, p2), h2, "P2"),
                    ],
                    lines=[
                        ChartLine(_t(candles, p1), neck, _t(candles, p2), neck, "dashed", "neck"),
                        ChartLine(_t(candles, p1), h1, _t(candles, p2), h2, "solid", "tops"),
                    ],
                )
            )

    if len(troughs) >= 2:
        t1i, t2i = troughs[-2], troughs[-1]
        l1, l2 = lows[t1i], lows[t2i]
        if abs(l1 - l2) / l1 * 100 < 2.5 and t2i - t1i >= 5:
            neck = max(closes[t1i:t2i]) if t2i > t1i else closes[-1]
            patterns.append(
                PatternHit(
                    "double_bottom",
                    62.0,
                    f"Dwa zbliżone dołki (~{l1:.2f} / {l2:.2f}). Odbicie powyżej ~{neck:.2f}.",
                    {"trough1": l1, "trough2": l2, "neckline": neck},
                    kind="reversal",
                    points=[
                        ChartPoint(_t(candles, t1i), l1, "T1"),
                        ChartPoint(_t(candles, t2i), l2, "T2"),
                    ],
                    lines=[
                        ChartLine(_t(candles, t1i), neck, _t(candles, t2i), neck, "dashed", "neck"),
                        ChartLine(_t(candles, t1i), l1, _t(candles, t2i), l2, "solid", "bottoms"),
                    ],
                )
            )

    if len(peaks) >= 3:
        i_l, i_h, i_r = peaks[-3], peaks[-2], peaks[-1]
        hl, hh, hr = highs[i_l], highs[i_h], highs[i_r]
        if hh > hl and hh > hr and abs(hl - hr) / max(hl, 1e-12) * 100 < 3.5 and i_r - i_l >= 8:
            neck = min(closes[i_l:i_r])
            patterns.append(
                PatternHit(
                    "head_and_shoulders",
                    64.0,
                    f"Head & shoulders (~{hl:.2f}/{hh:.2f}/{hr:.2f}). Szyja ~{neck:.2f}.",
                    {"left": hl, "head": hh, "right": hr, "neckline": neck},
                    kind="reversal",
                    points=[
                        ChartPoint(_t(candles, i_l), hl, "LS"),
                        ChartPoint(_t(candles, i_h), hh, "H"),
                        ChartPoint(_t(candles, i_r), hr, "RS"),
                    ],
                    lines=[
                        ChartLine(_t(candles, i_l), hl, _t(candles, i_h), hh, "solid", "hs"),
                        ChartLine(_t(candles, i_h), hh, _t(candles, i_r), hr, "solid", "hs"),
                        ChartLine(_t(candles, i_l), neck, _t(candles, i_r), neck, "dashed", "neck"),
                    ],
                )
            )

    if len(peaks) >= 3 and len(troughs) >= 3:
        rp = peaks[-3:]
        rt = troughs[-3:]
        peak_vals = [highs[i] for i in rp]
        trough_vals = [lows[i] for i in rt]
        peak_flat = (max(peak_vals) - min(peak_vals)) / max(peak_vals) * 100 < 1.8
        trough_rising = trough_vals[-1] > trough_vals[0] * 1.008
        trough_flat = (max(trough_vals) - min(trough_vals)) / max(trough_vals) * 100 < 1.8
        peak_falling = peak_vals[-1] < peak_vals[0] * 0.992
        if peak_flat and trough_rising:
            res = sum(peak_vals) / 3
            patterns.append(
                PatternHit(
                    "ascending_triangle",
                    61.0,
                    f"Trójkąt wzrostowy — płaski opór ~{res:.2f}, rosnące dołki.",
                    {"resistance": res, "support_last": trough_vals[-1]},
                    kind="continuation",
                    points=[
                        ChartPoint(_t(candles, rp[0]), peak_vals[0], "R"),
                        ChartPoint(_t(candles, rt[0]), trough_vals[0], "S0"),
                        ChartPoint(_t(candles, rt[-1]), trough_vals[-1], "S1"),
                    ],
                    lines=[
                        ChartLine(_t(candles, rp[0]), res, _t(candles, rp[-1]), res, "solid", "res"),
                        ChartLine(
                            _t(candles, rt[0]),
                            trough_vals[0],
                            _t(candles, rt[-1]),
                            trough_vals[-1],
                            "solid",
                            "sup",
                        ),
                    ],
                )
            )
        elif trough_flat and peak_falling:
            sup = sum(trough_vals) / 3
            patterns.append(
                PatternHit(
                    "descending_triangle",
                    61.0,
                    f"Trójkąt spadkowy — płaskie wsparcie ~{sup:.2f}, spadające szczyty.",
                    {"support": sup, "resistance_last": peak_vals[-1]},
                    kind="continuation",
                    points=[
                        ChartPoint(_t(candles, rt[0]), trough_vals[0], "S"),
                        ChartPoint(_t(candles, rp[0]), peak_vals[0], "R0"),
                        ChartPoint(_t(candles, rp[-1]), peak_vals[-1], "R1"),
                    ],
                    lines=[
                        ChartLine(_t(candles, rt[0]), sup, _t(candles, rt[-1]), sup, "solid", "sup"),
                        ChartLine(
                            _t(candles, rp[0]),
                            peak_vals[0],
                            _t(candles, rp[-1]),
                            peak_vals[-1],
                            "solid",
                            "res",
                        ),
                    ],
                )
            )

    if len(troughs) >= 3:
        idx = troughs[-4:]
        fit = _linreg([float(i) for i in idx], [lows[i] for i in idx])
        if fit and fit[0] > 0:
            slope, intercept = fit
            i0, i1 = idx[0], idx[-1]
            p0, p1 = intercept + slope * i0, intercept + slope * i1
            patterns.append(
                PatternHit(
                    "uptrend_line",
                    57.0,
                    f"Linia trendu wzrostowego (~{p0:.2f} → ~{p1:.2f}).",
                    {"start": p0, "end": p1},
                    kind="trend",
                    points=[
                        ChartPoint(_t(candles, i0), lows[i0], "TL"),
                        ChartPoint(_t(candles, i1), lows[i1], "TL"),
                    ],
                    lines=[ChartLine(_t(candles, i0), p0, _t(candles, i1), p1, "solid", "uptrend")],
                )
            )
    if len(peaks) >= 3:
        idx = peaks[-4:]
        fit = _linreg([float(i) for i in idx], [highs[i] for i in idx])
        if fit and fit[0] < 0:
            slope, intercept = fit
            i0, i1 = idx[0], idx[-1]
            p0, p1 = intercept + slope * i0, intercept + slope * i1
            patterns.append(
                PatternHit(
                    "downtrend_line",
                    57.0,
                    f"Linia trendu spadkowego (~{p0:.2f} → ~{p1:.2f}).",
                    {"start": p0, "end": p1},
                    kind="trend",
                    points=[
                        ChartPoint(_t(candles, i0), highs[i0], "TL"),
                        ChartPoint(_t(candles, i1), highs[i1], "TL"),
                    ],
                    lines=[ChartLine(_t(candles, i0), p0, _t(candles, i1), p1, "solid", "downtrend")],
                )
            )

    for r in resistance[-3:]:
        dist = (r - price) / price * 100
        if 0 < dist < 3:
            patterns.append(
                PatternHit(
                    "near_resistance",
                    55.0,
                    f"Cena ~{dist:.1f}% poniżej oporu {r:.2f}.",
                    {"resistance": r},
                    kind="level",
                    lines=[ChartLine(t_start, r, t_end, r, "dashed", "R")],
                )
            )
    for s in support[-3:]:
        dist = (price - s) / price * 100
        if 0 < dist < 3:
            patterns.append(
                PatternHit(
                    "near_support",
                    55.0,
                    f"Cena ~{dist:.1f}% powyżej wsparcia {s:.2f}.",
                    {"support": s},
                    kind="level",
                    lines=[ChartLine(t_start, s, t_end, s, "dashed", "S")],
                )
            )

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
                    kind="structure",
                    points=[
                        ChartPoint(_t(candles, peaks[-3]), recent_peaks[0], "HH0"),
                        ChartPoint(_t(candles, peaks[-1]), recent_peaks[-1], "HH1"),
                        ChartPoint(_t(candles, troughs[-3]), recent_troughs[0], "HL0"),
                        ChartPoint(_t(candles, troughs[-1]), recent_troughs[-1], "HL1"),
                    ],
                    lines=[
                        ChartLine(
                            _t(candles, peaks[-3]),
                            recent_peaks[0],
                            _t(candles, peaks[-1]),
                            recent_peaks[-1],
                            "dotted",
                            "HH",
                        ),
                        ChartLine(
                            _t(candles, troughs[-3]),
                            recent_troughs[0],
                            _t(candles, troughs[-1]),
                            recent_troughs[-1],
                            "dotted",
                            "HL",
                        ),
                    ],
                )
            )
        elif recent_peaks[-1] < recent_peaks[0] and recent_troughs[-1] < recent_troughs[0]:
            patterns.append(
                PatternHit(
                    "descending_structure",
                    58.0,
                    "Seria niższych szczytów i dołków — struktura spadkowa.",
                    {},
                    kind="structure",
                    points=[
                        ChartPoint(_t(candles, peaks[-3]), recent_peaks[0], "LH0"),
                        ChartPoint(_t(candles, peaks[-1]), recent_peaks[-1], "LH1"),
                        ChartPoint(_t(candles, troughs[-3]), recent_troughs[0], "LL0"),
                        ChartPoint(_t(candles, troughs[-1]), recent_troughs[-1], "LL1"),
                    ],
                    lines=[
                        ChartLine(
                            _t(candles, peaks[-3]),
                            recent_peaks[0],
                            _t(candles, peaks[-1]),
                            recent_peaks[-1],
                            "dotted",
                            "LH",
                        ),
                        ChartLine(
                            _t(candles, troughs[-3]),
                            recent_troughs[0],
                            _t(candles, troughs[-1]),
                            recent_troughs[-1],
                            "dotted",
                            "LL",
                        ),
                    ],
                )
            )

    patterns.extend(_candlestick_flags(candles))

    for s in support[-3:]:
        if not any(
            p.name in {"near_support", "support_level"} and abs(p.levels.get("support", 0) - s) < 1e-9
            for p in patterns
        ):
            patterns.append(
                PatternHit(
                    "support_level",
                    40.0,
                    f"Poziom wsparcia ~{s:.2f}.",
                    {"support": s},
                    kind="level",
                    lines=[ChartLine(t_start, s, t_end, s, "dotted", "S")],
                )
            )
    for r in resistance[-3:]:
        if not any(
            p.name in {"near_resistance", "resistance_level"}
            and abs(p.levels.get("resistance", 0) - r) < 1e-9
            for p in patterns
        ):
            patterns.append(
                PatternHit(
                    "resistance_level",
                    40.0,
                    f"Poziom oporu ~{r:.2f}.",
                    {"resistance": r},
                    kind="level",
                    lines=[ChartLine(t_start, r, t_end, r, "dotted", "R")],
                )
            )

    notable = [p for p in patterns if p.kind != "level" or p.name.startswith("near_")]
    if not notable:
        summary = (
            f"Brak wyraźnych klasycznych wzorców. "
            f"Wsparcia: {support[-2:] or '—'}, opory: {resistance[-2:] or '—'}."
        )
    else:
        summary = " · ".join(f"{p.name} ({p.confidence:.0f}%)" for p in notable[:4])

    return PatternAnalysis(
        symbol=symbol,
        patterns=patterns,
        support_levels=support[-5:],
        resistance_levels=resistance[-5:],
        summary=summary,
    )

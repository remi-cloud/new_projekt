"""Render OHLC + pattern overlays as compact SVG (no external deps)."""

from __future__ import annotations

import html
from typing import Sequence

from app.ai.pattern_detector import PatternAnalysis
from app.models.schemas import ChartCandle

W = 720
H = 320
PAD_L, PAD_R, PAD_T, PAD_B = 48, 16, 28, 28


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_pattern_svg(
    symbol: str,
    candles: Sequence[ChartCandle],
    analysis: PatternAnalysis,
    *,
    max_bars: int = 80,
) -> str:
    if not candles:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">'
            f'<text x="24" y="40" fill="#94a3b8">Brak świec</text></svg>'
        )

    bars = list(candles[-max_bars:])
    n = len(bars)
    times = [int(c.time) for c in bars]
    t0, t1 = times[0], times[-1]
    lo = min(c.low for c in bars)
    hi = max(c.high for c in bars)
    # Expand range to fit overlay levels
    for p in analysis.patterns:
        for ln in p.lines:
            lo = min(lo, ln.p1, ln.p2)
            hi = max(hi, ln.p1, ln.p2)
        for pt in p.points:
            lo = min(lo, pt.price)
            hi = max(hi, pt.price)
    for lvl in analysis.support_levels + analysis.resistance_levels:
        lo = min(lo, lvl)
        hi = max(hi, lvl)
    pad = (hi - lo) * 0.06 or 1.0
    lo -= pad
    hi += pad
    span = hi - lo or 1.0

    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def x_at_time(t: int) -> float:
        if t1 == t0:
            return PAD_L + plot_w / 2
        # clamp to plot
        tt = min(max(t, t0), t1)
        return PAD_L + (tt - t0) / (t1 - t0) * plot_w

    def x_at_idx(i: int) -> float:
        if n <= 1:
            return PAD_L + plot_w / 2
        return PAD_L + i / (n - 1) * plot_w

    def y_at(price: float) -> float:
        return PAD_T + (hi - price) / span * plot_h

    from app.data.assets import display_symbol_label

    title = display_symbol_label(symbol)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{_esc(title)} patterns">',
        f'<rect width="{W}" height="{H}" fill="#0f1115"/>',
        f'<text x="{PAD_L}" y="18" fill="#e2e8f0" font-size="12" '
        f'font-family="ui-sans-serif,system-ui">{_esc(title)} · patterns</text>',
        f'<text x="{W - PAD_R}" y="18" text-anchor="end" fill="#64748b" font-size="11" '
        f'font-family="ui-monospace,monospace">{_esc(analysis.summary[:72])}</text>',
    ]

    # Grid
    for k in range(5):
        yy = PAD_T + plot_h * k / 4
        price = hi - span * k / 4
        parts.append(
            f'<line x1="{PAD_L}" y1="{yy:.1f}" x2="{W - PAD_R}" y2="{yy:.1f}" '
            f'stroke="#1e293b" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{PAD_L - 6}" y="{yy + 3:.1f}" text-anchor="end" fill="#64748b" '
            f'font-size="9" font-family="ui-monospace,monospace">{price:.4g}</text>'
        )

    # Candles
    candle_w = max(2.0, plot_w / max(n, 1) * 0.55)
    for i, c in enumerate(bars):
        x = x_at_idx(i)
        up = c.close >= c.open
        color = "#22c55e" if up else "#f97316"
        y_h, y_l = y_at(c.high), y_at(c.low)
        y_o, y_c = y_at(c.open), y_at(c.close)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_h:.1f}" x2="{x:.1f}" y2="{y_l:.1f}" '
            f'stroke="{color}" stroke-width="1"/>'
        )
        top, bot = min(y_o, y_c), max(y_o, y_c)
        bh = max(1.0, bot - top)
        parts.append(
            f'<rect x="{x - candle_w / 2:.1f}" y="{top:.1f}" width="{candle_w:.1f}" '
            f'height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
        )

    # Overlay lines from patterns (prefer notable first, cap count)
    draw_patterns = sorted(
        analysis.patterns,
        key=lambda p: (0 if p.kind != "level" else 1, -p.confidence),
    )[:12]
    style_dash = {"solid": "", "dashed": "6 4", "dotted": "2 3"}
    colors = {
        "reversal": "#f472b6",
        "continuation": "#38bdf8",
        "trend": "#a78bfa",
        "structure": "#fbbf24",
        "level": "#94a3b8",
        "candle": "#2dd4bf",
        "pattern": "#e2e8f0",
    }
    for p in draw_patterns:
        col = colors.get(p.kind, "#e2e8f0")
        for ln in p.lines:
            x1, y1 = x_at_time(ln.t1), y_at(ln.p1)
            x2, y2 = x_at_time(ln.t2), y_at(ln.p2)
            dash = style_dash.get(ln.style, "")
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{col}" stroke-width="1.6"{dash_attr} opacity="0.9"/>'
            )
        for pt in p.points:
            if pt.time < t0 or pt.time > t1:
                continue
            cx, cy = x_at_time(pt.time), y_at(pt.price)
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{col}" '
                f'stroke="#0f1115" stroke-width="1"/>'
            )
            if pt.label:
                parts.append(
                    f'<text x="{cx + 5:.1f}" y="{cy - 5:.1f}" fill="{col}" font-size="9" '
                    f'font-family="ui-sans-serif,system-ui">{_esc(pt.label)}</text>'
                )

    parts.append("</svg>")
    return "".join(parts)

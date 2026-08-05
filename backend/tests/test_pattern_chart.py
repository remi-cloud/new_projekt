"""Pattern detector geometry + SVG renderer."""

from __future__ import annotations

from app.ai.pattern_chart_svg import render_pattern_svg
from app.ai.pattern_detector import detect_patterns
from app.models.schemas import ChartCandle


def _synth_double_top(n: int = 60) -> list[ChartCandle]:
    """Synthetic series with two similar peaks and S/R structure."""
    candles: list[ChartCandle] = []
    t0 = 1_700_000_000
    for i in range(n):
        # Rise to peak ~40, dip, second peak ~40, then fade
        if i < 20:
            c = 30 + i * 0.5
        elif i < 30:
            c = 40 - (i - 20) * 0.6
        elif i < 45:
            c = 34 + (i - 30) * 0.4
        else:
            c = 40 - (i - 45) * 0.5
        hi = c + 0.4
        lo = c - 0.4
        o = c - 0.1
        candles.append(
            ChartCandle(
                time=t0 + i * 86_400,
                open=o,
                high=hi,
                low=lo,
                close=c,
                volume=1000.0,
            )
        )
    return candles


def test_detect_patterns_geometry_has_times():
    candles = _synth_double_top()
    pa = detect_patterns("TEST-USD", candles)
    geom = pa.to_geometry()
    assert "patterns" in geom
    assert "support" in geom
    assert "resistance" in geom
    # At least support/resistance level hits or a named pattern with times
    timed = False
    for p in geom["patterns"]:
        for pt in p.get("points") or []:
            assert isinstance(pt["time"], int)
            assert pt["time"] > 0
            timed = True
        for ln in p.get("lines") or []:
            assert isinstance(ln["t1"], int)
            assert isinstance(ln["t2"], int)
            timed = True
    assert timed or pa.support_levels or pa.resistance_levels


def test_render_pattern_svg_contains_svg_and_lines():
    candles = _synth_double_top()
    pa = detect_patterns("TEST-USD", candles)
    svg = render_pattern_svg("TEST-USD", candles, pa)
    assert "<svg" in svg
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "TEST-USD" in svg
    # candles or overlays produce line/rect elements
    assert "<line" in svg or "<rect" in svg

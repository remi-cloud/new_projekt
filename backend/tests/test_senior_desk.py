"""Senior desk: focus symbol, shared OHLC desk, MTF/risk tools."""

from __future__ import annotations

import pytest

from app.ai.pattern_chart_svg import render_pattern_svg
from app.ai.tools import (
    build_desk_tool_bundle,
    load_pattern_desk,
    resolve_focus_symbol,
    run_tool,
)
from app.models.schemas import ChartCandle


def test_resolve_focus_symbol_explicit_wins():
    assert resolve_focus_symbol("Co z AAPL?", "BTC-USD") == "BTC-USD"
    assert resolve_focus_symbol("trend na eth", None) == "ETH-USD"
    assert resolve_focus_symbol("ethereum setup", None) == "ETH-USD"
    # Explicit never replaced by text extraction (LQD vs AVAX/ADA in prompt)
    assert resolve_focus_symbol("Full analysis of Avalanche AVAX-USD", "LQD") == "LQD"
    assert resolve_focus_symbol("trend on bitcoin", "SPCX") == "SPCX"
    assert resolve_focus_symbol("spacex analysis", None) == "SPCX"
    assert resolve_focus_symbol("Full analysis", "SPACEX") == "SPCX"
    # Typo LIQ → LQD (iShares IG bond ETF)
    assert resolve_focus_symbol("Full analysis of LIQ", "LIQ") == "LQD"
    assert resolve_focus_symbol("liq chart", None) == "LQD"
    # Stopword "on" must not resolve to ON Semiconductor
    assert resolve_focus_symbol("trend on LQD", None) == "LQD"


def _synth(n: int = 50) -> list[ChartCandle]:
    t0 = 1_700_000_000
    out: list[ChartCandle] = []
    for i in range(n):
        c = 100 + i * 0.2
        out.append(
            ChartCandle(
                time=t0 + i * 86_400,
                open=c - 0.1,
                high=c + 0.5,
                low=c - 0.5,
                close=c,
                volume=1_000,
            )
        )
    return out


@pytest.mark.asyncio
async def test_load_pattern_desk_shared_candles(monkeypatch):
    candles = _synth()

    class FakeChart:
        def __init__(self):
            self.candles = candles

    async def fake_fetch(symbol, preset="3M"):
        return FakeChart()

    monkeypatch.setattr("app.ai.tools.fetch_chart", fake_fetch)
    desk = await load_pattern_desk("TEST-USD", "3M")
    assert desk["error"] is None
    assert desk["analysis"] is not None
    assert len(desk["candles"]) == len(candles)
    svg = render_pattern_svg("TEST-USD", desk["candles"], desk["analysis"])
    assert "<svg" in svg
    assert "TEST-USD" in svg


@pytest.mark.asyncio
async def test_desk_bundle_has_render_for_focus(monkeypatch):
    candles = _synth(60)

    class FakeChart:
        def __init__(self):
            self.candles = candles

    async def fake_fetch(symbol, preset="3M"):
        return FakeChart()

    async def fake_run(name, args):
        if name == "get_market_context":
            return {"symbol": args.get("symbol"), "signal": "watch", "confidence": 50, "rationale": "t"}
        if name == "analyze_multi_timeframe":
            return {"symbol": args.get("symbol"), "bias": "neutral", "confluence_score": 0, "frames": []}
        if name == "risk_snapshot":
            return {"symbol": args.get("symbol"), "summary": "risk ok"}
        if name == "get_macro_cycles":
            return {"bitcoin": {}, "presidential": {}}
        return {"error": "unexpected"}

    monkeypatch.setattr("app.ai.tools.fetch_chart", fake_fetch)
    monkeypatch.setattr("app.ai.tools.run_tool", fake_run)

    bundle = await build_desk_tool_bundle("BTC-USD")
    tools = [b["tool"] for b in bundle]
    assert "analyze_trend" in tools
    assert "detect_patterns" in tools
    assert "render_pattern_chart" in tools
    svg_block = next(b for b in bundle if b["tool"] == "render_pattern_chart")
    assert svg_block["result"]["symbol"] == "BTC-USD"
    assert "<svg" in svg_block["result"]["svg"]


@pytest.mark.asyncio
async def test_analyze_multi_timeframe_tool(monkeypatch):
    candles = _synth(80)

    class FakeChart:
        def __init__(self):
            self.candles = candles

    async def fake_fetch(symbol, preset="3M"):
        return FakeChart()

    monkeypatch.setattr("app.ai.tools.fetch_chart", fake_fetch)
    res = await run_tool("analyze_multi_timeframe", {"symbol": "BTC-USD"})
    assert res.get("symbol") == "BTC-USD"
    assert "bias" in res
    assert "frames" in res

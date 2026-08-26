"""desk_ui compact payload for agent visual desk."""

from app.ai.agent import build_desk_ui


def test_build_desk_ui_from_tool_results():
    tools = [
        {
            "tool": "analyze_trend",
            "result": {
                "symbol": "BTC-USD",
                "trend": "uptrend",
                "strength": 72,
                "summary": "Uptrend structure",
            },
        },
        {
            "tool": "detect_patterns",
            "result": {
                "symbol": "BTC-USD",
                "support": [60000.0, 62000.0],
                "resistance": [70000.0],
                "patterns": [{"name": "double_bottom", "confidence": 62, "kind": "reversal"}],
                "summary": "Double bottom",
            },
        },
        {
            "tool": "analyze_multi_timeframe",
            "result": {
                "symbol": "BTC-USD",
                "bias": "bullish",
                "confluence_score": 66,
                "frames": [{"range": "3M", "trend": "uptrend", "strength": 70}],
            },
        },
        {
            "tool": "risk_snapshot",
            "result": {
                "symbol": "BTC-USD",
                "summary": "ATR stop",
                "suggested_stop_price": 58000,
                "reward_risk": 2.1,
            },
        },
        {
            "tool": "render_pattern_chart",
            "result": {"symbol": "BTC-USD", "svg": "<svg xmlns='x'></svg>"},
        },
    ]
    ui = build_desk_ui("BTC-USD", tools)
    assert ui is not None
    assert ui["symbol"] == "BTC-USD"
    assert ui["bias"] == "bull"
    assert ui["support"][0] == 60000.0
    assert ui["patterns"][0]["name"] == "double_bottom"
    assert ui["has_svg"] is True
    assert ui["risk"]["reward_risk"] == 2.1
    assert "svg" not in ui


def test_build_desk_ui_none_without_focus():
    assert build_desk_ui(None, []) is None


def test_build_desk_ui_ignores_foreign_symbol_tools():
    tools = [
        {
            "tool": "analyze_trend",
            "result": {"symbol": "AVAX-USD", "trend": "uptrend", "strength": 88},
        },
        {
            "tool": "detect_patterns",
            "result": {
                "symbol": "LQD",
                "support": [100.0],
                "resistance": [110.0],
                "patterns": [{"name": "range", "confidence": 50, "kind": "continuation"}],
            },
        },
    ]
    ui = build_desk_ui("LQD", tools)
    assert ui is not None
    assert ui["symbol"] == "LQD"
    assert ui["support"] == [100.0]
    # Must not latch AVAX trend into LQD desk
    assert ui.get("bias") in ("neutral", "bull", "bear")
    assert ui.get("conviction") != 88

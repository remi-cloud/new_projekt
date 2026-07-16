"""Agent tools — market data, trend, patterns, cycles, knowledge."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai import db as ai_db
from app.ai.pattern_detector import detect_patterns
from app.ai.trend_analyzer import analyze_trend
from app.data.chart_data import fetch_chart
from app.data.assets import MONITORED_ASSETS
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

SYMBOL_ALIASES = {
    "btc": "BTC-USD",
    "bitcoin": "BTC-USD",
    "eth": "ETH-USD",
    "ethereum": "ETH-USD",
    "sol": "SOL-USD",
    "sp500": "^GSPC",
    "s&p": "^GSPC",
    "nasdaq": "^IXIC",
    "dax": "^GDAXI",
    "wig20": "WIG20.WA",
    "gold": "GC=F",
    "oil": "CL=F",
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_trend",
            "description": "Analyze price trend, RSI, SMA structure for a symbol",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}, "range": {"type": "string", "default": "3M"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_patterns",
            "description": "Detect chart patterns, support and resistance for a symbol",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}, "range": {"type": "string", "default": "3M"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_context",
            "description": "Get cyclical assessment, signal and rationale for a symbol from our scanner",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search internal finance knowledge base (cycles, macro, patterns, risk)",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_roi_backtest",
            "description": "Run historical ROI backtest with our cycle strategy vs buy and hold",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "amount": {"type": "number", "default": 10000},
                    "years": {"type": "integer", "default": 10},
                    "strategy": {
                        "type": "string",
                        "enum": ["buy_hold", "cycle", "dca", "cycle_dca"],
                        "default": "cycle",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
]


def normalize_symbol(raw: str) -> str | None:
    s = raw.strip().upper().replace(" ", "")
    if s in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[s.lower()]
    low = raw.strip().lower()
    if low in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[low]
    known = {a["symbol"].upper() for a in MONITORED_ASSETS}
    if s in known:
        return s
    if s.endswith("-USD") and s in known:
        return s
    for sym in known:
        if sym.replace("-USD", "") == s.replace("-USD", ""):
            return sym
    return None


def extract_symbol_from_text(text: str) -> str | None:
    for word in re.findall(r"[A-Za-z0-9^./-]+", text):
        sym = normalize_symbol(word)
        if sym:
            return sym
    low = text.lower()
    for alias, sym in SYMBOL_ALIASES.items():
        if alias in low:
            return sym
    return None


async def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "analyze_trend":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            chart = await fetch_chart(symbol, arguments.get("range", "3M"))
            trend = analyze_trend(symbol, chart.candles)
            return {
                "symbol": symbol,
                "trend": trend.direction,
                "strength": trend.strength,
                "rsi14": trend.rsi14,
                "structure": trend.structure,
                "change_7d_pct": trend.change_7d_pct,
                "change_30d_pct": trend.change_30d_pct,
                "summary": trend.summary,
            }
        if name == "detect_patterns":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            chart = await fetch_chart(symbol, arguments.get("range", "3M"))
            pa = detect_patterns(symbol, chart.candles)
            return {
                "symbol": symbol,
                "patterns": [{"name": p.name, "confidence": p.confidence, "description": p.description} for p in pa.patterns],
                "support": pa.support_levels,
                "resistance": pa.resistance_levels,
                "summary": pa.summary,
            }
        if name == "get_market_context":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            if not scanner.market_assessments:
                await scanner.scan()
            for a in scanner.market_assessments:
                if a.symbol.upper() == symbol.upper():
                    return {
                        "symbol": a.symbol,
                        "signal": a.signal.value,
                        "confidence": a.confidence,
                        "macro_phase": a.macro_phase,
                        "price_phase": a.price_phase,
                        "macro_cycle": a.macro_cycle,
                        "rationale": a.rationale,
                        "momentum_pick": a.is_momentum_pick,
                    }
            return {"error": f"No assessment for {symbol}"}
        if name == "search_knowledge":
            hits = await ai_db.search_knowledge(arguments.get("query", ""), limit=5)
            notes = await ai_db.get_learning_notes(limit=3)
            return {"knowledge": hits, "lessons_learned": notes}
        if name == "get_macro_cycles":
            if not scanner.bitcoin_cycle:
                await scanner.scan()
            btc = scanner.bitcoin_cycle
            pres = scanner.presidential_cycle
            return {
                "bitcoin": {
                    "phase": btc.phase.value if btc else None,
                    "signal": btc.signal.value if btc else None,
                    "rationale": btc.rationale if btc else None,
                },
                "presidential": {
                    "president": pres.president if pres else None,
                    "year": pres.current_year.value if pres else None,
                    "signal": pres.signal.value if pres else None,
                    "rationale": pres.rationale if pres else None,
                },
            }
        if name == "run_roi_backtest":
            from datetime import date, timedelta

            from app.roi.calculator import calculate_roi

            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            amount = float(arguments.get("amount", 10000))
            years = int(arguments.get("years", 10))
            strategy = arguments.get("strategy", "cycle")
            end = date.today()
            start = end - timedelta(days=int(years * 365.25))
            result = await calculate_roi(
                symbol=symbol,
                amount=amount,
                strategy=strategy,
                start=start,
                end=end,
                compare_buy_hold=True,
            )
            return {
                "symbol": result["symbol"],
                "name": result["name"],
                "strategy": result["strategy"],
                "amount": result["amount"],
                "final_value": result["final_value"],
                "profit": result["profit"],
                "roi_pct": result["roi_pct"],
                "cagr_pct": result["cagr_pct"],
                "years": result["years"],
                "buy_hold": result.get("buy_hold"),
                "data_start": result.get("data_start"),
                "data_end": result.get("data_end"),
            }
        return {"error": f"Unknown tool {name}"}
    except Exception as exc:
        logger.exception("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}


async def auto_tools_for_question(question: str) -> list[dict[str, Any]]:
    """Run relevant tools without LLM (fallback / enrichment)."""
    results: list[dict] = []
    sym = extract_symbol_from_text(question)
    low = question.lower()

    if sym:
        results.append({"tool": "analyze_trend", "result": await run_tool("analyze_trend", {"symbol": sym})})
        if any(k in low for k in ("wzor", "pattern", "formac", "support", "opór", "resist")):
            results.append({"tool": "detect_patterns", "result": await run_tool("detect_patterns", {"symbol": sym})})
        results.append({"tool": "get_market_context", "result": await run_tool("get_market_context", {"symbol": sym})})

    if any(k in low for k in ("cykl", "cycle", "bitcoin", "btc", "prezyden", "president", "fed", "makro")):
        results.append({"tool": "get_macro_cycles", "result": await run_tool("get_macro_cycles", {})})

    if any(k in low for k in ("roi", "backtest", "rentown", "cagr", "zysk", "profit", "inwest", "invest")):
        sym_roi = sym or "BTC-USD"
        results.append(
            {
                "tool": "run_roi_backtest",
                "result": await run_tool(
                    "run_roi_backtest",
                    {"symbol": sym_roi, "amount": 10000, "years": 10, "strategy": "cycle"},
                ),
            }
        )

    hits = await ai_db.search_knowledge(question, limit=4)
    if hits:
        results.append({"tool": "search_knowledge", "result": {"knowledge": hits}})

    lessons = await ai_db.get_learning_notes(limit=3)
    if lessons:
        results.append({"tool": "lessons", "result": {"lessons_learned": lessons}})

    return results


def tools_context_string(tool_results: list[dict]) -> str:
    return json.dumps(tool_results, ensure_ascii=False, indent=2)[:8000]

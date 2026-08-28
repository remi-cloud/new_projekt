"""Agent tools — market data, trend, patterns, cycles, knowledge."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai import db as ai_db
from app.ai.pattern_chart_svg import render_pattern_svg
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
    "spacex": "SPCX",
    "space-x": "SPCX",
    "space x": "SPCX",
    "spcx": "SPCX",
    # Common typo for iShares IG Corp Bond ETF
    "liq": "LQD",
}

# Common English / filler tokens that normalize to real tickers (e.g. ON) or noise.
_SYMBOL_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "on",
        "in",
        "at",
        "to",
        "for",
        "of",
        "it",
        "is",
        "are",
        "be",
        "as",
        "by",
        "from",
        "with",
        "all",
        "any",
        "ai",
        "vs",
        "me",
        "my",
        "we",
        "us",
        "you",
        "your",
        "this",
        "that",
        "trend",
        "pattern",
        "patterns",
        "macro",
        "cycle",
        "cycles",
        "full",
        "analysis",
        "analyze",
        "chart",
        "price",
        "buy",
        "sell",
        "long",
        "short",
    }
)

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
            "description": "Detect chart patterns with drawable geometry (points/lines), support and resistance",
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
            "name": "render_pattern_chart",
            "description": "Draw SVG chart of recent candles with detected pattern overlays (lines, S/R, markers)",
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
    {
        "type": "function",
        "function": {
            "name": "get_super_opportunity",
            "description": "Superokazja: bid/ask, IN/SL/TP, heatmap summary, AI trade verdict for a symbol",
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
            "name": "get_whale_bias",
            "description": "Whale / large-player CEX + on-chain flow bias for crypto (BTC/ETH/SOL)",
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
            "name": "get_fomo_ghost",
            "description": (
                "FOMO Ghost: top-30 fomo.family portfolios (Cope Capital) and recent "
                "tokens landing in their bags (buy activity). Educational — not advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max bag events (default 15)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_launch_scout",
            "description": (
                "Meme Universe · Launch Scout (flagship): Seed (~$200 MC / <$2k), Fresh/Early/Watch, "
                "Pump.fun top-30 trader moves, Robinhood chain, Dex/Gecko, Elon/CZ + Binance radar. "
                "Catch pumps before $1M — not late tips. Educational — not investment advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "description": "seed | fresh | early | watch | all (default seed)",
                    },
                    "limit": {"type": "integer", "description": "Max candidates (default 15)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_clock",
            "description": (
                "Session Clock: Asia/EU/US UTC timetable for meme activity heatmap + BTC/SOL "
                "hourly log-return bias. Use when user asks about timezone pumps, global schedule, "
                "session hot lanes. Educational — not a ticker prediction."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dex_arena",
            "description": (
                "Dex Arena (P1): best Launch Scout picks per DEX (Pump, Raydium, Pancake, Flap, 4meme) "
                "with whale_boost from Wallet Scout bags. Use for per-venue opportunity ranking. "
                "Educational — not advice."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wallet_scout",
            "description": (
                "Wallet Scout (P0): Pump top wallets with token, buy/sell direction, and open bags "
                "(net buy−sell) + optional RPC holdings. Use when user asks what big wallets hold. "
                "Educational — not advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max wallets (default 15)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_binance_portfolio_sync",
            "description": (
                "Binance AI BOT portfolio bridge: paper crypto positions vs Binance spot balances, "
                "drift % and trade deep links. Read-only. Use when user asks about Binance vs portfel."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_binance_ai_support",
            "description": (
                "Binance AI bridge: CZ/listing radar headlines + BTC/ETH/SOL whale bias from Binance feeds. "
                "Use for listing/meme radar / macro crypto context. Educational — not advice."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_singularity_book",
            "description": "Singularity war-room summary: scout counts, merged LONG/SHORT book",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_portfolio",
            "description": "Live paper trading desk from portfolio.db (cash, equity, open positions, recent trades). Use after restart / when user asks about portfel.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_cycles",
            "description": (
                "Bitcoin ATH cycle (364/1064) with BTC monthly seasonality + vs-SPX verdict/regime, "
                "and US presidential cycle with year×month seasonality (Best Six Nov–Apr). "
                "Use for crypto timing and US equities/ETFs/indexes when discussing when to expect strength or weakness."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_multi_timeframe",
            "description": "Multi-timeframe trend confluence (1M / 3M / 1Y) for a symbol",
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
            "name": "risk_snapshot",
            "description": "ATR-based stop distance, suggested position size vs paper equity, optional R:R vs Superokazja levels",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "account_equity": {"type": "number"},
                    "risk_pct": {"type": "number", "default": 1.0},
                },
                "required": ["symbol"],
            },
        },
    },
]


def normalize_symbol(raw: str) -> str | None:
    s = raw.strip().upper().replace(" ", "")
    low = raw.strip().lower()
    if low in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[low]
    if s.lower() in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[s.lower()]
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
    for word in re.findall(r"[A-Za-z0-9^./-]+", text or ""):
        if word.lower() in _SYMBOL_STOPWORDS:
            continue
        sym = normalize_symbol(word)
        if sym:
            return sym
    low = (text or "").lower()
    # Whole-word / bounded alias match only — avoid substring false positives.
    for alias, sym in sorted(SYMBOL_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", low):
            return sym
    return None


def resolve_focus_symbol(message: str, explicit_symbol: str | None = None) -> str | None:
    """Canonical symbol for a chat turn: explicit API symbol always wins."""
    if explicit_symbol and str(explicit_symbol).strip():
        raw = str(explicit_symbol).strip()
        norm = normalize_symbol(raw)
        if norm:
            return norm
        # Never replace a user/API ticker with a different one from the message.
        return raw.upper().replace(" ", "")
    return extract_symbol_from_text(message or "")


async def load_pattern_desk(symbol: str, range_: str = "3M") -> dict[str, Any]:
    """Single OHLC fetch shared by detect_patterns + render_pattern_chart."""
    chart = await fetch_chart(symbol, range_)
    if not chart or not chart.candles:
        return {"symbol": symbol, "range": range_, "candles": [], "analysis": None, "error": "No candles"}
    pa = detect_patterns(symbol, chart.candles)
    return {
        "symbol": symbol,
        "range": range_,
        "candles": chart.candles,
        "analysis": pa,
        "error": None,
    }


def _pattern_payload(symbol: str, pa) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "patterns": [
            {
                "name": p.name,
                "kind": p.kind,
                "confidence": p.confidence,
                "description": p.description,
                "levels": p.levels,
            }
            for p in pa.patterns
            if p.kind != "level" or p.name.startswith("near_")
        ],
        "support": pa.support_levels,
        "resistance": pa.resistance_levels,
        "summary": pa.summary,
        "geometry": pa.to_geometry(),
    }


def _atr(candles: list, period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    for i in range(-period, 0):
        c = candles[i]
        prev = candles[i - 1]
        tr = max(c.high - c.low, abs(c.high - prev.close), abs(c.low - prev.close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


async def build_desk_tool_bundle(symbol: str, range_: str = "3M") -> list[dict[str, Any]]:
    """Fresh desk tools for focus symbol (trend, patterns, SVG, context, MTF, risk, cycles)."""
    results: list[dict[str, Any]] = []
    desk = await load_pattern_desk(symbol, range_)
    candles = desk.get("candles") or []
    pa = desk.get("analysis")

    if candles:
        trend = analyze_trend(symbol, candles)
        results.append(
            {
                "tool": "analyze_trend",
                "result": {
                    "symbol": symbol,
                    "trend": trend.direction,
                    "strength": trend.strength,
                    "rsi14": trend.rsi14,
                    "structure": trend.structure,
                    "change_7d_pct": trend.change_7d_pct,
                    "change_30d_pct": trend.change_30d_pct,
                    "summary": trend.summary,
                },
            }
        )
    else:
        results.append(
            {
                "tool": "analyze_trend",
                "result": {"error": desk.get("error") or "No candles", "symbol": symbol},
            }
        )

    if pa is not None:
        results.append({"tool": "detect_patterns", "result": _pattern_payload(symbol, pa)})
        svg = render_pattern_svg(symbol, candles, pa)
        results.append(
            {
                "tool": "render_pattern_chart",
                "result": {
                    "symbol": symbol,
                    "mime": "image/svg+xml",
                    "svg": svg,
                    "patterns_summary": pa.summary,
                    "pattern_count": len(
                        [p for p in pa.patterns if p.kind != "level" or p.name.startswith("near_")]
                    ),
                },
            }
        )
    else:
        results.append(
            {
                "tool": "detect_patterns",
                "result": {"symbol": symbol, "error": desk.get("error") or "No patterns"},
            }
        )

    results.append({"tool": "get_market_context", "result": await run_tool("get_market_context", {"symbol": symbol})})
    results.append(
        {"tool": "analyze_multi_timeframe", "result": await run_tool("analyze_multi_timeframe", {"symbol": symbol})}
    )
    results.append({"tool": "risk_snapshot", "result": await run_tool("risk_snapshot", {"symbol": symbol})})
    results.append({"tool": "get_macro_cycles", "result": await run_tool("get_macro_cycles", {})})
    return results


async def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "analyze_trend":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            chart = await fetch_chart(symbol, arguments.get("range", "3M"))
            if not chart or not chart.candles:
                return {"error": f"No candles for {symbol}", "symbol": symbol}
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
            desk = await load_pattern_desk(symbol, arguments.get("range", "3M"))
            if desk.get("error") or desk.get("analysis") is None:
                return {"error": desk.get("error") or "No candles", "symbol": symbol}
            return _pattern_payload(symbol, desk["analysis"])
        if name == "render_pattern_chart":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            desk = await load_pattern_desk(symbol, arguments.get("range", "3M"))
            if desk.get("error") or desk.get("analysis") is None:
                return {"error": desk.get("error") or "No candles", "symbol": symbol}
            pa = desk["analysis"]
            svg = render_pattern_svg(symbol, desk["candles"], pa)
            return {
                "symbol": symbol,
                "mime": "image/svg+xml",
                "svg": svg,
                "patterns_summary": pa.summary,
                "pattern_count": len(
                    [p for p in pa.patterns if p.kind != "level" or p.name.startswith("near_")]
                ),
            }
        if name == "analyze_multi_timeframe":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            frames: list[dict[str, Any]] = []
            score_map = {"uptrend": 1, "downtrend": -1, "sideways": 0, "unknown": 0}
            votes = 0
            for preset in ("1M", "3M", "1Y"):
                chart = await fetch_chart(symbol, preset)
                if not chart or not chart.candles:
                    frames.append({"range": preset, "error": "no_data"})
                    continue
                trend = analyze_trend(symbol, chart.candles)
                votes += score_map.get(trend.direction, 0)
                frames.append(
                    {
                        "range": preset,
                        "trend": trend.direction,
                        "strength": trend.strength,
                        "structure": trend.structure,
                        "rsi14": trend.rsi14,
                    }
                )
            n = max(1, sum(1 for f in frames if "trend" in f))
            conf = abs(votes) / n
            if votes > 0:
                bias = "bullish"
            elif votes < 0:
                bias = "bearish"
            else:
                bias = "neutral"
            return {
                "symbol": symbol,
                "frames": frames,
                "bias": bias,
                "confluence_score": round(conf * 100, 1),
                "summary": f"{symbol} MTF bias {bias} (confluence {conf * 100:.0f}%)",
            }
        if name == "risk_snapshot":
            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            chart = await fetch_chart(symbol, arguments.get("range", "3M"))
            if not chart or not chart.candles:
                return {"error": f"No candles for {symbol}", "symbol": symbol}
            candles = chart.candles
            price = float(candles[-1].close)
            atr = _atr(candles, 14)
            stop_dist = float(atr) * 1.5 if atr else price * 0.02
            risk_pct = float(arguments.get("risk_pct") or 1.0)
            risk_pct = max(0.25, min(2.0, risk_pct))
            equity = arguments.get("account_equity")
            if equity is None:
                try:
                    from app.paper.portfolio_memory import get_agent_portfolio_context

                    paper = await get_agent_portfolio_context()
                    summary = (paper or {}).get("summary") or paper or {}
                    equity = summary.get("total_equity_pln") or summary.get("equity")
                except Exception:
                    equity = None
            try:
                equity_f = float(equity) if equity is not None else 100_000.0
            except (TypeError, ValueError):
                equity_f = 100_000.0
            risk_budget = equity_f * (risk_pct / 100.0)
            size_units = risk_budget / stop_dist if stop_dist > 0 else None
            notional = (size_units * price) if size_units is not None else None
            stop_price = price - stop_dist
            levels = None
            rr = None
            try:
                super_res = await run_tool("get_super_opportunity", {"symbol": symbol})
                if not super_res.get("error"):
                    levels = super_res.get("levels")
                    if isinstance(levels, dict):
                        tp = levels.get("tp") or levels.get("take_profit") or levels.get("tp1")
                        sl = levels.get("sl") or levels.get("stop_loss")
                        entry = levels.get("entry") or levels.get("in") or price
                        if tp is not None and sl is not None and entry is not None:
                            risk = abs(float(entry) - float(sl))
                            reward = abs(float(tp) - float(entry))
                            if risk > 0:
                                rr = round(reward / risk, 2)
            except Exception:
                pass
            return {
                "symbol": symbol,
                "price": round(price, 6),
                "atr14": round(atr, 6) if atr else None,
                "suggested_stop_distance": round(stop_dist, 6),
                "suggested_stop_price": round(stop_price, 6),
                "account_equity": round(equity_f, 2),
                "risk_pct": risk_pct,
                "risk_budget": round(risk_budget, 2),
                "suggested_size_units": round(size_units, 6) if size_units is not None else None,
                "suggested_notional": round(notional, 2) if notional is not None else None,
                "super_levels": levels,
                "reward_risk": rr,
                "summary": (
                    f"{symbol} risk: ATR stop ~{stop_dist:.4g}, "
                    f"size≈{size_units:.4g} u ({risk_pct}% of equity)"
                    + (f", R:R {rr}" if rr is not None else "")
                ),
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
            from app.cycles.bitcoin_seasonality import btc_seasonality_desk_brief
            from app.cycles.presidential_cycle import analyze_presidential_cycle
            from app.cycles.presidential_seasonality import seasonality_desk_brief

            if not scanner.bitcoin_cycle:
                await scanner.scan()
            btc = scanner.bitcoin_cycle
            # Fresh presidential snapshot so seasonality fields are always current
            pres = analyze_presidential_cycle()
            scanner.presidential_cycle = pres
            season = seasonality_desk_brief(pres.current_year)
            month_strip = [
                {
                    "month": m.month,
                    "avg_pct": m.avg_return_pct,
                    "bias": m.bias,
                    "is_current": m.is_current,
                }
                for m in (pres.month_returns or [])
            ]
            month_matrices = [
                {
                    "year": row.year.value,
                    "year_number": row.year_number,
                    "label": row.label,
                    "calendar_year": row.calendar_year,
                    "is_current": row.is_current,
                    "months": [
                        {
                            "month": m.month,
                            "avg_pct": m.avg_return_pct,
                            "bias": m.bias,
                            "is_current": m.is_current,
                        }
                        for m in row.months
                    ],
                }
                for row in (pres.month_matrices or [])
            ]
            next_term = None
            if pres.next_term_outlook:
                nt = pres.next_term_outlook
                next_term = {
                    "term_start": nt.term_start.isoformat(),
                    "term_end": nt.term_end.isoformat(),
                    "label": nt.label,
                    "note": nt.note,
                    "year_rows": [
                        {
                            "year": row.year.value,
                            "year_number": row.year_number,
                            "label": row.label,
                            "calendar_year": row.calendar_year,
                            "months": [
                                {
                                    "month": m.month,
                                    "avg_pct": m.avg_return_pct,
                                    "bias": m.bias,
                                }
                                for m in row.months
                            ],
                        }
                        for row in nt.year_rows
                    ],
                }
            btc_payload: dict = {
                "phase": btc.phase.value if btc else None,
                "signal": btc.signal.value if btc else None,
                "rationale": btc.rationale if btc else None,
            }
            if btc:
                btc_season = btc_seasonality_desk_brief(
                    btc.phase,
                    btc.days_since_ath,
                    bear_end=btc.bear_phase_end_day,
                    bull_days=max(1, btc.bull_phase_end_day - btc.bear_phase_end_day),
                )
                btc_month_strip = [
                    {
                        "month": m.month,
                        "avg_pct": m.avg_return_pct,
                        "bias": m.bias,
                        "is_current": m.is_current,
                        "n": m.n,
                    }
                    for m in (btc.month_returns or [])
                ]
                spx = btc.spx_comparison
                btc_payload.update(
                    {
                        "days_since_ath": btc.days_since_ath,
                        "phase_progress_pct": btc.phase_progress_pct,
                        "calendar_season": btc.calendar_season,
                        "current_month_avg_pct": btc.current_month_avg_return_pct,
                        "current_month_bias": btc.current_month_bias,
                        "phase_month_bias": btc.phase_month_bias,
                        "seasonality_sample_count": btc.seasonality_sample_count,
                        "month_returns": btc_month_strip,
                        "seasonality": btc_season,
                        "spx_comparison": (
                            {
                                "corr_full": spx.corr_full,
                                "corr_rolling_24m_latest": spx.corr_rolling_24m_latest,
                                "best_six_delta_pct": spx.best_six_delta_pct,
                                "month_sign_agreement": spx.month_sign_agreement,
                                "verdict": spx.verdict,
                                "regime": spx.regime,
                            }
                            if spx
                            else None
                        ),
                        "how_to_use": (
                            "For crypto: cite ATH phase (364/1064) PLUS current month bias from "
                            "seasonality. spx_comparison.verdict/regime tell whether BTC is "
                            "tracking equity seasonality (do not copy US Best Six blindly). "
                            "Never invent monthly stats — use this payload only."
                        ),
                    }
                )
            from app.cycles.calendar_seasonality import current_month_pumps_brief
            from app.cycles.global_cycle_book import get_global_cycle_book
            from app.cycles.seasonality_monitor import get_health
            from app.telemetry.agent_vs_spx import get_telemetry_series

            season_health = get_health()
            try:
                tele = await get_telemetry_series("30d")
                tele_last = tele.get("last")
            except Exception:
                tele_last = None
            gbook = get_global_cycle_book("all")
            adopted_brief = [
                {
                    "id": e["id"],
                    "horizon": e["horizon"],
                    "slot_label": e["slot_label"],
                    "side": e["side"],
                    "avg_return_pct": e["avg_return_pct"],
                    "markets": e["markets"],
                    "reproduction_score": e["reproduction_score"],
                }
                for e in (gbook.get("adopted") or [])[:12]
            ]
            return {
                "bitcoin": btc_payload,
                "presidential": {
                    "president": pres.president,
                    "year": pres.current_year.value,
                    "year_number": pres.year_number,
                    "signal": pres.signal.value,
                    "buy_weight": pres.buy_weight,
                    "rationale": pres.rationale,
                    "calendar_season": pres.calendar_season,
                    "current_month_avg_pct": pres.current_month_avg_return_pct,
                    "current_month_bias": pres.current_month_bias,
                    "seasonality_universe_size": pres.seasonality_universe_size,
                    "month_returns": month_strip,
                    "month_matrices": month_matrices,
                    "next_term_outlook": next_term,
                    "seasonality": season,
                    "seasonality_health": season_health,
                    "how_to_use": (
                        "For region=us instruments: cite year_of_term + current month bias + "
                        "best_six/worst_six. month_matrices has all years 1–4 (not only current). "
                        "next_term_outlook projects the same historical pattern onto 2029–2033 "
                        "after Trump II — not a prediction of who wins 2028. "
                        "If seasonality_health.drift_alert, overlay is softened — mention uncertainty. "
                        "Do not invent monthly stats — use this payload only."
                    ),
                },
                "global_cycle_book": {
                    "meta": gbook.get("meta"),
                    "adopted": adopted_brief,
                    "mean_month_corr": (gbook.get("meta") or {}).get("mean_month_corr"),
                    "mean_week_corr": (gbook.get("meta") or {}).get("mean_week_corr"),
                    "how_to_use": (
                        "Field scouts: same month/week/Best-Six rules on us/eu/asia/em/pl/crypto. "
                        "Cite adopted slots (bid↑/ask↓) + markets + reproduction_score. "
                        "For non-US assets prefer global_cycle_book over US presidential months."
                    ),
                },
                "calendar_pumps": {
                    **current_month_pumps_brief(top_n=5),
                    "how_to_use": (
                        "Current calendar month: which catalog assets were historically pumped/drained "
                        "(avg monthly return). Includes commodities, sector/utility ETFs (XLU…), bonds, crypto. "
                        "Cite symbol + avg_pct; do not invent rankings."
                    ),
                },
                "telemetry": {
                    "last": tele_last,
                    "note": "Live agent EW BUY basket NAV vs SPX (normalized 100).",
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
        if name == "get_super_opportunity":
            from app.scanners.super_opportunities import (
                build_super_opportunity,
                resolve_opportunity_for_symbol,
            )

            symbol = normalize_symbol(arguments.get("symbol", ""))
            if not symbol:
                return {"error": "Unknown symbol"}
            opp = await resolve_opportunity_for_symbol(symbol)
            if not opp:
                return {"error": f"No opportunity for {symbol}"}
            data = await build_super_opportunity(opp, include_heatmap_3d=False)
            heat = data.get("heatmap") or {}
            bins = heat.get("bins") or []
            top = sorted(bins, key=lambda b: b.get("intensity", 0), reverse=True)[:5]
            return {
                "symbol": data["symbol"],
                "super_score": data["super_score"],
                "is_super": data["is_super"],
                "action": data["action"],
                "bid": data.get("bid"),
                "ask": data.get("ask"),
                "levels": data.get("levels"),
                "ai_signal": data.get("ai_signal"),
                "prediction_summary": (data.get("prediction") or {}).get("summary"),
                "whale": data.get("whale"),
                "heatmap_top_bins": top,
                "reasons": (data.get("reasons") or [])[:6],
            }
        if name == "get_whale_bias":
            from app.data.whale_flows import fetch_whale_for_symbol

            symbol = normalize_symbol(arguments.get("symbol", "")) or "BTC-USD"
            whale = await fetch_whale_for_symbol(symbol)
            if not whale:
                return {"error": f"Whale data only for BTC/ETH/SOL — got {symbol}"}
            return {
                "symbol": whale.get("symbol"),
                "bias": whale.get("bias"),
                "strength": whale.get("strength"),
                "summary": whale.get("summary"),
                "factors": (whale.get("factors") or [])[:5],
            }
        if name == "get_fomo_ghost":
            from app.fomo.service import get_fomo_status, list_fomo_events, list_fomo_top

            lim = int(arguments.get("limit") or 15)
            lim = max(1, min(40, lim))
            status = await get_fomo_status()
            top = await list_fomo_top(limit=30)
            buys = await list_fomo_events(limit=lim, side="buy")
            return {
                "status": {
                    "enabled": status.get("enabled"),
                    "needs_api_key": status.get("needs_api_key"),
                    "last_tick_at": status.get("last_tick_at"),
                    "traders_count": status.get("traders_count"),
                    "events_count": status.get("events_count"),
                },
                "top_handles": [t.get("handle") for t in top[:30]],
                "recent_bag_buys": buys,
                "note": "Buy = token landed in bag; not always a brand-new position.",
            }
        if name == "get_session_clock":
            from app.cycles.session_clock import get_session_clock_snapshot

            return await get_session_clock_snapshot()
        if name == "get_dex_arena":
            from app.launch_scout.dex_arena import get_dex_arena_snapshot

            return await get_dex_arena_snapshot()
        if name == "get_wallet_scout":
            from app.launch_scout.wallet_scout import get_wallet_scout_snapshot

            lim = int(arguments.get("limit") or 15)
            lim = max(1, min(30, lim))
            return await get_wallet_scout_snapshot(limit=lim)
        if name == "get_launch_scout":
            from app.launch_scout.service import (
                get_launch_status,
                list_launch_candidates,
                list_launch_traders,
                list_meme_whispers,
            )

            lim = int(arguments.get("limit") or 15)
            lim = max(1, min(40, lim))
            tier = str(arguments.get("tier") or "seed").strip().lower()
            if tier not in ("seed", "fresh", "early", "watch", "all"):
                tier = "seed"
            status = await get_launch_status()
            cands = await list_launch_candidates(tier=tier, limit=lim)
            whispers = await list_meme_whispers(limit=10)
            traders = await list_launch_traders(limit=10)
            return {
                "status": {
                    "enabled": status.get("enabled"),
                    "flagship": status.get("flagship"),
                    "brand": status.get("brand"),
                    "last_tick_at": status.get("last_tick_at"),
                    "counts": status.get("counts"),
                    "thresholds": status.get("thresholds"),
                    "whispers_count": status.get("whispers_count"),
                    "traders_count": status.get("traders_count"),
                    "entry_note": status.get("entry_note"),
                },
                "tier": tier,
                "candidates": [
                    {
                        "symbol": c.get("symbol"),
                        "chain": c.get("chain"),
                        "dex_id": c.get("dex_id"),
                        "market_cap": c.get("market_cap"),
                        "liq_usd": c.get("liq_usd"),
                        "tier": c.get("tier"),
                        "score": c.get("score"),
                        "tags": c.get("tags"),
                        "url": c.get("url"),
                        "mint": c.get("mint"),
                    }
                    for c in cands
                ],
                "traders": [
                    {
                        "wallet": t.get("wallet"),
                        "rank": t.get("rank"),
                        "buys": t.get("buys"),
                        "score": t.get("score"),
                        "source": t.get("source"),
                    }
                    for t in traders
                ],
                "whispers": [
                    {
                        "author": w.get("author"),
                        "text": (w.get("text") or "")[:240],
                        "keywords": w.get("keywords"),
                        "url": w.get("url"),
                        "source": w.get("source"),
                    }
                    for w in whispers
                ],
                "note": "Meme Universe flagship — educational, not investment advice.",
            }
        if name == "get_binance_portfolio_sync":
            from app.integrations.portfolio_binance_bridge import build_binance_sync

            return await build_binance_sync()
        if name == "get_binance_ai_support":
            from app.integrations.binance_ai_bridge import get_binance_ai_context

            return await get_binance_ai_context()
        if name == "get_singularity_book":
            from app.agents.orchestrator import orchestrator

            if not orchestrator.last_result:
                await orchestrator.run_pipeline()
            report = orchestrator.agent_report()
            return {
                "ready": report.get("ready"),
                "pipeline": report.get("pipeline"),
                "opportunities": report.get("opportunities"),
                "counts": report.get("counts"),
                "last_scan_at": report.get("last_scan_at"),
                "long_sample": (report.get("long_verdicts") or [])[:5],
                "short_sample": (report.get("short_verdicts") or [])[:5],
            }
        if name == "get_paper_portfolio":
            from app.paper.portfolio_memory import get_agent_portfolio_context

            return await get_agent_portfolio_context()
        return {"error": f"Unknown tool {name}"}
    except Exception as exc:
        logger.exception("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}


async def auto_tools_for_question(
    question: str,
    explicit_symbol: str | None = None,
    *,
    with_desk_bundle: bool = False,
) -> list[dict[str, Any]]:
    """Run relevant tools without LLM (fallback / enrichment)."""
    results: list[dict] = []
    sym = resolve_focus_symbol(question, explicit_symbol)
    low = question.lower()

    want_desk = with_desk_bundle or (
        sym
        and any(
            k in low
            for k in (
                "wzor",
                "pattern",
                "formac",
                "support",
                "opór",
                "opor",
                "resist",
                "rysuj",
                "wykres",
                "chart",
                "double",
                "triangle",
                "engulf",
                "doji",
                "analiz",
                "analyz",
                "trend",
                "setup",
                "ryzyk",
                "risk",
            )
        )
    )
    if sym and want_desk:
        results.extend(await build_desk_tool_bundle(sym))
    elif sym:
        results.append({"tool": "analyze_trend", "result": await run_tool("analyze_trend", {"symbol": sym})})
        results.append(
            {"tool": "get_market_context", "result": await run_tool("get_market_context", {"symbol": sym})}
        )

    if sym and any(k in low for k in ("super", "heatmap", "liq", "likwid", "sl", "tp", "wejś", "entry")):
        if not any(t.get("tool") == "get_super_opportunity" for t in results):
            results.append(
                {"tool": "get_super_opportunity", "result": await run_tool("get_super_opportunity", {"symbol": sym})}
            )
    if sym and any(k in low for k in ("whale", "wielk", "on-chain", "onchain", "mempool")):
        results.append({"tool": "get_whale_bias", "result": await run_tool("get_whale_bias", {"symbol": sym})})

    if not any(t.get("tool") == "get_macro_cycles" for t in results) and any(
        k in low
        for k in (
            "cykl",
            "cycle",
            "bitcoin",
            "btc",
            "prezyden",
            "president",
            "fed",
            "makro",
            "sezon",
            "season",
            "best six",
            "midterm",
            "kadenc",
            "miesiąc",
            "miesiac",
            "november",
            "listopad",
        )
    ):
        results.append({"tool": "get_macro_cycles", "result": await run_tool("get_macro_cycles", {})})

    if any(
        k in low
        for k in (
            "sezon",
            "season",
            "best six",
            "prezyden",
            "president",
            "kadenc",
            "midterm",
            "bitcoin",
            "btc",
        )
    ):
        if not any(t.get("tool") == "search_knowledge" for t in results):
            q = (
                "sezonowość BTC vs S&P cykl 364/1064"
                if any(k in low for k in ("bitcoin", "btc"))
                else "sezonowość prezydencka USA best six months"
            )
            results.append(
                {
                    "tool": "search_knowledge",
                    "result": await run_tool("search_knowledge", {"query": q}),
                }
            )

    if any(
        k in low
        for k in (
            "asymmetr",
            "asymetri",
            "asymmetric",
            "r:r",
            "risk/reward",
            "risk reward",
            "reward risk",
            "sizing",
            "accept",
            "reject",
            "superokaz",
            "payoff",
        )
    ):
        results.append(
            {
                "tool": "search_knowledge",
                "result": await run_tool(
                    "search_knowledge",
                    {"query": "Asymmetric bets R:R Superokazja sizing ACCEPT REJECT"},
                ),
            }
        )
        if sym and not any(t.get("tool") == "risk_snapshot" for t in results):
            results.append(
                {"tool": "risk_snapshot", "result": await run_tool("risk_snapshot", {"symbol": sym})}
            )
        if sym and not any(t.get("tool") == "get_super_opportunity" for t in results):
            results.append(
                {
                    "tool": "get_super_opportunity",
                    "result": await run_tool("get_super_opportunity", {"symbol": sym}),
                }
            )
    if any(k in low for k in ("singularity", "scout", "war room", "orchestr")):
        results.append({"tool": "get_singularity_book", "result": await run_tool("get_singularity_book", {})})

    if any(
        k in low
        for k in (
            "launch scout",
            "meme universe",
            "launchpad",
            "low mc",
            "low-mc",
            "market cap",
            "marketcap",
            "pump.fun",
            "pumpfun",
            "dexscreener",
            "fresh launch",
            "nowy token",
            "nowe tokeny",
            "mały mc",
            "maly mc",
            "elon",
            "musk",
            "changpeng",
            "binance alpha",
            "who owns the memes",
        )
    ):
        results.append(
            {
                "tool": "get_launch_scout",
                "result": await run_tool("get_launch_scout", {"tier": "seed", "limit": 15}),
            }
        )

    if any(
        k in low
        for k in (
            "wallet scout",
            "open bags",
            "top wallet",
            "big wallet",
            "pump trader",
            "co trzyma",
            "portfel pump",
            "otwarte bagi",
        )
    ):
        results.append(
            {
                "tool": "get_wallet_scout",
                "result": await run_tool("get_wallet_scout", {"limit": 15}),
            }
        )

    if any(
        k in low
        for k in (
            "session clock",
            "timezone",
            "time zone",
            "asia open",
            "london session",
            "ny session",
            "plan jazdy",
            "strefa czasowa",
            "log return",
            "log-return",
            "sesja asia",
            "sesja us",
        )
    ):
        results.append(
            {
                "tool": "get_session_clock",
                "result": await run_tool("get_session_clock", {}),
            }
        )

    if any(
        k in low
        for k in (
            "dex arena",
            "raydium",
            "pancakeswap",
            "pancake",
            "per dex",
            "per-dex",
            "cały dex",
            "caly dex",
            "whole dex",
            "flap",
            "4meme",
        )
    ):
        results.append(
            {
                "tool": "get_dex_arena",
                "result": await run_tool("get_dex_arena", {}),
            }
        )

    if any(k in low for k in ("binance", "listing radar", "cz binance", "binance trade", "portfel binance", "portfolio binance")):
        results.append(
            {
                "tool": "get_binance_ai_support",
                "result": await run_tool("get_binance_ai_support", {}),
            }
        )
        results.append(
            {
                "tool": "get_binance_portfolio_sync",
                "result": await run_tool("get_binance_portfolio_sync", {}),
            }
        )

    if any(
        k in low
        for k in (
            "portfel",
            "portfolio",
            "paper",
            "gotówk",
            "gotowk",
            "cash",
            "pozycj",
            "equity",
            "konto paper",
        )
    ):
        results.append({"tool": "get_paper_portfolio", "result": await run_tool("get_paper_portfolio", {})})

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
    slim: list[dict] = []
    for block in tool_results:
        res = block.get("result")
        if isinstance(res, dict) and res.get("svg"):
            slim.append(
                {
                    **block,
                    "result": {
                        **{k: v for k, v in res.items() if k != "svg"},
                        "svg": "[svg omitted — shown in UI]",
                    },
                }
            )
        else:
            slim.append(block)
    return json.dumps(slim, ensure_ascii=False, indent=2)[:8000]

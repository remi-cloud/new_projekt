"""Finance AI agent orchestrator — Senior Finance Desk."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai import db as ai_db
from app.ai.critic import critique_response
from app.ai.finance_guard import finance_only_message, is_finance_related
from app.ai.llm import (
    chat_completion,
    extract_message,
    llm_configured,
    message_content,
    parse_tool_calls,
    simple_complete,
)
from app.ai.tools import (
    TOOL_DEFINITIONS,
    auto_tools_for_question,
    build_desk_tool_bundle,
    resolve_focus_symbol,
    run_tool,
    tools_context_string,
)
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Cyclical Academy Supermind Desk — a synthetic Wall Street investment committee with 15+ years of desk judgment.
You fuse three thinking styles (inspired by, NOT impersonating anyone):
- Value / Capital (Buffett-style): margin of safety, capital allocation discipline, moat vs no-moat.
- First principles / Asymmetry (Musk-style): what must be true, upside vs ruin, when status quo is wrong.
- Liquidity & power (Rothschild-style capital stewardship): credit/liquidity cycles, who holds power in the capital chain, multi-year horizon.
Never say “I am Elon/Warren/Rothschild” or speak in their first person. No celebrity gossip.

You are NOT a licensed advisor; all output is educational desk analysis for the user’s own decisions.

RULES:
- Answer ONLY finance/markets/trading/cycles/macro/risk questions.
- Use ONLY tool data for prices, levels, patterns, cycles, portfolio — never invent numbers.
- When render_pattern_chart / detect_patterns / Chart UI are present, refer to those levels only.
- Paper portfolio (if injected) is the live simulated desk from portfolio.db — do not invent holdings.
- Prefer multi-timeframe confluence + cyclical scanner + risk_snapshot; use whale / Superokazja / macro cycles / paper equity when present in tools.
- US seasonality (from get_macro_cycles → presidential.seasonality / month_returns / month_matrices):
  - Year of term 1–4 + current calendar month tell historically where strength/weakness clusters (US equal-weight universe, not just S&P).
  - month_matrices covers ALL years 1–4 for the current term (calendar years mapped); do not discuss only year 2.
  - next_term_outlook = same historical pattern on the term after Trump II (2029–2033) — continuation, not election forecasting.
  - Best Six Months = Nov–Apr (historically stronger); May–Oct = softer — prefer confirmation / smaller size unless tools disagree.
  - In Thesis and Liquidity & power, say what to expect NOW (month bias up/down) and which months in this year were historically strongest/weakest when relevant.
  - For non-US assets, do not force presidential month seasonality.
- BTC seasonality (from get_macro_cycles → bitcoin.seasonality / month_returns / spx_comparison):
  - Primary clock remains ATH phase 364/1064; month bias is additive.
  - Cite current_month_bias + strongest/weakest months; mention spx_comparison.verdict and regime (equity_beta | mixed | crypto_idiosyncratic).
  - Do not copy US Best Six onto BTC unless verdict/regime justify a comparison — BTC best/worst six can be similar in magnitude.
  - DISTRIBUTION/SELL from late cycle is not upgraded by a historically strong calendar month alone.
- Global cycle order book (from get_macro_cycles → global_cycle_book):
  - Same rules (calendar month, week-of-month W1–W4, Best Six) compared across us/eu/asia/em/pl/crypto.
  - Prefer adopted slots that reproduce on ≥4 markets; cite side (bid/ask), markets, reproduction_score.
  - For EU/Asia/EM/PL use this book instead of forcing US presidential month seasonality.
- Calendar pumps (from get_macro_cycles → calendar_pumps):
  - Which instruments historically rise/fall in the current calendar month across the full catalog
    (commodities, utility/sector ETFs, bonds, crypto, forex). Cite top pumped/drained with avg_pct.
- Never guarantee profits. State uncertainty explicitly. If lenses conflict, say so and lower conviction.

ALWAYS structure the answer with these headings (match user language):
1) **Instrument & bias** — Bull / Bear / Neutral + merged conviction 0–100% after the council
2) **Thesis** — 2–4 sentences: trend, structure, cycle/macro context
3) **Council lenses** — exactly three short bullets (1–2 sentences each):
   - **Value / Capital**
   - **First principles / Asymmetry**
   - **Liquidity & power**
4) **Setup** — entry zone, invalidation, targets; R:R if computable from tools
5) **Risk** — what breaks the thesis; suggested size / stop from risk_snapshot when available
6) **Plan** — what to watch next; when NOT to trade
7) Closing disclaimer: "Informacja edukacyjna — nie stanowi porady inwestycyjnej." (or EN equivalent)

Language: match the user's language (Polish/English/German/etc.). Decisive, institutional, committee tone — not a chatbot."""


def _prioritize_tool_data(tool_results: list[dict], limit: int = 12) -> list[dict]:
    """Keep SVG / desk core tools in meta even when many tools ran."""
    priority = {
        "render_pattern_chart": 0,
        "detect_patterns": 1,
        "analyze_trend": 2,
        "risk_snapshot": 3,
        "analyze_multi_timeframe": 4,
        "get_market_context": 5,
        "get_macro_cycles": 6,
        "get_super_opportunity": 7,
    }
    ranked = sorted(
        enumerate(tool_results),
        key=lambda iv: (priority.get(iv[1].get("tool", ""), 50), iv[0]),
    )
    return [b for _, b in ranked[:limit]]


def _tool_map(tool_results: list[dict], focus: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for block in tool_results:
        name = block.get("tool")
        res = block.get("result")
        if not name or not isinstance(res, dict):
            continue
        if focus and res.get("symbol") and res.get("symbol") != focus:
            continue
        out[str(name)] = res
    return out


def build_desk_ui(focus: str | None, tool_results: list[dict]) -> dict[str, Any] | None:
    """Compact UI payload — levels/bias/MTF/risk without embedding SVG bytes."""
    if not focus:
        return None
    by = _tool_map(tool_results, focus)
    # Also accept tools without symbol filter if focus-only map empty for that tool
    by_any = _tool_map(tool_results, None)
    trend = by.get("analyze_trend") or by_any.get("analyze_trend") or {}
    patterns = by.get("detect_patterns") or by_any.get("detect_patterns") or {}
    risk = by.get("risk_snapshot") or by_any.get("risk_snapshot") or {}
    mtf = by.get("analyze_multi_timeframe") or by_any.get("analyze_multi_timeframe") or {}
    market = by.get("get_market_context") or by_any.get("get_market_context") or {}
    svg = by.get("render_pattern_chart") or by_any.get("render_pattern_chart") or {}

    direction = str(mtf.get("bias") or trend.get("trend") or market.get("signal") or "neutral")
    low = direction.lower()
    if "up" in low or low in ("bull", "bullish", "buy"):
        bias = "bull"
    elif "down" in low or low in ("bear", "bearish", "sell"):
        bias = "bear"
    else:
        bias = "neutral"

    try:
        conviction = float(trend.get("strength") or mtf.get("confluence_score") or market.get("confidence") or 50)
    except (TypeError, ValueError):
        conviction = 50.0

    pat_list = []
    for p in patterns.get("patterns") or []:
        if not isinstance(p, dict):
            continue
        pat_list.append(
            {
                "name": p.get("name"),
                "confidence": p.get("confidence"),
                "kind": p.get("kind"),
            }
        )

    frames = []
    for f in mtf.get("frames") or []:
        if isinstance(f, dict):
            frames.append(
                {
                    "range": f.get("range"),
                    "trend": f.get("trend"),
                    "strength": f.get("strength"),
                    "error": f.get("error"),
                }
            )

    has_svg = isinstance(svg.get("svg"), str) and "<svg" in svg["svg"]

    return {
        "symbol": focus,
        "bias": bias,
        "conviction": round(conviction, 1),
        "trend_summary": trend.get("summary"),
        "support": list(patterns.get("support") or [])[:5],
        "resistance": list(patterns.get("resistance") or [])[:5],
        "patterns": pat_list[:8],
        "patterns_summary": patterns.get("summary") or svg.get("patterns_summary"),
        "mtf": {
            "bias": mtf.get("bias"),
            "confluence_score": mtf.get("confluence_score"),
            "frames": frames,
        },
        "risk": {
            "summary": risk.get("summary"),
            "suggested_stop_price": risk.get("suggested_stop_price"),
            "suggested_stop_distance": risk.get("suggested_stop_distance"),
            "reward_risk": risk.get("reward_risk"),
            "suggested_size_units": risk.get("suggested_size_units"),
            "price": risk.get("price"),
        },
        "market_signal": market.get("signal"),
        "market_confidence": market.get("confidence"),
        "has_svg": has_svg,
    }


async def chat(
    message: str,
    session_id: str | None = None,
    locale: str = "pl",
    symbol: str | None = None,
) -> dict[str, Any]:
    if not settings.ai_enabled:
        return _disabled_response(session_id)

    if not is_finance_related(message) and not symbol:
        sid = session_id or await ai_db.create_session("Off-topic")
        await ai_db.add_message(sid, "user", message)
        reply = finance_only_message(locale)
        mid = await ai_db.add_message(sid, "assistant", reply, {"blocked": True})
        return _pack(sid, reply, mid, [], None, 0, None, None)

    sid = session_id or await ai_db.create_session(message[:60])
    history = await ai_db.get_messages(sid, limit=settings.ai_max_history_messages)
    await ai_db.add_message(sid, "user", message)

    focus = resolve_focus_symbol(message, symbol)
    # Always rebuild a fresh desk bundle for the focus symbol (no stale other-symbol tools).
    if focus:
        tool_results = await build_desk_tool_bundle(focus)
        extras = await auto_tools_for_question(message, focus, with_desk_bundle=False)
        for block in extras:
            name = block.get("tool")
            if name in {
                "analyze_trend",
                "detect_patterns",
                "render_pattern_chart",
                "get_market_context",
                "analyze_multi_timeframe",
                "risk_snapshot",
                "get_macro_cycles",
            }:
                continue
            tool_results.append(block)
    else:
        tool_results = await auto_tools_for_question(message, None, with_desk_bundle=False)

    ctx = tools_context_string(tool_results)
    if focus:
        ctx = f"Focus symbol for this turn: {focus}\n\n" + ctx
    try:
        from app.paper.portfolio_memory import get_agent_portfolio_context

        paper_ctx = await get_agent_portfolio_context()
        ctx += "\n\nPaper portfolio (session memory from portfolio.db):\n" + json.dumps(
            paper_ctx, ensure_ascii=False
        )
    except Exception as exc:
        logger.debug("Paper portfolio inject skipped: %s", exc)

    inject_n = max(3, min(12, int(getattr(settings, "ai_learning_inject_limit", 8) or 8)))
    lessons = await ai_db.get_learning_notes(limit=inject_n)
    if lessons:
        ctx += "\n\nLearned lessons (apply when relevant):\n" + json.dumps(lessons, ensure_ascii=False)
        for note in lessons:
            if note.get("id") is not None:
                try:
                    await ai_db.bump_learning_use(int(note["id"]))
                except Exception:
                    pass

    draft, llm_tool_blocks = await _generate(message, history, ctx, focus)
    for block in llm_tool_blocks:
        bsym = (block.get("result") or {}).get("symbol")
        # Prefer focus-symbol tool results; skip conflicting other symbols for chart tools
        if focus and block.get("tool") in ("detect_patterns", "render_pattern_chart", "analyze_trend"):
            if bsym and bsym != focus:
                continue
        if not any(
            t.get("tool") == block.get("tool") and (t.get("result") or {}).get("symbol") == bsym
            for t in tool_results
        ):
            tool_results.append(block)

    # Ensure SVG for focus after detect_patterns
    if focus:
        has_svg = any(
            t.get("tool") == "render_pattern_chart" and (t.get("result") or {}).get("symbol") == focus
            for t in tool_results
        )
        if not has_svg and any(
            t.get("tool") == "detect_patterns" and (t.get("result") or {}).get("symbol") == focus
            for t in tool_results
        ):
            tool_results.append(
                {
                    "tool": "render_pattern_chart",
                    "result": await run_tool("render_pattern_chart", {"symbol": focus}),
                }
            )

    critic = await critique_response(message, draft, ctx)
    final = draft
    if critic.get("revised_answer"):
        final = critic["revised_answer"]
    elif critic.get("issues"):
        final = draft + "\n\n(Uwaga wewnętrzna: " + "; ".join(critic["issues"][:2]) + ")"

    desk_ui = build_desk_ui(focus, tool_results)
    meta = {
        "tools": [t.get("tool") for t in tool_results],
        "critic_score": critic.get("score"),
        "llm": llm_configured(),
        "tool_data": _prioritize_tool_data(tool_results, 12),
        "focus_symbol": focus,
        "desk_ui": desk_ui,
    }
    mid = await ai_db.add_message(sid, "assistant", final, meta)
    await ai_db.touch_session(sid, message[:60])

    try:
        from app.ai.self_learn import learn_from_news_exchange

        await learn_from_news_exchange(message, final)
    except Exception:
        pass

    return _pack(sid, final, mid, tool_results, critic.get("score"), len(llm_tool_blocks), focus, desk_ui)


async def _generate(
    message: str,
    history: list[dict],
    tool_context: str,
    focus: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    llm_blocks: list[dict[str, Any]] = []

    if llm_configured():
        try:
            messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
            for h in history[-8:]:
                if h["role"] in ("user", "assistant"):
                    messages.append({"role": h["role"], "content": h["content"][:2000]})
            focus_line = f"\nFocus symbol: {focus}" if focus else ""
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool data:\n{tool_context}{focus_line}\n\nUser question:\n{message}",
                }
            )

            data = await chat_completion(messages, tools=TOOL_DEFINITIONS)
            msg = extract_message(data)
            calls = parse_tool_calls(msg)

            if calls:
                messages.append(msg)
                for call in calls[:5]:
                    fn = call.get("function", {})
                    name = fn.get("name", "")
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if focus and "symbol" not in args and name not in (
                        "get_macro_cycles",
                        "get_singularity_book",
                        "get_paper_portfolio",
                        "search_knowledge",
                    ):
                        args["symbol"] = focus
                    result = await run_tool(name, args)
                    llm_blocks.append({"tool": name, "result": result})
                    payload = result
                    if isinstance(result, dict) and result.get("svg"):
                        payload = {**result, "svg": "[svg omitted — shown in UI]"}
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps(payload, ensure_ascii=False)[:4000],
                        }
                    )
                data2 = await chat_completion(messages)
                return message_content(extract_message(data2)), llm_blocks

            content = message_content(msg)
            if content:
                return content, llm_blocks
        except Exception as exc:
            logger.warning("LLM chat failed, fallback: %s", exc)

    return _compose_fallback(message, tool_context, focus), llm_blocks


def _compose_fallback(message: str, tool_context: str, focus: str | None = None) -> str:
    try:
        # Strip optional "Focus symbol…" prefix before JSON array
        raw = tool_context.lstrip()
        idx = raw.find("[")
        data = json.loads(raw[idx:]) if idx >= 0 else []
    except json.JSONDecodeError:
        data = []

    by_tool = {b.get("tool"): (b.get("result") or {}) for b in data if isinstance(b, dict)}
    trend = by_tool.get("analyze_trend") or {}
    mtf = by_tool.get("analyze_multi_timeframe") or {}
    risk = by_tool.get("risk_snapshot") or {}
    patterns = by_tool.get("detect_patterns") or {}
    mkt = by_tool.get("get_market_context") or {}
    cycles = by_tool.get("get_macro_cycles") or {}

    sym = focus or trend.get("symbol") or patterns.get("symbol") or "—"
    direction = trend.get("trend") or mtf.get("bias") or "neutral"
    strength = float(trend.get("strength") or mtf.get("confluence_score") or 50)
    bias = "Bull" if "up" in str(direction) or str(direction) == "bullish" else (
        "Bear" if "down" in str(direction) or str(direction) == "bearish" else "Neutral"
    )

    value_lens = risk.get("summary") or (
        f"Alokacja: size/stop z risk desk; R:R={risk.get('reward_risk')}"
        if risk.get("reward_risk") is not None
        else "Margin of safety: bez czystego R:R z narzędzi — mniejszy rozmiar lub wait."
    )
    first_lens = (
        f"MTF/trend: {mtf.get('summary') or trend.get('summary') or 'brak pełnej konfluencji'}."
    )
    btc = (cycles.get("bitcoin") or {}) if isinstance(cycles, dict) else {}
    pres = (cycles.get("presidential") or {}) if isinstance(cycles, dict) else {}
    season = (pres.get("seasonality") or {}) if isinstance(pres, dict) else {}
    btc_season = (btc.get("seasonality") or {}) if isinstance(btc, dict) else {}
    spx = (btc.get("spx_comparison") or {}) if isinstance(btc, dict) else {}
    liq_bits = [
        mkt.get("rationale"),
        btc.get("rationale") if isinstance(btc, dict) else None,
        (btc_season.get("expect_now") if isinstance(btc_season, dict) else None),
        (
            f"btc_vs_spx={spx.get('verdict')} regime={spx.get('regime')}"
            if isinstance(spx, dict) and (spx.get("verdict") or spx.get("regime"))
            else None
        ),
        (pres.get("rationale") if isinstance(pres, dict) else None),
        (season.get("expect_now") if isinstance(season, dict) else None),
        (
            f"calendar={pres.get('calendar_season')} month_bias={pres.get('current_month_bias')}"
            if isinstance(pres, dict) and (pres.get("calendar_season") or pres.get("current_month_bias"))
            else None
        ),
        f"macro_phase={mkt.get('macro_phase')}" if mkt.get("macro_phase") else None,
    ]
    liq_lens = " · ".join(str(x) for x in liq_bits if x) or (
        "Płynność/cykl: brak mocnego sygnału makro w tool data — horyzont ostrożny."
    )

    # Soft conflict: MTF vs market signal
    mkt_sig = str(mkt.get("signal") or "").lower()
    if bias == "Bull" and mkt_sig in ("sell", "bear", "avoid"):
        strength = max(25, strength - 20)
    elif bias == "Bear" and mkt_sig in ("buy", "bull"):
        strength = max(25, strength - 20)

    parts = [
        f"**Instrument & bias** — {sym}: {bias} (merged conviction ~{strength:.0f}%)",
        "",
        "**Thesis**",
        trend.get("summary") or mkt.get("rationale") or "Brak pełnych danych trendu — ograniczamy ekspozycję.",
        "",
        "**Council lenses**",
        f"- **Value / Capital**: {value_lens}",
        f"- **First principles / Asymmetry**: {first_lens}",
        f"- **Liquidity & power**: {liq_lens}",
        "",
        "**Setup**",
    ]
    support = patterns.get("support") or []
    resistance = patterns.get("resistance") or []
    if support or resistance:
        parts.append(
            f"Support: {', '.join(str(x) for x in support[:3]) or '—'} · "
            f"Resistance: {', '.join(str(x) for x in resistance[:3]) or '—'}"
        )
    if patterns.get("summary"):
        parts.append(str(patterns["summary"]))
    if risk.get("reward_risk") is not None:
        parts.append(f"R:R (Superokazja): {risk['reward_risk']}")
    if not support and not resistance and not patterns.get("summary"):
        parts.append("Czekaj na czystszy setup — brak wiarygodnych poziomów z narzędzi.")

    parts.extend(["", "**Risk**"])
    if risk.get("summary"):
        parts.append(str(risk["summary"]))
    else:
        parts.append("Ustal stop poza strukturą; nie ryzykuj >1% equity paper bez planu.")

    parts.extend(
        [
            "",
            "**Plan**",
            "Obserwuj konfluencję MTF i sygnał cykliczny; nie doganiaj impulsów bez invalidacji.",
            "",
            "Informacja edukacyjna — nie stanowi porady inwestycyjnej.",
        ]
    )
    return "\n".join(parts)


def _disabled_response(session_id: str | None) -> dict:
    return _pack(session_id or "", "Agent AI jest wyłączony (CYCLICAL_AI_ENABLED=false).", 0, [], None, 0, None, None)


def _pack(
    session_id: str,
    reply: str,
    message_id: int,
    tools: list,
    critic_score: float | None,
    tool_count: int,
    focus_symbol: str | None,
    desk_ui: dict | None = None,
) -> dict:
    return {
        "session_id": session_id,
        "reply": reply,
        "message_id": message_id,
        "tools_used": [t.get("tool") for t in tools] if tools else [],
        "tool_results": tools,
        "critic_score": critic_score,
        "llm_active": llm_configured(),
        "tool_count": tool_count,
        "focus_symbol": focus_symbol,
        "desk_ui": desk_ui,
    }


async def analyze_symbol(symbol: str, locale: str = "pl") -> dict[str, Any]:
    focus = resolve_focus_symbol(symbol, symbol) or symbol.strip()
    tool_results = await build_desk_tool_bundle(focus)
    desk_ui = build_desk_ui(focus, tool_results)
    ctx = f"Focus symbol for this turn: {focus}\n\n" + tools_context_string(tool_results)

    if llm_configured():
        try:
            prompt = (
                f"Pełna analiza Supermind Desk instrumentu {focus}. "
                f"Użyj formatu Instrument & bias / Thesis / Council lenses / Setup / Risk / Plan. Język: {locale}."
            )
            summary = await simple_complete(SYSTEM_PROMPT, f"{prompt}\n\nData:\n{ctx}", temperature=0.35)
            return {
                "symbol": focus,
                "summary": summary,
                "tools": tool_results,
                "llm_active": True,
                "focus_symbol": focus,
                "desk_ui": desk_ui,
            }
        except Exception as exc:
            logger.warning("Analyze symbol LLM failed: %s", exc)

    return {
        "symbol": focus,
        "summary": _compose_fallback(f"analiza {focus}", ctx, focus),
        "tools": tool_results,
        "llm_active": False,
        "focus_symbol": focus,
        "desk_ui": desk_ui,
    }

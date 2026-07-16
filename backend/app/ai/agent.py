"""Finance AI agent orchestrator."""

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
from app.ai.tools import TOOL_DEFINITIONS, auto_tools_for_question, run_tool, tools_context_string
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Cyclical Academy Finance Agent — expert in markets, cycles, technical analysis, macro context.
RULES:
- Answer ONLY finance/markets/trading/cycles/macro questions.
- Use tool data when provided; do not invent prices.
- Combine: trend, patterns, our cyclical signals (BTC cycle, presidential cycle, regional macro, momentum).
- Be concise, structured (bullets ok). Mention uncertainty.
- Always end with: "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
- Never guarantee profits.
Language: match the user's language (Polish/English/German/etc.)."""


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
        return _pack(sid, reply, mid, [], None, 0)

    sid = session_id or await ai_db.create_session(message[:60])
    history = await ai_db.get_messages(sid, limit=settings.ai_max_history_messages)
    await ai_db.add_message(sid, "user", message)

    tool_results = await auto_tools_for_question(message if not symbol else f"{message} {symbol}")
    if symbol:
        for name in ("analyze_trend", "detect_patterns", "get_market_context"):
            tool_results.append({"tool": name, "result": await run_tool(name, {"symbol": symbol})})

    ctx = tools_context_string(tool_results)
    lessons = await ai_db.get_learning_notes(limit=5)
    if lessons:
        ctx += "\n\nLessons from past mistakes:\n" + json.dumps(lessons, ensure_ascii=False)

    draft, tools_used = await _generate(message, history, ctx)

    critic = await critique_response(message, draft, ctx)
    final = draft
    if critic.get("revised_answer"):
        final = critic["revised_answer"]
    elif critic.get("issues"):
        final = draft + "\n\n(Uwaga wewnętrzna: " + "; ".join(critic["issues"][:2]) + ")"

    meta = {
        "tools": [t.get("tool") for t in tool_results],
        "critic_score": critic.get("score"),
        "llm": llm_configured(),
        "tool_data": tool_results[:6],
    }
    mid = await ai_db.add_message(sid, "assistant", final, meta)
    await ai_db.touch_session(sid, message[:60])

    return _pack(sid, final, mid, tool_results, critic.get("score"), len(tools_used))


async def _generate(message: str, history: list[dict], tool_context: str) -> tuple[str, list[str]]:
    tools_used: list[str] = []

    if llm_configured():
        try:
            messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
            for h in history[-8:]:
                if h["role"] in ("user", "assistant"):
                    messages.append({"role": h["role"], "content": h["content"][:2000]})
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool data:\n{tool_context}\n\nUser question:\n{message}",
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
                    result = await run_tool(name, args)
                    tools_used.append(name)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps(result, ensure_ascii=False)[:4000],
                        }
                    )
                data2 = await chat_completion(messages)
                return message_content(extract_message(data2)), tools_used

            content = message_content(msg)
            if content:
                return content, tools_used
        except Exception as exc:
            logger.warning("LLM chat failed, fallback: %s", exc)

    return _compose_fallback(message, tool_context), tools_used


def _compose_fallback(message: str, tool_context: str) -> str:
    try:
        data = json.loads(tool_context) if tool_context.startswith("[") else []
    except json.JSONDecodeError:
        data = []

    parts = ["**Analiza (tryb lokalny — bez klucza OpenAI)**", ""]
    for block in data if isinstance(data, list) else []:
        tool = block.get("tool", "")
        res = block.get("result", {})
        if res.get("summary"):
            parts.append(f"• **{tool}**: {res['summary']}")
        elif res.get("rationale"):
            parts.append(f"• **{tool}**: sygnał {res.get('signal')} ({res.get('confidence')}%) — {res.get('rationale')[:200]}")
        elif res.get("knowledge"):
            for k in res["knowledge"][:2]:
                parts.append(f"• **Wiedza · {k.get('title')}**: {k.get('content')[:180]}…")

    if len(parts) <= 2:
        parts.append("Uruchom analizę podając symbol (np. BTC-USD, AAPL) lub zapytaj o cykl Bitcoina / Fed / wzorce wykresu.")

    parts.append("")
    parts.append("_Aby pełna odpowiedź LLM: ustaw CYCLICAL_OPENAI_API_KEY w .env_")
    parts.append("Informacja edukacyjna — nie stanowi porady inwestycyjnej.")
    return "\n".join(parts)


def _disabled_response(session_id: str | None) -> dict:
    return _pack(session_id or "", "Agent AI jest wyłączony (CYCLICAL_AI_ENABLED=false).", 0, [], None, 0)


def _pack(
    session_id: str,
    reply: str,
    message_id: int,
    tools: list,
    critic_score: float | None,
    tool_count: int,
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
    }


async def analyze_symbol(symbol: str, locale: str = "pl") -> dict[str, Any]:
    sym = symbol.strip()
    tool_results = []
    for name in ("analyze_trend", "detect_patterns", "get_market_context"):
        tool_results.append({"tool": name, "result": await run_tool(name, {"symbol": sym})})
    tool_results.append({"tool": "get_macro_cycles", "result": await run_tool("get_macro_cycles", {})})
    ctx = tools_context_string(tool_results)

    if llm_configured():
        try:
            prompt = f"Pełna analiza instrumentu {sym}. Trend, wzorce, sygnał cykliczny, ryzyko. Język: {locale}."
            summary = await simple_complete(SYSTEM_PROMPT, f"{prompt}\n\nData:\n{ctx}", temperature=0.35)
            return {"symbol": sym, "summary": summary, "tools": tool_results, "llm_active": True}
        except Exception as exc:
            logger.warning("Analyze symbol LLM failed: %s", exc)

    return {
        "symbol": sym,
        "summary": _compose_fallback(f"analiza {sym}", ctx),
        "tools": tool_results,
        "llm_active": False,
    }

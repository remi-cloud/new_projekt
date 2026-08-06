"""Self-critique layer for agent responses."""

from __future__ import annotations

import json
import logging
import re

from app.ai import db as ai_db
from app.ai.llm import llm_configured, simple_complete
from app.config import settings

logger = logging.getLogger(__name__)

CRITIC_SYSTEM = """You are a senior desk risk reviewer checking another AI's draft (Supermind investment committee).
Reject or revise when:
- invents prices/levels not present in tool_data
- omits Council lenses (Value/Capital, First principles/Asymmetry, Liquidity & power) when tool_data includes analyze_trend / risk_snapshot / instrument context
- omits Risk section when tool_data has risk_snapshot / support-resistance / Superokazja levels
- omits Setup levels when detect_patterns or risk_snapshot provided numbers
- impersonates celebrities (“I am Warren…”, “jako Elon…”, “as Rothschild…”)
- overconfident / guarantees profits
- missing educational disclaimer
Return JSON only: {"score": 0-100, "issues": ["..."], "revised_answer": "full revised answer or null", "lesson": "one sentence lesson if mistake pattern detected"}
If revising, keep: Instrument & bias / Thesis / Council lenses / Setup / Risk / Plan + disclaimer."""


async def critique_response(question: str, draft: str, tool_context: str) -> dict:
    if not settings.ai_self_critique_enabled:
        return {"score": 75, "issues": [], "revised_answer": None, "lesson": None}

    if llm_configured():
        try:
            user = json.dumps(
                {"question": question, "draft": draft[:4000], "tool_data": tool_context[:3500]},
                ensure_ascii=False,
            )
            raw = await simple_complete(CRITIC_SYSTEM, user, temperature=0.2)
            match = re.search(r"\{.*\}", raw, re.S)
            if match:
                parsed = json.loads(match.group())
                lesson = parsed.get("lesson")
                if lesson and isinstance(lesson, str) and len(lesson) > 10:
                    await ai_db.add_learning_note("self_critique", lesson, source="critic", confidence=0.72)
                return parsed
        except Exception as exc:
            logger.warning("LLM critic failed: %s", exc)

    result = _rule_critic(draft, tool_context)
    if result.get("lesson"):
        await ai_db.add_learning_note("self_critique", result["lesson"], source="critic_rules", confidence=0.65)
    return result


def _rule_critic(draft: str, tool_context: str = "") -> dict:
    issues = []
    low = draft.lower()
    ctx = (tool_context or "").lower()
    if "gwarant" in low or "pewny zysk" in low or "guaranteed" in low:
        issues.append("Overconfident language detected")
    if "nie stanowi" not in low and "not investment advice" not in low and "edukacyj" not in low:
        issues.append("Missing educational disclaimer")
    if re.search(r"\b(i am|i'm|jestem)\b.{0,40}\b(warren|buffett|elon|musk|rothschild)\b", low):
        issues.append("Celebrity impersonation detected")
    if re.search(r"\bjako\s+(warren|buffett|elon|musk|rothschild)\b", low):
        issues.append("Celebrity impersonation detected")

    has_desk = any(
        k in ctx
        for k in (
            "analyze_trend",
            "risk_snapshot",
            "detect_patterns",
            "analyze_multi_timeframe",
        )
    )
    if has_desk:
        has_council = "council" in low or "soczew" in low
        has_value = "value" in low or "capital" in low or "margin of safety" in low or "alokac" in low
        has_first = "first principle" in low or "asymmetr" in low or "pierwsz" in low
        has_liq = "liquidity" in low or "płynność" in low or "plynnosc" in low or "liquidity & power" in low or "power" in low
        if not (has_council or (has_value and has_first and has_liq)):
            issues.append("Missing Council lenses (Value / First principles / Liquidity)")

    has_levels = any(
        k in ctx
        for k in (
            "support",
            "resistance",
            "suggested_stop",
            "risk_snapshot",
            "geometry",
            "\"levels\"",
        )
    )
    if has_levels and "risk" not in low and "ryzyk" not in low:
        issues.append("Missing Risk section despite tool risk/levels data")
    if has_levels and "setup" not in low and "invalid" not in low and "support" not in low and "opór" not in low:
        issues.append("Missing Setup/levels discussion despite tool levels")

    has_season = "seasonality" in ctx or "calendar_season" in ctx or "month_returns" in ctx
    if has_season:
        mentions_season = any(
            x in low
            for x in (
                "sezon",
                "season",
                "best six",
                "xi–iv",
                "nov",
                "miesiąc",
                "month",
                "midterm",
                "kadenc",
                "year 2",
                "rok 2",
                "y2",
                "ath",
                "364",
                "1064",
                "spx",
                "s&p",
                "regime",
                "equity_beta",
            )
        )
        if not mentions_season:
            issues.append(
                "Missing seasonality discussion despite get_macro_cycles seasonality data "
                "(US month/term and/or BTC month + vs-SPX)"
            )

    score = max(30, 90 - len(issues) * 12)
    lesson = None
    if issues:
        lesson = (
            "Supermind desk: Council lenses + Setup + Risk z tool data; "
            "dla US cytuj sezonowość miesiąca/kadencji; dla BTC fazę ATH + bias miesiąca + vs SPX; "
            "bez impersonacji; bez gwarancji zysku; disclaimer edukacyjny."
        )
    return {"score": score, "issues": issues, "revised_answer": None, "lesson": lesson}

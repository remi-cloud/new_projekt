"""Self-critique layer for agent responses."""

from __future__ import annotations

import json
import logging
import re

from app.ai import db as ai_db
from app.ai.llm import llm_configured, simple_complete
from app.config import settings

logger = logging.getLogger(__name__)

CRITIC_SYSTEM = """You are a senior financial analyst reviewing another AI's draft answer.
Evaluate ONLY for: factual caution, finance relevance, missing risk disclaimer, overconfidence, ignoring cycle context.
Return JSON only: {"score": 0-100, "issues": ["..."], "revised_answer": "..." or null if draft is fine, "lesson": "one sentence lesson if mistake pattern detected"}"""


async def critique_response(question: str, draft: str, tool_context: str) -> dict:
    if not settings.ai_self_critique_enabled:
        return {"score": 75, "issues": [], "revised_answer": None, "lesson": None}

    if llm_configured():
        try:
            user = json.dumps(
                {"question": question, "draft": draft[:4000], "tool_data": tool_context[:3000]},
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

    return _rule_critic(draft)


def _rule_critic(draft: str) -> dict:
    issues = []
    low = draft.lower()
    if "gwarant" in low or "pewny zysk" in low or "guaranteed" in low:
        issues.append("Overconfident language detected")
    if "nie stanowi" not in low and "not investment advice" not in low and "edukacyj" not in low:
        issues.append("Missing educational disclaimer")
    score = max(40, 85 - len(issues) * 15)
    lesson = None
    if issues:
        lesson = "Unikaj języka gwarancji zysku; zawsze dodaj disclaimer edukacyjny."
    return {"score": score, "issues": issues, "revised_answer": None, "lesson": lesson}

"""Finance-agent lessons share the desk store and are injected into the next prompt."""

from __future__ import annotations

from app.solana_desk.learning.memory import for_agent, save_lesson
from app.solana_desk.store import ensure_schema


async def note_correction(question: str, correction: str) -> dict:
    await ensure_schema()
    text = correction.strip()
    return await save_lesson(
        agent="llm",
        trigger="correction",
        evidence={"question": question[:240]},
        diagnosis="user correction",
        lesson_text=text[:500],
        rule={"when": [], "action": {"type": "require_check", "param": "prompt", "value": None, "factor": None}},
        source="rule",
        confidence=0.85,
        deterministic=True,
    )


async def finance_lesson_prompt() -> str:
    await ensure_schema()
    rows = await for_agent("llm", ("active", "shadow"))
    if not rows:
        return ""
    lines = [f"LESSON #{row['id']}: {row.get('lesson_text')}" for row in rows]
    return "Desk lessons (apply; do not loosen risk limits):\n" + "\n".join(lines)


async def inject_finance_lessons(ctx: str) -> str:
    block = await finance_lesson_prompt()
    if not block:
        return ctx
    return f"{ctx}\n\n{block}" if ctx else block

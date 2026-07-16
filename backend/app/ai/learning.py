"""Process user feedback into learning notes."""

from __future__ import annotations

import logging

from app.ai import db as ai_db
from app.ai.llm import llm_configured, simple_complete

logger = logging.getLogger(__name__)


async def process_feedback(rating: int, question: str, answer: str, correction: str | None) -> None:
    if rating >= 4:
        return
    if correction and len(correction.strip()) > 10:
        await ai_db.add_learning_note(
            topic="user_correction",
            lesson=f"Przy pytaniu: {question[:200]} → poprawka użytkownika: {correction[:500]}",
            source="user_feedback",
            confidence=0.85,
        )
        return

    if llm_configured() and rating <= 2:
        try:
            lesson = await simple_complete(
                "Extract one short lesson for a finance AI from this failed answer. One sentence, Polish or English.",
                f"Q: {question[:500]}\nA: {answer[:800]}",
                temperature=0.2,
            )
            if lesson and len(lesson) > 15:
                await ai_db.add_learning_note("feedback", lesson[:500], source="user_feedback", confidence=0.8)
        except Exception as exc:
            logger.warning("Feedback lesson extraction failed: %s", exc)

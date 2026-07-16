from fastapi import APIRouter, HTTPException

from app.ai import agent as ai_agent
from app.ai import db as ai_db
from app.ai.learning import process_feedback
from app.ai.llm import llm_configured
from app.config import settings
from app.models.schemas import (
    AiAnalyzeResponse,
    AiChatRequest,
    AiChatResponse,
    AiFeedbackRequest,
    AiStatusResponse,
)

router = APIRouter(tags=["ai"])


@router.get("/api/ai/status", response_model=AiStatusResponse)
async def ai_status():
    stats = await ai_db.get_stats()
    return AiStatusResponse(
        enabled=settings.ai_enabled,
        llm_configured=llm_configured(),
        model=settings.openai_model,
        features=[
            "finance_guard",
            "trend_analysis",
            "pattern_detection",
            "knowledge_base",
            "self_critique",
            "learning_from_feedback",
            "macro_cycles",
            "news_image_agent",
        ],
        knowledge_entries=stats["knowledge_entries"],
        learning_notes=stats["learning_notes"],
    )


@router.post("/api/ai/chat", response_model=AiChatResponse)
async def ai_chat(body: AiChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message required")
    result = await ai_agent.chat(
        message=body.message.strip(),
        session_id=body.session_id,
        locale=body.locale or "pl",
        symbol=body.symbol,
    )
    return AiChatResponse(**result)


@router.post("/api/ai/feedback")
async def ai_feedback(body: AiFeedbackRequest):
    await ai_db.add_feedback(body.session_id, body.message_id, body.rating, body.correction)
    if body.rating <= 3 and body.question and body.answer:
        await process_feedback(body.rating, body.question, body.answer, body.correction)
    return {"saved": True}


@router.get("/api/ai/history")
async def ai_history(session_id: str, limit: int = 40):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    messages = await ai_db.get_messages(session_id, limit=min(limit, 80))
    return {"session_id": session_id, "messages": messages}


@router.post("/api/ai/analyze/{symbol}", response_model=AiAnalyzeResponse)
async def ai_analyze_symbol(symbol: str, lang: str | None = None):
    result = await ai_agent.analyze_symbol(symbol, locale=lang or "pl")
    return AiAnalyzeResponse(**result)

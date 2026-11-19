from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Request

from app.ai import agent as ai_agent
from app.ai.visibility import desk_portfolio_visible
from app.desk_auth import supplied_desk_token, tokens_match
from app.ai import db as ai_db
from app.ai.learning import process_feedback
from app.ai.academy import academy_payload
from app.ai.llm import active_llm_target, free_chain_labels, redact_secrets
from app.config import settings
from app.models.schemas import (
    AiAnalyzeResponse,
    AiChatRequest,
    AiChatResponse,
    AiFeedbackRequest,
    AiStatusResponse,
)

router = APIRouter(tags=["ai"])

_DISABLED_DETAIL = "Agent AI jest wyłączony (CYCLICAL_AI_ENABLED=false)."


def _public_base_url(url: str) -> str:
    """Base URL safe to show. Local daemons and embedded secrets stay off the wire."""
    raw = redact_secrets((url or "").strip())
    if not raw:
        return ""
    if raw.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]", "http://0.0.0.0")):
        return ""
    parts = urlsplit(raw)
    if parts.username or parts.password or parts.query:
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        path = parts.path if "[redacted]" not in parts.path else ""
        return urlunsplit((parts.scheme, f"{host}{port}", path, "", ""))
    if "[redacted]" in raw:
        return ""
    return raw


def _ai_disabled() -> HTTPException:
    return HTTPException(status_code=503, detail=_DISABLED_DETAIL)


def _desk_open(request: Request) -> bool:
    expected = (settings.desk_token or "").strip()
    supplied = supplied_desk_token(request)
    return bool(expected and supplied and tokens_match(supplied, expected))


@router.get("/api/ai/academy")
async def ai_academy():
    """Educational brief for the AI & security page. Static copy, no secrets."""
    return academy_payload()


@router.get("/api/ai/status", response_model=AiStatusResponse)
async def ai_status():
    stats = await ai_db.get_stats()
    target = active_llm_target()
    # A real target is a keyed provider, an opted-in llm7 chain, or explicit Ollama.
    # A default local URL with nothing listening is not configured.
    configured = bool(settings.ai_enabled and target)
    provider = target.provider if target else "none"
    model = redact_secrets(target.model) if target else ""
    if model == "[redacted]":
        model = ""
    has_paid_key = bool(
        (getattr(settings, "xai_api_key", "") or "").strip() or (settings.openai_api_key or "").strip()
    )
    if target and target.provider in {"llm7", "ollama"}:
        requires_api_key = False
    else:
        requires_api_key = not has_paid_key
    labels = [redact_secrets(label) for label in free_chain_labels()]
    return AiStatusResponse(
        enabled=settings.ai_enabled,
        llm_configured=configured,
        model=model,
        provider=provider if provider in {"xai", "openai", "llm7", "ollama"} else "none",
        base_url=_public_base_url(target.base_url if target else ""),
        requires_api_key=requires_api_key,
        free_chain=[label for label in labels if "[redacted]" not in label],
        features=[
            "finance_guard",
            "trend_analysis",
            "pattern_detection",
            "knowledge_base",
            "self_critique",
            "self_learn",
            "learn_from_news_chat",
            "learning_from_feedback",
            "macro_cycles",
            "news_image_agent",
            "free_llm7",
        ],
        knowledge_entries=stats["knowledge_entries"],
        learning_notes=stats["learning_notes"],
    )


@router.post("/api/ai/chat", response_model=AiChatResponse)
async def ai_chat(body: AiChatRequest, request: Request):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message required")
    if not settings.ai_enabled:
        raise _ai_disabled()
    token = desk_portfolio_visible.set(_desk_open(request))
    try:
        result = await ai_agent.chat(
            message=body.message.strip(),
            session_id=body.session_id,
            locale=body.locale or "pl",
            symbol=body.symbol,
        )
    except RuntimeError:
        # Missing keys are a 200 local fallback inside the agent. 503 is only
        # the explicit CYCLICAL_AI_ENABLED=false switch above.
        raise HTTPException(status_code=502, detail="Czat AI nie odpowiedział.") from None
    finally:
        desk_portfolio_visible.reset(token)
    return AiChatResponse(**result)


@router.post("/api/ai/feedback")
async def ai_feedback(body: AiFeedbackRequest):
    await ai_db.add_feedback(body.session_id, body.message_id, body.rating, body.correction)
    await process_feedback(
        body.rating,
        body.question or "",
        body.answer or "",
        body.correction,
        session_id=body.session_id,
        message_id=body.message_id,
    )
    stats = await ai_db.get_stats()
    return {"saved": True, "learning_notes": stats["learning_notes"]}


@router.get("/api/ai/history")
async def ai_history(session_id: str, limit: int = 40):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    messages = await ai_db.get_messages(session_id, limit=min(limit, 80))
    return {"session_id": session_id, "messages": messages}


@router.post("/api/ai/analyze/{symbol}", response_model=AiAnalyzeResponse)
async def ai_analyze_symbol(symbol: str, request: Request, lang: str | None = None):
    # Not a public write. Guests get 401 from desk auth; the page hides the button.
    # Chat stays the guest path and answers from local tools when no key is set.
    if not settings.ai_enabled:
        raise _ai_disabled()
    token = desk_portfolio_visible.set(_desk_open(request))
    try:
        result = await ai_agent.analyze_symbol(symbol, locale=lang or "pl")
    finally:
        desk_portfolio_visible.reset(token)
    return AiAnalyzeResponse(**result)

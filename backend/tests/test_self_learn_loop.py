"""A wrong call or a thumbs-down becomes a lesson, and the next answer obeys it."""

import pytest

from app.ai.learning import (
    apply_learned_corrections,
    lesson_from_thumbs_down,
    process_feedback,
    review_predictions,
)


def _bull_reply() -> str:
    return "\n".join(
        [
            "**Instrument & bias** — BTC-USD: Bull (merged conviction ~80%)",
            "",
            "**Thesis**",
            "up",
            "",
            "Asymmetric bet: R:R=2.5 → ACCEPT (przy konfluencji).",
        ]
    )


@pytest.mark.asyncio
async def test_price_postmortem_corrects_the_next_answer():
    from app.ai import db as ai_db

    await ai_db.init_ai_db()
    await ai_db.record_market_call("BTC-USD", "bull", 100.0, "sess")
    result = await review_predictions({"BTC-USD": 90.0})
    assert result["wrong"] == 1
    notes = await ai_db.get_learning_notes(limit=40)
    mine = [note for note in notes if note.get("symbol") == "BTC-USD" and note["source"] == "postmortem"]
    assert mine
    assert "WAIT" in mine[0]["lesson"]
    corrected, applied = apply_learned_corrections(_bull_reply(), notes, "BTC-USD")
    assert applied
    assert "Lekcja z błędu:" in corrected
    assert "ACCEPT (przy konfluencji)" not in corrected
    assert "Bull" not in corrected.split("Lekcja z błędu:", 1)[-1].split("**Thesis**", 1)[0]


@pytest.mark.asyncio
async def test_thumbs_down_stores_a_lesson_without_a_model(monkeypatch):
    from app.ai import db as ai_db
    from app.config import settings

    await ai_db.init_ai_db()
    monkeypatch.setattr(settings, "xai_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    text, symbol = lesson_from_thumbs_down("trend BTC-USD", _bull_reply(), None)
    assert symbol == "BTC-USD"
    assert "kciuk w dół" in text
    await process_feedback(1, "trend BTC-USD", _bull_reply(), None, session_id="s", message_id=None)
    notes = await ai_db.get_learning_notes(limit=40)
    assert any(note["source"] == "user_feedback" and note.get("symbol") == "BTC-USD" for note in notes)


@pytest.mark.asyncio
async def test_lesson_that_does_not_help_is_retired():
    from app.ai import db as ai_db

    await ai_db.init_ai_db()
    await ai_db.add_learning_note(
        topic="mistake:ZZZ-USD",
        lesson="Nie powtarzaj bull na ZZZ-USD: test. Następna odpowiedź: WAIT, mniejszy size.",
        source="postmortem",
        confidence=0.9,
        symbol="ZZZ-USD",
    )
    notes = [note for note in await ai_db.get_learning_notes(limit=40) if note.get("symbol") == "ZZZ-USD"]
    assert len(notes) == 1
    note_id = int(notes[0]["id"])
    assert await ai_db.mark_lesson_outcome(note_id, helpful=False) is False
    assert await ai_db.mark_lesson_outcome(note_id, helpful=False) is True
    left = [note for note in await ai_db.get_learning_notes(limit=40) if note.get("symbol") == "ZZZ-USD"]
    assert left == []
    reply, applied = apply_learned_corrections(_bull_reply().replace("BTC-USD", "ZZZ-USD"), left, "ZZZ-USD")
    assert applied == []
    assert "Bull" in reply


@pytest.mark.asyncio
async def test_chat_does_not_repeat_a_bull_call_after_the_price_drops(client, monkeypatch):
    async def bundle(symbol):
        price = 90.0 if bundle.calls else 100.0
        bundle.calls += 1
        return [
            {
                "tool": "analyze_trend",
                "result": {
                    "symbol": symbol,
                    "trend": "uptrend",
                    "strength": 80,
                    "summary": "up",
                    "source": "binance",
                },
            },
            {
                "tool": "risk_snapshot",
                "result": {"symbol": symbol, "price": price, "reward_risk": 2.5, "summary": "rr 2.5"},
            },
        ]

    async def extras(*_args, **_kwargs):
        return []

    bundle.calls = 0
    monkeypatch.setattr("app.ai.agent.build_desk_tool_bundle", bundle)
    monkeypatch.setattr("app.ai.agent.auto_tools_for_question", extras)
    monkeypatch.setattr("app.config.settings.xai_api_key", "")
    monkeypatch.setattr("app.config.settings.openai_api_key", "")
    monkeypatch.setattr("app.config.settings.ai_external_enabled", False)
    first = client.post(
        "/api/ai/chat",
        json={"message": "Jaki jest trend SOL-USD?", "symbol": "SOL-USD"},
    )
    assert first.status_code == 200
    body = first.json()
    assert body["llm_active"] is False
    assert body["critic_score"] is None
    assert "ACCEPT" in body["reply"]
    second = client.post(
        "/api/ai/chat",
        json={
            "message": "Jaki jest trend SOL-USD?",
            "symbol": "SOL-USD",
            "session_id": body["session_id"],
        },
    )
    assert second.status_code == 200
    reply = second.json()["reply"]
    assert "Lekcja z błędu" in reply
    assert "ACCEPT (przy konfluencji)" not in reply
    assert "WAIT" in reply
    status = client.get("/api/ai/status")
    assert status.status_code == 200
    assert status.json()["learning_notes"] >= 1

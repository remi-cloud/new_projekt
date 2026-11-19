"""Turn a bad call or a thumbs-down into a lesson the next answer has to follow."""

from __future__ import annotations

import logging
import re

from app.ai import db as ai_db
from app.ai.llm import llm_configured, simple_complete

logger = logging.getLogger(__name__)

MISTAKE_MOVE_PCT = 3.0
_WAIT = "Następna odpowiedź: WAIT, mniejszy size."
_BIAS_BULL = re.compile(r"(—\s*[A-Z0-9^=.\-]{2,16}\s*:\s*)Bull\b")


def extract_focus(question: str, answer: str) -> str | None:
    match = re.search(r"—\s*([A-Z0-9^=.\-]{2,16})\s*:", answer or "")
    if match:
        return match.group(1)
    match = re.search(
        r"\b([A-Z]{2,5}-USD|\^[A-Z0-9.]+|[A-Z]{2,6}=X|[A-Z]{2,6}\.WA)\b",
        f"{question or ''} {answer or ''}",
    )
    return match.group(1) if match else None


def stance_from_reply(reply: str) -> str | None:
    if "Lekcja z błędu:" in (reply or "") and "WAIT" in reply:
        return "wait"
    if _BIAS_BULL.search(reply or "") or "ACCEPT (przy konfluencji)" in (reply or "") or "→ ACCEPT" in (reply or ""):
        return "bull"
    if re.search(r"—\s*[A-Z0-9^=.\-]{2,16}\s*:\s*Bear\b", reply or "") or "REJECT" in (reply or ""):
        return "bear"
    if "WAIT" in (reply or ""):
        return "wait"
    return None


def lesson_from_thumbs_down(question: str, answer: str, correction: str | None) -> tuple[str, str | None]:
    """Concrete rule, no model required."""
    symbol = extract_focus(question, answer)
    fix = (correction or "").strip()
    where = f" na {symbol}" if symbol else ""
    if fix:
        text = f"Nie powtarzaj odrzuconej tezy{where}: {fix[:400]}. {_WAIT}"
    else:
        text = (
            f"Nie powtarzaj odrzuconej tezy{where}: użytkownik dał kciuk w dół. "
            f"Poprzednia odpowiedź nie przeszła. {_WAIT}"
        )
    return text, symbol


def apply_learned_corrections(
    reply: str,
    lessons: list[dict],
    symbol: str | None,
) -> tuple[str, list[int]]:
    """Rewrite a fresh draft when a stored mistake says the next call is WAIT."""
    wanted = (symbol or "").upper()
    matched: list[dict] = []
    for note in lessons:
        if note.get("retired"):
            continue
        text = str(note.get("lesson") or "")
        if _WAIT not in text and "Następna odpowiedź: WAIT" not in text:
            continue
        note_symbol = str(note.get("symbol") or "").upper()
        if wanted and note_symbol and note_symbol != wanted:
            continue
        if wanted and not note_symbol and wanted not in text.upper():
            continue
        if not wanted and note_symbol:
            continue
        matched.append(note)
    if not matched:
        return reply, []
    matched.sort(key=lambda note: int(note.get("id") or 0), reverse=True)
    top = matched[0]
    out = _BIAS_BULL.sub(r"\1Neutral", reply or "")
    out = out.replace("ACCEPT (przy konfluencji)", "WAIT")
    out = out.replace("ACCEPT ostrożny / OK", "WAIT")
    line = f"Lekcja z błędu: {top.get('lesson')}"
    if line not in out:
        out = f"{line}\n\n{out}"
    ids = [int(note["id"]) for note in matched if note.get("id") is not None]
    return out, ids


def _call_was_wrong(stance: str, before: float, after: float) -> bool:
    if before <= 0:
        return False
    move = (after - before) / before * 100
    if stance in {"bull", "accept"}:
        return move <= -MISTAKE_MOVE_PCT
    if stance in {"bear", "reject"}:
        return move >= MISTAKE_MOVE_PCT
    return False


async def review_predictions(prices: dict[str, float] | None = None) -> dict:
    """Check open calls against later prices. A wrong call becomes one lesson."""
    book = {str(key).upper(): float(value) for key, value in (prices or {}).items() if value is not None}
    if not book:
        try:
            from app.scanners.opportunity_scanner import scanner

            for quote in scanner.quotes or []:
                book[str(quote.symbol).upper()] = float(quote.price)
        except Exception as exc:
            logger.debug("Prediction review has no prices: %s", type(exc).__name__)
    checked = 0
    wrong = 0
    added = 0
    for call in await ai_db.open_market_calls():
        later = book.get(str(call["symbol"]).upper())
        if later is None:
            continue
        checked += 1
        before = float(call["price"])
        stance = str(call["stance"])
        if _call_was_wrong(stance, before, later):
            wrong += 1
            lesson = (
                f"Nie powtarzaj {stance} na {call['symbol']}: cena {before:.4g} "
                f"poszła do {later:.4g}. {_WAIT}"
            )
            if await ai_db.add_learning_note(
                topic=f"mistake:{call['symbol']}",
                lesson=lesson,
                source="postmortem",
                confidence=0.9,
                symbol=str(call["symbol"]),
            ):
                added += 1
            await ai_db.close_market_call(int(call["id"]), "wrong")
        else:
            await ai_db.close_market_call(int(call["id"]), "ok")
    return {"checked": checked, "wrong": wrong, "added": added}


async def process_feedback(
    rating: int,
    question: str,
    answer: str,
    correction: str | None,
    session_id: str | None = None,
    message_id: int | None = None,
) -> None:
    meta = await ai_db.get_message_meta(session_id or "", message_id)
    applied: list[int] = []
    for item in meta.get("applied_lesson_ids") or []:
        try:
            applied.append(int(item))
        except (TypeError, ValueError):
            continue
    if rating >= 4:
        for note_id in applied:
            await ai_db.mark_lesson_outcome(note_id, helpful=True)
        if llm_configured() and answer and len(answer) > 40:
            try:
                lesson = await simple_complete(
                    "Extract ONE reusable strength from this good finance answer as a short lesson "
                    "(what pattern/approach to repeat). One sentence.",
                    f"Q: {question[:500]}\nA: {answer[:900]}",
                    temperature=0.15,
                )
                if lesson and len(lesson.strip()) > 15:
                    await ai_db.add_learning_note(
                        "positive_feedback",
                        lesson.strip()[:500],
                        source="user_feedback_pos",
                        confidence=0.82,
                    )
            except Exception as exc:
                logger.debug("Positive feedback learn failed: %s", type(exc).__name__)
        return

    for note_id in applied:
        await ai_db.mark_lesson_outcome(note_id, helpful=False)

    if rating > 2 and not (correction and len(correction.strip()) > 10):
        return

    text, symbol = lesson_from_thumbs_down(question, answer, correction)
    await ai_db.add_learning_note(
        topic=f"mistake:{symbol or 'general'}",
        lesson=text,
        source="user_feedback",
        confidence=0.88,
        symbol=symbol,
    )

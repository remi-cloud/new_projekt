"""Autonomous self-learning — distill market/news/calendar into durable lessons."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from app.ai import db as ai_db
from app.ai.llm import llm_configured, simple_complete
from app.config import settings

logger = logging.getLogger(__name__)

_LEARN_SYSTEM = """You are the self-learning loop for Cyclical Trader Kar Digital finance agent.
From the market snapshot below, extract SHORT durable lessons the agent must remember
for future answers (macro, cycles, risk, Fed/CPI/NFP, Trump/Musk/stagflation tape when relevant).

Return ONLY JSON:
{"lessons":[{"topic":"short_topic","lesson":"one concrete sentence","confidence":0.0-1.0}]}

Rules:
- Concrete, actionable for a trading desk AI (not fluff, no generic "be careful").
- Prefer regime / risk / data-surprise / calendar-skew lessons.
- Prefer NEW angles not already listed under EXISTING_LESSONS.
- Language: Polish if input is mostly Polish, else English.
- Max lessons as requested. No markdown."""


async def _collect_context() -> str:
    bits: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    bits.append(f"as_of_utc={now}")

    try:
        from app.news.macro_news import get_macro_news

        feed = await get_macro_news(category="all", limit=18, locale="pl")
        headlines = [
            f"[{n.category}] {n.title}" + (f" — {(n.summary or '')[:100]}" if n.summary else "")
            for n in feed.items[:14]
        ]
        if headlines:
            bits.append("NEWS:\n" + "\n".join(headlines))
    except Exception as exc:
        logger.debug("Self-learn news context failed: %s", exc)

    try:
        from app.news.macro_calendar import get_upcoming_calendar
        from app.news.calendar_ai import enrich_calendar_events

        events = await enrich_calendar_events(get_upcoming_calendar(locale="pl")[:6], locale="pl")
        cal_lines = []
        for e in events:
            line = f"{e.event_date} {e.title} bias={e.ai_bias}"
            if e.current_state:
                line += f" | state: {e.current_state[:140]}"
            if e.expectations:
                line += f" | expect: {e.expectations[:140]}"
            cal_lines.append(line)
        if cal_lines:
            bits.append("CALENDAR:\n" + "\n".join(cal_lines))
    except Exception as exc:
        logger.debug("Self-learn calendar context failed: %s", exc)

    try:
        from app.scanners.opportunity_scanner import scanner

        opps = sorted(
            scanner.opportunities or [],
            key=lambda o: (getattr(o, "is_momentum_pick", False), getattr(o, "confidence", 0)),
            reverse=True,
        )[:5]
        if opps:
            bits.append(
                "TOP_OPPS:\n"
                + "\n".join(
                    f"{o.symbol} {getattr(o.action, 'value', o.action)} conf={o.confidence} phase={o.phase}"
                    for o in opps
                )
            )
        if scanner.bitcoin_cycle:
            b = scanner.bitcoin_cycle
            spx = getattr(b, "spx_comparison", None)
            bits.append(
                "BTC_CYCLE: "
                f"phase={getattr(b.phase, 'value', b.phase)} "
                f"days_since_ath={getattr(b, 'days_since_ath', None)} "
                f"month_bias={getattr(b, 'current_month_bias', None)} "
                f"vs_spx={getattr(spx, 'verdict', None)} "
                f"regime={getattr(spx, 'regime', None)}"
            )
    except Exception as exc:
        logger.debug("Self-learn scanner context failed: %s", exc)

    try:
        from app.paper.portfolio_memory import get_agent_portfolio_context

        paper = await get_agent_portfolio_context()
        bits.append(
            "PAPER_PORTFOLIO (session desk):\n"
            + f"cash={paper.get('cash_pln')} equity={paper.get('total_equity_pln')} "
            + f"positions={paper.get('positions_count')} "
            + f"open={[p.get('symbol') for p in (paper.get('positions') or [])]}"
        )
    except Exception as exc:
        logger.debug("Self-learn portfolio context failed: %s", exc)

    existing = await ai_db.get_learning_notes(limit=6)
    if existing:
        bits.append(
            "EXISTING_LESSONS (avoid duplicates):\n"
            + "\n".join(f"- {n['lesson'][:120]}" for n in existing)
        )

    return "\n\n".join(bits)


def _parse_lessons(raw: str) -> list[dict]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    lessons = data.get("lessons") if isinstance(data, dict) else None
    if not isinstance(lessons, list):
        return []
    out: list[dict] = []
    max_n = max(1, min(8, int(getattr(settings, "ai_self_learn_max_lessons", 5) or 5)))
    for item in lessons[:max_n]:
        if not isinstance(item, dict):
            continue
        lesson = str(item.get("lesson") or "").strip()
        if len(lesson) < 15:
            continue
        topic = str(item.get("topic") or "market").strip()[:80] or "market"
        try:
            conf = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        out.append({"topic": topic, "lesson": lesson, "confidence": max(0.4, min(0.92, conf))})
    return out


async def learn_from_news_exchange(question: str, answer: str) -> bool:
    """Distill one lesson after a user-driven news/instrument analysis chat."""
    if not getattr(settings, "ai_learn_from_news_chat", True):
        return False
    if not llm_configured():
        return False
    q = (question or "").lower()
    markers = ("przeanalizuj ten news", "analyze this news", "desk trading", "trading desk", "tytuł:", "title:")
    if not any(m in q for m in markers):
        return False
    try:
        lesson = await simple_complete(
            "Extract ONE durable market lesson from this news analysis. One sentence. "
            "Focus on regime/risk/calendar implication. Polish if question is Polish.",
            f"Q:\n{question[:1200]}\n\nA:\n{answer[:1600]}",
            temperature=0.15,
        )
        text = (lesson or "").strip()
        if len(text) < 20:
            return False
        return await ai_db.add_learning_note(
            topic="news_analysis",
            lesson=text[:500],
            source="news_chat",
            confidence=0.78,
        )
    except Exception as exc:
        logger.debug("News-chat learn failed: %s", exc)
        return False


async def run_self_learn_cycle() -> dict:
    """One autonomous learning tick. Safe to call from scheduler."""
    if not settings.ai_enabled or not settings.ai_self_learn_enabled:
        return {"ok": False, "reason": "disabled", "added": 0}
    if not llm_configured():
        return {"ok": False, "reason": "llm_not_configured", "added": 0}

    ctx = await _collect_context()
    if len(ctx) < 80:
        return {"ok": False, "reason": "thin_context", "added": 0}

    max_n = max(1, min(8, int(getattr(settings, "ai_self_learn_max_lessons", 5) or 5)))
    try:
        raw = await simple_complete(
            _LEARN_SYSTEM + f"\n\nExtract up to {max_n} lessons.",
            ctx[:9000],
            temperature=0.18,
        )
        lessons = _parse_lessons(raw)
    except Exception as exc:
        logger.warning("Self-learn LLM failed: %s", exc)
        return {"ok": False, "reason": str(exc), "added": 0}

    added = 0
    for item in lessons:
        ok = await ai_db.add_learning_note(
            topic=item["topic"],
            lesson=item["lesson"],
            source="self_learn",
            confidence=item["confidence"],
        )
        if ok:
            added += 1

    logger.info("Self-learn cycle: proposed=%d added=%d", len(lessons), added)
    return {"ok": True, "proposed": len(lessons), "added": added}

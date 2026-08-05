"""AI desk assessment for macro calendar events — current state + expectations."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from app.ai.llm import llm_configured, llm_provider, simple_complete
from app.config import settings
from app.models.schemas import MacroCalendarEvent

logger = logging.getLogger(__name__)

_CACHE: dict[str, MacroCalendarEvent] = {}
_CACHE_LOCK = asyncio.Lock()
_SEM = asyncio.Semaphore(4)

_SYSTEM = """You are a macro trading desk analyst for Cyclical Trader Kar Digital.
Given a scheduled macro event, assess the CURRENT market state right now and the
EXPECTATIONS / consensus ahead of the print (or what markets will watch if already passed).

Reply with ONLY valid JSON (no markdown):
{
  "current_state": "2-3 short sentences in the requested language — what the tape shows now (rates, USD, risk, inflation narrative)",
  "expectations": "2-3 short sentences — consensus / base case / what would surprise hawkish vs dovish",
  "bias": "hawkish|dovish|neutral|risk_on|risk_off",
  "confidence": 0-100
}
Be concrete. No investment advice disclaimer fluff. No invented exact CPI prints unless clearly labeled as typical/prior context."""


def _cache_key(event: MacroCalendarEvent, locale: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")  # refresh roughly hourly
    return f"{event.id}|{locale}|{day}"


async def _market_snapshot() -> str:
    """Lightweight Yahoo snapshot for AI context (best-effort)."""
    symbols = ["^TNX", "DX-Y.NYB", "CL=F", "GC=F", "BTC-USD"]
    lines: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "CyclicalTrader/1.0"}) as client:
            for sym in symbols:
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                    resp = await client.get(url, params={"range": "5d", "interval": "1d"})
                    resp.raise_for_status()
                    result = (resp.json().get("chart") or {}).get("result") or []
                    if not result:
                        continue
                    meta = result[0].get("meta") or {}
                    price = meta.get("regularMarketPrice")
                    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                    if price is None:
                        continue
                    chg = ""
                    if prev:
                        pct = (float(price) - float(prev)) / float(prev) * 100
                        chg = f" ({pct:+.2f}%)"
                    lines.append(f"{sym}={float(price):.4g}{chg}")
                except Exception:
                    continue
    except Exception as exc:
        logger.debug("Market snapshot failed: %s", exc)
    return ", ".join(lines) if lines else "snapshot unavailable"


def _heuristic(event: MacroCalendarEvent, locale: str) -> MacroCalendarEvent:
    """Rule-based fallback when OpenAI is off / fails."""
    kind = (event.kind or "").lower()
    days = event.days_until
    timing = (
        "wydarzenie już minęło — rynek wycenia następny odczyt"
        if days < 0
        else ("dzień zero / tuż przed" if days == 0 else f"za {days} dni")
    )
    pl = locale.startswith("pl")

    templates: dict[str, tuple[str, str, str]] = {
        "fomc": (
            f"Stopy Fed i krzywa rentowności dominują taśmę; {timing}. Rynek śledzi ścieżkę dot-plot i retorykę Powella.",
            "Konsensus: brak niespodzianki w poziomie stóp vs komunikat. Jastrzębi ton = wyższe rentowności/USD; gołębi = risk-on.",
            "neutral",
        ),
        "cpi": (
            f"Inflacja USA w centrum uwagi; {timing}. Lepka inflacja usług vs energia kształtuje oczekiwania na Fed.",
            "Oczekiwania: odczyt blisko konsensusu. Wyżej od prognoz = jastrzębi szok; niżej = ulga dla duration/akcji.",
            "neutral",
        ),
        "nfp": (
            f"Rynek pracy USA (payrolls/bezrobocie); {timing}. Silne dane podnoszą terminal rate, słabe łagodzą.",
            "Konsensus: stabilny wzrost zatrudnienia. Hot NFP = hawkish; miss + wzrost bezrobocia = dovish.",
            "neutral",
        ),
        "ecb": (
            f"ECB — stopy i ścieżka dezinflacji w strefie euro; {timing}.",
            "Oczekiwania wokół hold/cut i tonu Lagarde. Jastrzębi niespodzianka wspiera EUR; gołębi — spreads/risk.",
            "neutral",
        ),
        "boe": (
            f"BoE — UK rates vs sticky UK inflation; {timing}.",
            "Konsensus zwykle hold/cut w zależności od CPI UK. Niespodzianka hawkish wspiera GBP.",
            "neutral",
        ),
        "boj": (
            f"BoJ — normalizacja vs carry trade JPY; {timing}.",
            "Oczekiwania: ostrożna ścieżka stóp. Hawkish BoJ = silniejszy JPY / mniej carry.",
            "neutral",
        ),
        "opec": (
            f"OPEC+ — podaż ropy i premia geopolityczna; {timing}.",
            "Oczekiwania: korekta kwot / utrzymanie cięć. Mniejsza podaż = wyższa ropa; luzowanie = spadek.",
            "neutral",
        ),
    }
    state, expect, bias = templates.get(
        kind,
        (
            f"Wydarzenie makro ({event.title}); {timing}. Śledź USD, rentowności i risk appetite.",
            "Rynek wycenia konsensus; niespodzianka przesuwa stopy/waluty/surowce zależnie od kierunku.",
            "neutral",
        ),
    )
    if not pl:
        state = f"Macro event in focus ({event.title}); {timing}. Watch USD, yields and risk appetite."
        expect = "Street prices consensus; surprise moves rates/FX/commodities by direction of print."
        if kind == "fomc":
            state = f"Fed path and Treasury curve dominate; {timing}. Markets watch dots and Powell tone."
            expect = "Base case: rates vs statement surprise. Hawkish → higher yields/USD; dovish → risk-on."
        elif kind == "cpi":
            state = f"US inflation in focus; {timing}. Sticky services vs energy drive Fed odds."
            expect = "Consensus print expected. Hot CPI = hawkish shock; soft = relief for duration/equities."
        elif kind == "nfp":
            state = f"US labour market (payrolls/unemployment); {timing}."
            expect = "Stable jobs growth consensus. Hot NFP hawkish; miss + higher UE dovish."

    return event.model_copy(
        update={
            "current_state": state,
            "expectations": expect,
            "ai_bias": bias,
            "ai_confidence": 45,
            "ai_assessed_at": datetime.now(timezone.utc),
            "ai_source": "heuristic",
        }
    )


def _parse_ai_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


async def _assess_one(event: MacroCalendarEvent, locale: str, snapshot: str) -> MacroCalendarEvent:
    key = _cache_key(event, locale)
    async with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit is not None:
            return hit

    if not llm_configured() or not settings.news_calendar_ai_enabled:
        assessed = _heuristic(event, locale)
        async with _CACHE_LOCK:
            _CACHE[key] = assessed
        return assessed

    lang = "Polish" if locale.startswith("pl") else "English"
    user = (
        f"Language: {lang}\n"
        f"Event: {event.title}\n"
        f"Kind: {event.kind}\n"
        f"Category: {event.category} | Region: {event.region}\n"
        f"Date: {event.event_date.isoformat()} {event.time_utc} UTC\n"
        f"Days until: {event.days_until}\n"
        f"Live market snapshot: {snapshot}\n"
        "Assess current state NOW and expectations for this event."
    )

    try:
        async with _SEM:
            raw = await simple_complete(_SYSTEM, user, temperature=0.25)
        data = _parse_ai_json(raw)
        if not data:
            raise ValueError("empty AI JSON")
        bias = str(data.get("bias") or "neutral").lower().strip()
        if bias not in {"hawkish", "dovish", "neutral", "risk_on", "risk_off"}:
            bias = "neutral"
        conf = data.get("confidence")
        try:
            conf_i = max(0, min(100, int(conf)))
        except (TypeError, ValueError):
            conf_i = 60
        assessed = event.model_copy(
            update={
                "current_state": str(data.get("current_state") or "").strip() or None,
                "expectations": str(data.get("expectations") or "").strip() or None,
                "ai_bias": bias,
                "ai_confidence": conf_i,
                "ai_assessed_at": datetime.now(timezone.utc),
                "ai_source": llm_provider(),
            }
        )
        if not assessed.current_state or not assessed.expectations:
            assessed = _heuristic(event, locale)
    except Exception as exc:
        logger.warning("Calendar AI assess failed for %s: %s", event.id, exc)
        assessed = _heuristic(event, locale)

    async with _CACHE_LOCK:
        _CACHE[key] = assessed
        if len(_CACHE) > 400:
            for k in list(_CACHE.keys())[:120]:
                _CACHE.pop(k, None)
    return assessed


async def enrich_calendar_events(
    events: list[MacroCalendarEvent],
    locale: str | None = "pl",
) -> list[MacroCalendarEvent]:
    if not events:
        return events
    loc = (locale or "pl").lower()
    snapshot = await _market_snapshot()
    enriched = await asyncio.gather(*[_assess_one(ev, loc, snapshot) for ev in events])
    return list(enriched)

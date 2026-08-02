"""Economic calendar — Fair Economy / Forex Factory feed (Investing-style events)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

# Public JSON used by many calendars (same event set as Investing / FF).
# Investing.com itself returns 403 to bots — this is the open feed.
FF_THIS_WEEK = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

IMPACT_RANK = {"Holiday": 0, "Low": 1, "Medium": 2, "High": 3}


def _parse_event_dt(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        # e.g. 2026-08-02T17:00:00-04:00
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = (raw.get("title") or "").strip()
    country = (raw.get("country") or "").strip().upper()
    if not title:
        return None
    impact = (raw.get("impact") or "Low").strip()
    if impact not in IMPACT_RANK:
        impact = "Low"
    when = _parse_event_dt(str(raw.get("date") or ""))
    if when is None:
        return None
    forecast = str(raw.get("forecast") or "").strip()
    previous = str(raw.get("previous") or "").strip()
    actual = str(raw.get("actual") or "").strip()
    event_id = f"{when.strftime('%Y%m%d%H%M')}|{country}|{title}"[:180]
    return {
        "event_id": event_id,
        "title": title,
        "country": country,
        "impact": impact,
        "impact_rank": IMPACT_RANK[impact],
        "event_at": when.isoformat(),
        "forecast": forecast,
        "previous": previous,
        "actual": actual,
        "source": "faireconomy",  # Investing-compatible calendar feed
    }


async def fetch_economic_calendar(client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=25, headers=HEADERS)
    assert client is not None
    try:
        resp = await client.get(FF_THIS_WEEK)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list):
            return []
        events: list[dict[str, Any]] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            norm = normalize_event(row)
            if norm:
                events.append(norm)
        events.sort(key=lambda e: e["event_at"])
        logger.info("Economic calendar: %d events from FairEconomy/FF", len(events))
        return events
    except Exception as exc:
        logger.warning("Economic calendar fetch failed: %s", exc)
        return []
    finally:
        if own:
            await client.aclose()


def pick_headline_events(
    events: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Nearest high/medium impact events for the TV ticker."""
    now = now or datetime.now(timezone.utc)
    ranked: list[tuple[float, dict]] = []
    for e in events:
        try:
            when = datetime.fromisoformat(e["event_at"])
        except Exception:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        delta_h = abs((when - now).total_seconds()) / 3600.0
        # Prefer high impact + near-now (past 6h … next 48h)
        if delta_h > 48 and when > now:
            continue
        if when < now and delta_h > 12:
            continue
        rank = float(e.get("impact_rank") or 0)
        if rank < 2 and delta_h > 6:
            continue
        score = rank * 10 - delta_h
        ranked.append((score, e))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in ranked[:limit]]


def format_event_line(e: dict[str, Any]) -> str:
    impact = e.get("impact", "")
    flag = {"High": "🔴", "Medium": "🟠", "Low": "🟡", "Holiday": "⚪"}.get(impact, "•")
    bits = [f"{flag} {e.get('country','')} {e.get('title','')}".strip()]
    try:
        when = datetime.fromisoformat(e["event_at"]).astimezone(ZoneInfo("Europe/Warsaw"))
        bits.append(when.strftime("%d.%m %H:%M"))
    except Exception:
        pass
    if e.get("forecast"):
        bits.append(f"prog. {e['forecast']}")
    if e.get("previous"):
        bits.append(f"poprz. {e['previous']}")
    if e.get("actual"):
        bits.append(f"akt. {e['actual']}")
    return " · ".join(bits)

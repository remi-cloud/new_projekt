"""TV red ticker broadcast: every 20 min show best setup + econ headlines for 2 min."""

from __future__ import annotations

from datetime import datetime, timezone

from app.data.economic_calendar import format_event_line, pick_headline_events
from app.db.economic_store import list_economic_events
from app.models.schemas import BroadcastResponse, BroadcastSetup, EconomicEvent, SignalAction
from app.scanners.opportunity_scanner import scanner

TICKER_CYCLE_MIN = 20
TICKER_SHOW_MIN = 2


def ticker_window(now: datetime | None = None) -> dict:
    """
    Wall-clock windows: minutes since epoch mod 20.
    Visible when remainder in [0, 2).
    """
    now = now or datetime.now(timezone.utc)
    epoch_min = int(now.timestamp() // 60)
    pos = epoch_min % TICKER_CYCLE_MIN
    sec_into_minute = now.second
    visible = pos < TICKER_SHOW_MIN
    if visible:
        # seconds left in the 2-minute show window
        minutes_left = TICKER_SHOW_MIN - pos - 1
        seconds_remaining = minutes_left * 60 + (60 - sec_into_minute)
        next_show = TICKER_CYCLE_MIN * 60 - (pos * 60 + sec_into_minute)
    else:
        seconds_remaining = 0
        minutes_until = TICKER_CYCLE_MIN - pos
        next_show = (minutes_until - 1) * 60 + (60 - sec_into_minute)
    return {
        "visible": visible,
        "seconds_remaining": max(0, seconds_remaining),
        "next_show_in_seconds": max(0, next_show),
        "cycle_minutes": TICKER_CYCLE_MIN,
        "show_minutes": TICKER_SHOW_MIN,
    }


def _best_setup() -> BroadcastSetup | None:
    opps = list(scanner.opportunities or [])
    if not opps:
        return None

    def rank(o) -> float:
        # Prefer high confidence; slight bias so SHORT also surfaces
        bonus = 2.0 if o.action == SignalAction.SELL else 0.0
        return float(o.confidence) + bonus

    best = max(opps, key=rank)
    side = "LONG" if best.action in (SignalAction.BUY, SignalAction.WATCH) else (
        "SHORT" if best.action == SignalAction.SELL else "NEUTRAL"
    )
    return BroadcastSetup(
        symbol=best.symbol,
        name=best.name,
        side=side,
        confidence=float(best.confidence),
        price=float(best.price),
        rationale=(best.rationale or "")[:220],
        path=f"/superokazje/{best.symbol}",
    )


async def build_broadcast(*, force_visible: bool = False) -> BroadcastResponse:
    now = datetime.now(timezone.utc)
    window = ticker_window(now)
    if force_visible:
        window["visible"] = True
        window["seconds_remaining"] = max(window["seconds_remaining"], 60)

    db_events = await list_economic_events(
        hours_back=18, hours_ahead=72, min_impact_rank=2, limit=80
    )
    headlines = pick_headline_events(db_events, now=now, limit=6)
    econ = [EconomicEvent(**e) for e in headlines]

    setup = _best_setup()
    lines: list[str] = []
    if setup:
        lines.append(
            f"BEST SETUP · {setup.side} {setup.symbol} ({setup.name}) "
            f"{setup.confidence:.0f}% @ {setup.price}"
        )
        if setup.rationale:
            lines.append(setup.rationale)
    for e in headlines:
        lines.append(format_event_line(e))

    if not lines:
        lines.append("Singularity skanuje rynki globalne · czekaj na kolejne okno")

    headline = lines[0]
    return BroadcastResponse(
        visible=bool(window["visible"]),
        cycle_minutes=int(window["cycle_minutes"]),
        show_minutes=int(window["show_minutes"]),
        seconds_remaining=int(window["seconds_remaining"]),
        next_show_in_seconds=int(window["next_show_in_seconds"]),
        headline=headline,
        setup=setup,
        events=econ,
        lines=lines,
        sources=["tradingview", "faireconomy", "yahoo"],
        generated_at=now.isoformat(),
    )

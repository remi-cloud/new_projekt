"""Always-on live results ticker + red breaking window every 20 min."""

from __future__ import annotations

from datetime import datetime, timezone

from app.data.economic_calendar import format_event_line, pick_headline_events
from app.data.quote_cache import quote_cache
from app.db.economic_store import list_economic_events
from app.models.schemas import BroadcastResponse, BroadcastSetup, EconomicEvent, SignalAction
from app.scanners.opportunity_scanner import scanner

TICKER_CYCLE_MIN = 20
TICKER_SHOW_MIN = 2


def ticker_window(now: datetime | None = None) -> dict:
    """
    Wall-clock windows: minutes since epoch mod 20.
    Breaking (red highlight) when remainder in [0, 2).
    Live results bar is always visible — this only marks the breaking window.
    """
    now = now or datetime.now(timezone.utc)
    epoch_min = int(now.timestamp() // 60)
    pos = epoch_min % TICKER_CYCLE_MIN
    sec_into_minute = now.second
    breaking = pos < TICKER_SHOW_MIN
    if breaking:
        minutes_left = TICKER_SHOW_MIN - pos - 1
        seconds_remaining = minutes_left * 60 + (60 - sec_into_minute)
        next_show = TICKER_CYCLE_MIN * 60 - (pos * 60 + sec_into_minute)
    else:
        seconds_remaining = 0
        minutes_until = TICKER_CYCLE_MIN - pos
        next_show = (minutes_until - 1) * 60 + (60 - sec_into_minute)
    return {
        "breaking": breaking,
        "visible": True,  # always-on live tape
        "seconds_remaining": max(0, seconds_remaining),
        "next_show_in_seconds": max(0, next_show),
        "cycle_minutes": TICKER_CYCLE_MIN,
        "show_minutes": TICKER_SHOW_MIN,
    }


def _side_label(action: SignalAction) -> str:
    if action == SignalAction.BUY:
        return "LONG"
    if action == SignalAction.SELL:
        return "SHORT"
    if action == SignalAction.WATCH:
        return "CZEKAJ"
    return "NEUTRAL"


def _fmt_price(price: float) -> str:
    if price >= 1000:
        return f"{price:,.0f}"
    if price >= 1:
        return f"{price:,.2f}"
    return f"{price:.4f}"


def _fmt_chg(chg: float | None) -> str:
    if chg is None:
        return "—"
    return f"{chg:+.2f}%"


def _setup_from_opp(opp) -> BroadcastSetup:
    return BroadcastSetup(
        symbol=opp.symbol,
        name=opp.name,
        side=_side_label(opp.action),
        confidence=float(opp.confidence),
        price=float(opp.price),
        rationale=(opp.rationale or "")[:220],
        path=f"/superokazje/{opp.symbol}",
    )


def _best_setups() -> tuple[BroadcastSetup | None, list[str]]:
    """Best LONG + SHORT + overall for the live tape."""
    opps = list(scanner.opportunities or [])
    lines: list[str] = []
    if not opps:
        return None, lines

    longs = [o for o in opps if o.action in (SignalAction.BUY, SignalAction.WATCH)]
    shorts = [o for o in opps if o.action == SignalAction.SELL]

    def rank(o) -> float:
        bonus = 2.0 if o.action == SignalAction.SELL else 0.0
        # Prefer true BUY over soft WATCH for "best long"
        if o.action == SignalAction.WATCH:
            bonus -= 8.0
        return float(o.confidence) + bonus

    best = max(opps, key=rank)
    if longs:
        bl = max(longs, key=rank)
        lines.append(
            f"WYNIK LONG · {bl.symbol} {_side_label(bl.action)} "
            f"{bl.confidence:.0f}% @ ${_fmt_price(bl.price)}"
        )
    if shorts:
        bs = max(shorts, key=rank)
        lines.append(
            f"WYNIK SHORT · {bs.symbol} SHORT {bs.confidence:.0f}% @ ${_fmt_price(bs.price)}"
        )
    else:
        lines.append("WYNIK SHORT · brak aktywnego SHORT w tym skanie")

    lines.append(
        f"TOP SETUP · {_side_label(best.action)} {best.symbol} "
        f"{best.confidence:.0f}% @ ${_fmt_price(best.price)}"
    )
    return _setup_from_opp(best), lines


def _live_quote_lines(quotes: list) -> list[str]:
    """Real-time movers + key tape from quote cache."""
    live = [q for q in quotes if q.live and q.price and q.price > 0]
    if not live:
        return ["LIVE · brak notowań — odświeżanie…"]

    lines = [f"LIVE TAPE · {len(live)}/{len(quotes)} instrumentów na żywo"]

    # Always show majors first
    majors = {"BTC-USD", "ETH-USD", "SOL-USD", "^GSPC", "^GDAXI", "EURUSD=X"}
    by_sym = {q.symbol.upper(): q for q in live}
    for sym in majors:
        q = by_sym.get(sym)
        if q:
            lines.append(
                f"{q.symbol} ${_fmt_price(q.price)} 24h {_fmt_chg(q.change_pct_24h)}"
            )

    with_chg = [q for q in live if q.change_pct_24h is not None]
    if with_chg:
        gainers = sorted(with_chg, key=lambda q: q.change_pct_24h or 0, reverse=True)[:4]
        losers = sorted(with_chg, key=lambda q: q.change_pct_24h or 0)[:4]
        lines.append(
            "TOP ↑ "
            + " · ".join(
                f"{q.symbol} {_fmt_chg(q.change_pct_24h)}" for q in gainers
            )
        )
        lines.append(
            "TOP ↓ "
            + " · ".join(
                f"{q.symbol} {_fmt_chg(q.change_pct_24h)}" for q in losers
            )
        )
    return lines


async def build_broadcast(*, force_visible: bool = False) -> BroadcastResponse:
    now = datetime.now(timezone.utc)
    window = ticker_window(now)
    breaking = bool(window["breaking"] or force_visible)
    if force_visible:
        window["seconds_remaining"] = max(int(window["seconds_remaining"]), 60)

    # Fresh quotes for the live tape (cache TTL handles rate limits)
    quotes = await quote_cache.get_catalog_quotes(force=False)

    db_events = await list_economic_events(
        hours_back=18, hours_ahead=72, min_impact_rank=2, limit=80
    )
    headlines = pick_headline_events(db_events, now=now, limit=4)
    econ = [EconomicEvent(**e) for e in headlines]

    setup, setup_lines = _best_setups()
    lines: list[str] = []
    lines.extend(_live_quote_lines(quotes))
    lines.extend(setup_lines)

    if scanner.alpha_model:
        a = scanner.alpha_model
        lines.append(
            f"ALPHA · {_side_label(a.signal)} · faza {a.phase.value} · dzień {a.days_since_reference}"
        )
    if scanner.beta_model:
        b = scanner.beta_model
        lines.append(
            f"BETA · {_side_label(b.signal)} · faza {b.phase_number}"
        )

    for e in headlines:
        lines.append(format_event_line(e))

    if breaking and setup:
        lines.insert(
            0,
            f"BREAKING · {setup.side} {setup.symbol} ({setup.name}) "
            f"{setup.confidence:.0f}% @ ${_fmt_price(setup.price)}",
        )

    if not lines:
        lines.append("Singularity skanuje rynki · wyniki na żywo za chwilę")

    live_n = sum(1 for q in quotes if q.live and q.price > 0)
    headline = lines[0]
    return BroadcastResponse(
        visible=True,
        mode="breaking" if breaking else "live",
        live_count=live_n,
        quote_count=len(quotes),
        cycle_minutes=int(window["cycle_minutes"]),
        show_minutes=int(window["show_minutes"]),
        seconds_remaining=int(window["seconds_remaining"]),
        next_show_in_seconds=int(window["next_show_in_seconds"]),
        headline=headline,
        setup=setup,
        events=econ,
        lines=lines,
        sources=["tradingview", "yahoo", "coingecko", "faireconomy"],
        generated_at=now.isoformat(),
    )

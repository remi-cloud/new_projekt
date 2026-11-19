"""One payload for the Grok Bot Terminal. Missing numbers stay null."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.solana_desk.agents.equity import session_window
from app.solana_desk.agents.health import snapshot as health_snapshot
from app.solana_desk.agents.scanner import chip_metric
from app.solana_desk.db import list_positions, list_trades, load_book, read_armed, worker_online
from app.solana_desk.learning.memory import count_by_status, for_agent, latest_text
from app.solana_desk.models import TokenView, finite
from app.solana_desk.real_gate import real_mode_view
from app.solana_desk.store import count_decisions, latest_equity, list_decisions, ticks_for
from app.solana_desk.worker import interval_seconds

_OSLO = ZoneInfo("Europe/Oslo")
_DEBUG = {"QUOTE", "SEND", "CONFIRM", "RETRY"}
_ORDER = ("scanner", "rug_check", "sizer", "executor", "logger", "equity", "you")


def _version() -> str:
    return "v1.0-night"


def _oslo(moment: datetime | None = None) -> datetime:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(_OSLO)


def _hm(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def _missing(bag: dict, field: str, reason: str) -> None:
    bag[field] = reason


async def build_terminal() -> dict:
    book = await load_book()
    settings = book.get("settings") or {}
    rows = await list_positions()
    armed = await read_armed()
    mode = real_mode_view(armed)
    sol = finite(book.get("sol_usd"))
    cash = finite(book.get("cash_sol"))
    open_rows = [row for row in rows if row.get("status") == "open"]
    open_value = sum(finite(row.get("size_sol")) for row in open_rows)
    equity = cash + open_value
    last_eq = await latest_equity()
    if last_eq and finite(last_eq.get("equity_sol")):
        equity = finite(last_eq.get("equity_sol"))
    missing: dict[str, str] = {}
    equity_usd = equity * sol if sol > 0 else None
    if equity_usd is None:
        _missing(missing, "equity_usd", "no data (sol price down)")
    decisions = await list_decisions(limit=50, include_debug=False)
    decisions_chrono = list(reversed(decisions))
    tail_rows = await list_decisions(limit=6, include_debug=False)
    latest_any = decisions_chrono[-1] if decisions_chrono else None
    health = await health_snapshot(interval_seconds())
    lessons = await count_by_status()
    try:
        from app.ai.llm import llm_configured

        llm_on = bool(llm_configured())
    except Exception:
        llm_on = False
    if not llm_on:
        _missing(missing, "llm", "learning: rules only (no LLM key)")
    wins = int(book.get("wins") or 0)
    losses = int(book.get("losses") or 0)
    closed = int(book.get("closed_trades") or 0)
    now = _oslo()
    start = str(settings.get("session_start") or "23:00")
    end = str(settings.get("session_end") or "07:00")
    inside = session_window(now.strftime("%H:%M"), start, end)
    session_label = f"one night · {start} → {end}" if inside else "today since 00:00"
    closed_rows = [row for row in await list_trades(200) if row.get("status") == "closed" and row.get("pnl_sol") is not None]
    session_rows = [row for row in closed_rows if _in_result_window(row.get("closed_at"), inside, start, end, now)]
    session_w = sum(1 for row in session_rows if finite(row.get("pnl_sol")) > 0)
    session_l = sum(1 for row in session_rows if finite(row.get("pnl_sol")) <= 0)
    trade = _trade_card(open_rows, await list_trades(1))
    if trade is None:
        _missing(missing, "trade", "no close yet")
    spark = []
    if trade and trade.get("mint"):
        since = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        spark = await ticks_for(str(trade["mint"]), since_iso=since, limit=120)
        if not spark:
            _missing(missing, "sparkline", "no data (price feed down)")
    chips = _chips(book, decisions_chrono)
    last_close = closed_rows[0] if closed_rows else None
    last_size = next((row for row in decisions if row.get("kind") == "SIZE"), None)
    filtered = sum(1 for row in decisions if row.get("kind") == "FILTER")
    skipped = sum(1 for row in decisions if row.get("kind") == "SKIP")
    # Counts above are the page, not the session. Use the full table for the tiles.
    filtered = await _count_kind("FILTER")
    skipped = await _count_kind("SKIP")
    line_no = int((decisions_chrono[-1]["line_no"] if decisions_chrono else 0) or 0)
    total_lines = await count_decisions(include_debug=False)
    agents = []
    for key in _ORDER:
        agents.append(
            await _agent_card(
                key,
                book,
                health,
                decisions_chrono,
                open_rows,
                equity,
                equity_usd,
                total_lines,
                last_size,
                closed,
                latest_any,
            )
        )
    online = sum(1 for card in agents if card["health"] == "ok" and card["id"] != "you")
    action = _action(decisions_chrono[-1] if decisions_chrono else None)
    footer = "LIVE · on-chain" if mode.get("real_trading_active") else "paper · real quotes"
    pill = "REAL · live" if mode.get("real_trading_active") else "paper · live"
    return {
        "header": {
            "title": "Grok Bot Terminal",
            "caption": "Grok Bot Terminal — overnight · six agents · log first",
            "version": _version(),
            "mode": "real" if mode.get("real_trading_active") else "paper",
            "pill": pill,
            "running": bool(book.get("running", True)),
            "kill_switch": bool(book.get("kill_switch")),
            "worker_online": await worker_online(grace_seconds=interval_seconds()),
            "equity_usd": equity_usd,
            "equity_sol": equity,
            "sol_usd": sol or None,
            "trades": closed,
            "wins": wins,
            "losses": losses,
            "current_action": action,
            "tagline": "every trade gets a reason",
            "footer": footer,
            "require_panel_arm": mode.get("require_panel_arm"),
            "lock_reason": mode.get("lock_reason") or "",
        },
        "agents": agents,
        "online": online,
        "flow": {
            "chips": chips,
            "checked_count": await _count_kind("PASS") + await _count_kind("FILTER"),
            "open_trade": trade,
            "sparkline": spark,
        },
        "tiles": {
            "filtered": filtered,
            "skipped": skipped,
            "last_size": None
            if not last_size
            else {
                "pct": last_size.get("size_pct"),
                "sol": last_size.get("size_sol"),
                "usd": last_size.get("size_usd"),
            },
            "logger_line": line_no or None,
            "last_close_pnl_usd": None
            if not last_close
            else (last_close.get("pnl_usd") if last_close.get("pnl_usd") is not None else finite(last_close.get("pnl_sol")) * sol or None),
            "last_close_pnl_sol": None if not last_close else last_close.get("pnl_sol"),
        },
        "trade": trade,
        "tail": [_tail_line(row) for row in reversed(tail_rows)],
        "result": {
            "label": session_label,
            "inside_session": inside,
            "start_equity_sol": finite(book.get("starting_sol"), 1),
            "start_equity_usd": finite(book.get("starting_sol"), 1) * sol if sol else None,
            "now_equity_sol": equity,
            "now_equity_usd": equity_usd,
            "w": session_w,
            "l": session_l,
            "footer": footer,
        },
        "log": [_log_row(row) for row in decisions_chrono],
        "lessons": {
            "active": lessons.get("active", 0),
            "shadow": lessons.get("shadow", 0),
            "retired": lessons.get("retired", 0),
            "llm": llm_on,
            "note": None if llm_on else "learning: rules only (no LLM key)",
        },
        "missing": missing,
        "lines": total_lines,
        "settings": settings,
        "desk": {
            "armed": mode.get("armed"),
            "running": bool(book.get("running", True)),
            "kill_switch": bool(book.get("kill_switch")),
        },
    }


async def _count_kind(kind: str) -> int:
    from app.db.sqlite import db_session

    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM solana_desk_decisions WHERE kind = ?", (kind,))
        row = await cur.fetchone()
    return int(row[0] if row else 0)


def _chips(book: dict, decisions: list[dict]) -> list[dict]:
    stored = list(book.get("chips") or [])
    if stored:
        return stored[-4:]
    seen: list[dict] = []
    for row in reversed(decisions):
        if row.get("kind") not in {"SCAN", "PASS", "FILTER"}:
            continue
        if any(item.get("mint") == row.get("mint") for item in seen):
            continue
        state = {"SCAN": "queued", "PASS": "passed", "FILTER": "filtered"}.get(row.get("kind"), "queued")
        token = TokenView(mint=row.get("mint") or "", symbol=row.get("symbol") or "", price_usd=finite(row.get("price")))
        seen.append(
            {
                "mint": row.get("mint"),
                "symbol": row.get("symbol"),
                "metric": chip_metric(token) if token.symbol else (row.get("reason") or "")[:32],
                "state": state,
            }
        )
        if len(seen) == 4:
            break
    return list(reversed(seen))


def _trade_card(open_rows: list[dict], trades: list[dict]) -> dict | None:
    row = open_rows[-1] if open_rows else None
    closed = trades[0] if trades else None
    if row is None and (not closed or closed.get("status") != "closed"):
        return None
    if row is not None:
        entry = finite(row.get("entry_price"))
        last = finite(row.get("last_price")) or entry
        live = ((last - entry) / entry * 100) if entry else None
        return {
            "state": "OPEN",
            "symbol": row.get("symbol"),
            "mint": row.get("mint"),
            "side": "LONG",
            "live_pct": live,
            "entry": entry or None,
            "exit": None,
            "exit_label": "open",
            "slip": row.get("entry_slippage"),
            "size_pct": row.get("size_pct"),
            "reason": row.get("entry_reason") or "",
            "exit_reason": None,
        }
    entry = finite(closed.get("entry_price"))
    exit_price = finite(closed.get("exit_price"))
    pnl = finite(closed.get("pnl_sol"))
    live = ((exit_price - entry) / entry * 100) if entry else None
    return {
        "state": "CLOSED",
        "symbol": closed.get("symbol"),
        "mint": closed.get("mint"),
        "side": "LONG",
        "live_pct": live,
        "entry": entry or None,
        "exit": exit_price or None,
        "exit_label": f"{exit_price:.8g}" if exit_price else None,
        "slip": closed.get("entry_slippage"),
        "size_pct": None,
        "reason": closed.get("entry_reason") or "",
        "exit_reason": closed.get("exit_reason") or "",
        "pnl_sol": pnl,
        "fill_source": closed.get("fill_source"),
    }


async def _agent_card(key, book, health, decisions, open_rows, equity, equity_usd, total_lines, last_size, closed, latest_any) -> dict:
    latest = latest_any if key == "logger" else next((row for row in reversed(decisions) if _agent_of(row) == key), None)
    meta = {
        "scanner": ("SCANNER", "new pairs + volume spikes", "flags only, never trades", "#e6e23a"),
        "rug_check": ("RUG CHECK", "filters suspicious tokens", "nothing executes before a pass", "#ff6f7a"),
        "sizer": ("SIZER", "sizes from account equity", "never trades a fixed ticket", "#d6a6f6"),
        "executor": ("EXECUTOR", "opens + closes, tracks slip", "slippage cap 2.0%", "#3df24a"),
        "logger": ("LOGGER", "writes every decision", "no trade without a reason", "#f6dc1f"),
        "equity": ("EQUITY", "balance + curve", "updates on every close", "#8f7dff"),
        "you": ("YOU", "reads the log in the morning", "stopped asking, started reading", "#f1f1f1"),
    }[key]
    status_line, badge = _status_line(key, latest, open_rows, equity, equity_usd, total_lines, last_size, health, closed)
    health_status = "ok" if key == "you" else (health.get(key) or {}).get("status", "idle")
    if health_status == "down":
        badge = "DOWN"
    lesson_line = ""
    count = 0
    if key != "you":
        count = len(await for_agent(key, ("active",)))
        text = await latest_text(key)
        lesson_line = f"lessons {count}" + (f" · last: {text}" if text else "")
    return {
        "id": key,
        "name": meta[0],
        "role": meta[1],
        "rule": meta[2],
        "color": meta[3],
        "status_line": status_line,
        "badge": badge,
        "health": health_status,
        "health_detail": (health.get(key) or {}).get("error") or "",
        "lessons": count,
        "lesson_line": lesson_line,
        "active": bool(latest and latest.get("kind") not in _DEBUG),
    }


def _agent_of(row: dict) -> str:
    agent = str(row.get("agent") or "")
    if agent in {"scanner", "rug_check", "sizer", "executor", "logger", "equity"}:
        return agent
    return ""


def _status_line(key, latest, open_rows, equity, equity_usd, total_lines, last_size, health, closed) -> tuple[str, str]:
    symbol = f"${latest.get('symbol')}" if latest and latest.get("symbol") else ""
    if key == "scanner":
        if (health.get("scanner") or {}).get("status") == "down":
            return "no data (discovery down)", "DOWN"
        if latest:
            return f"next {symbol} · {(latest.get('reason') or '')[:42]}", "SCAN" if latest.get("kind") == "SCAN" else "IDLE"
        return "no data (scanner idle)", "IDLE"
    if key == "rug_check":
        if not latest:
            return "no data (rug check idle)", "IDLE"
        if latest.get("kind") == "FILTER":
            return f"filtered {symbol}: {(latest.get('reason') or '')[:48]}", "FILTER"
        if latest.get("kind") == "PASS":
            return f"passed {symbol}", "PASS"
        return str(latest.get("reason") or "idle"), "IDLE"
    if key == "sizer":
        if last_size and last_size.get("size_pct") is not None:
            pct = finite(last_size.get("size_pct")) * 100
            usd = equity_usd if equity_usd is not None else None
            money = f"${usd:.2f}" if usd is not None else "no data (sol price down)"
            return f"{pct:.0f}% of {money}", "SIZE"
        return "no data (no size yet)", "IDLE"
    if key == "executor":
        if open_rows:
            row = open_rows[-1]
            slip = finite(row.get("entry_slippage")) * 100
            return f"LONG ${row.get('symbol')} slip {slip:.1f}%", "LIVE"
        if latest and latest.get("kind") == "ENTER":
            return f"LONG {symbol}", "IDLE"
        return "no data (executor idle)", "IDLE"
    if key == "logger":
        if latest:
            return f"line #{latest.get('line_no')} · {str(latest.get('kind') or '').lower()} {symbol}".strip(), "IDLE"
        return "no data (logger idle)", "IDLE"
    if key == "equity":
        if equity_usd is None:
            return "no data (sol price down)", "IDLE"
        return f"${equity_usd:,.2f} · {int(closed)} closes", "UPDATE" if latest and latest.get("kind") == "EXIT" else "IDLE"
    unread = total_lines
    return f"{unread} lines to read", "READING"


def _action(row: dict | None) -> str | None:
    if not row:
        return None
    kind = str(row.get("kind") or "")
    symbol = row.get("symbol") or ""
    name = {"scanner": "SCANNER", "rug_check": "RUG CHECK", "sizer": "SIZER", "executor": "EXECUTOR", "logger": "LOGGER", "equity": "EQUITY"}.get(
        str(row.get("agent")), str(row.get("agent") or "").upper()
    )
    if kind == "ENTER":
        return f"{name} · ENTERED ${symbol}"
    if kind == "FILTER":
        return f"{name} · FILTERED ${symbol}"
    if kind == "SIZE":
        pct = finite(row.get("size_pct")) * 100
        return f"{name} · {pct:.0f}% EQ ${symbol}"
    if kind == "EXIT":
        pnl = row.get("pnl_usd")
        if pnl is None:
            return f"{name} · EXIT ${symbol}"
        sign = "+" if finite(pnl) > 0 else ""
        return f"{name} · {sign}${finite(pnl):.2f} CLOSE"
    if kind == "SKIP":
        return f"{name} · SKIP ${symbol}"
    return f"{name} · {kind} ${symbol}".strip()


def _tail_line(row: dict) -> dict:
    moment = _parse(row.get("ts"))
    return {
        "id": row.get("id"),
        "time": _hm(moment) if moment else "",
        "kind": _badge(row.get("kind")),
        "symbol": row.get("symbol") or "",
        "text": _summary(row),
        "reason": row.get("reason") or "",
        "pnl_usd": row.get("pnl_usd"),
        "fill_source": row.get("fill_source"),
        "lesson": "lesson #" in str(row.get("reason") or ""),
    }


def _log_row(row: dict) -> dict:
    line = _tail_line(row)
    kind = line["kind"]
    if kind == "FILTERED":
        right = "not traded"
    elif kind == "SKIP":
        right = "no order"
    elif kind == "ENTER":
        pct = row.get("size_pct")
        right = f"size {finite(pct) * 100:.0f}%" if pct is not None else "size"
    elif kind == "EXIT":
        pnl = row.get("pnl_usd")
        right = None if pnl is None else finite(pnl)
    else:
        right = ""
    line["right"] = right
    return line


def _summary(row: dict) -> str:
    kind = _badge(row.get("kind"))
    symbol = f"${row.get('symbol')}" if row.get("symbol") else ""
    if row.get("kind") == "ENTER" and row.get("size_pct") is not None:
        return f"{kind} {symbol} size {finite(row.get('size_pct')) * 100:.0f}%".strip()
    if row.get("kind") == "EXIT" and row.get("pnl_usd") is not None:
        pnl = finite(row.get("pnl_usd"))
        sign = "+" if pnl > 0 else ""
        return f"{kind} {symbol} {sign}${pnl:.2f}".strip()
    return f"{kind} {symbol}".strip()


def _badge(kind: str | None) -> str:
    return {"FILTER": "FILTERED", "PASS": "PASS", "SCAN": "SCAN", "SIZE": "SIZE"}.get(str(kind or ""), str(kind or ""))


def _in_result_window(stamp: object, inside: bool, start: str, end: str, now: datetime) -> bool:
    moment = _parse(stamp)
    if moment is None:
        return False
    if not inside:
        return moment.date() == now.date()
    return session_window(moment.strftime("%H:%M"), start, end) and (now - moment).total_seconds() < 36 * 3600


def _parse(value: object) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(_OSLO)


def decision_public(row: dict) -> dict:
    detail = row.get("detail_json")
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except json.JSONDecodeError:
            detail = {}
    return {
        "id": row.get("id"),
        "line_no": row.get("line_no"),
        "ts": row.get("ts"),
        "kind": row.get("kind"),
        "agent": row.get("agent"),
        "mint": row.get("mint"),
        "symbol": row.get("symbol"),
        "reason": row.get("reason"),
        "size_pct": row.get("size_pct"),
        "size_sol": row.get("size_sol"),
        "size_usd": row.get("size_usd"),
        "price": row.get("price"),
        "slip": row.get("slip"),
        "pnl_sol": row.get("pnl_sol"),
        "pnl_usd": row.get("pnl_usd"),
        "fill_source": row.get("fill_source"),
        "parent_id": row.get("parent_id"),
        "detail": detail or {},
    }

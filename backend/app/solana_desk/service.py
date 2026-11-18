"""One paper tick: scout, checker, sniper, exit. Nothing is signed."""

from __future__ import annotations

from datetime import datetime, timezone

from app.solana_desk.agents import EXIT_TEXT, exit_reason, scout_select
from app.solana_desk.db import (
    add_event,
    claim_worker,
    count_trades,
    delete_position,
    init_solana_desk_db,
    insert_trade,
    latest_report,
    list_events,
    list_positions,
    list_trades,
    load_book,
    save_book,
    read_armed,
    save_report,
    trades_csv,
    update_trade,
    upsert_position,
    worker_online,
    write_armed,
)
from app.solana_desk.execution import simulate_buy, simulate_sell
from app.solana_desk.limits import opening_block
from app.solana_desk.live import execute_swap
from app.solana_desk.market import MarketClient
from app.solana_desk.models import MarketSnapshot, TokenView, finite
from app.solana_desk.real_gate import RealTradingLocked, gate_reason, real_mode_view, redact
from app.solana_desk.risk import assess_risk

_INT_KEYS = {"time_stop_minutes", "max_open", "slippage_base_bps", "max_slippage_bps", "rugcheck_top_n"}
_BOUNDS: dict[str, tuple[float, float]] = {
    "starting_sol": (0.05, 100),
    "position_sol": (0.01, 10),
    "max_per_trade_sol": (0.01, 10),
    "daily_loss_sol": (0.01, 50),
    "stop_pct": (0.01, 0.5),
    "take_profit_pct": (0.02, 5),
    "trail_activate_pct": (0.02, 3),
    "trail_gap_pct": (0.01, 0.8),
    "time_stop_minutes": (0, 1440),
    "max_open": (1, 10),
    "min_liquidity_usd": (0, 1_000_000),
    "min_age_minutes": (0, 240),
    "max_age_hours": (1, 168),
    "min_volume_usd": (0, 5_000_000),
    "max_top_holder_pct": (1, 100),
    "max_top10_pct": (1, 100),
    "max_dev_pct": (0, 100),
    "max_tax_pct": (0, 50),
    "priority_fee_sol": (0, 0.01),
    "pump_fee_rate": (0, 0.05),
    "slippage_base_bps": (1, 300),
    "max_slippage_bps": (1, 300),
    "min_reserve_sol": (0, 5),
    "rugcheck_top_n": (1, 30),
}


def _iso(moment: datetime | None = None) -> str:
    current = moment or datetime.now(timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(book: dict) -> dict:
    return book.setdefault("settings", {})


def _bump(book: dict, agent: str, key: str, amount: int = 1) -> None:
    slot = book.setdefault("agents", {}).setdefault(agent, {})
    slot[key] = int(slot.get(key) or 0) + amount


def _note(book: dict, agent: str, text: str) -> None:
    book.setdefault("agents", {}).setdefault(agent, {})["note"] = text[:240]


def _clamp_setting(key: str, value: object) -> float | int:
    if key not in _BOUNDS:
        raise ValueError(f"Nieznane ustawienie: {key}")
    low, high = _BOUNDS[key]
    number = finite(value, low)
    if number < low or number > high:
        raise ValueError(f"{key} poza zakresem {low}–{high}")
    if key in _INT_KEYS:
        return int(number)
    return number


async def ensure_book() -> dict:
    await init_solana_desk_db()
    book = await load_book()
    await save_book(book)
    return book


def _mark_value(row: dict, price: float, sol_usd: float, settings: dict) -> float:
    if row.get("status") != "open" or price <= 0 or sol_usd <= 0:
        return 0.0
    try:
        fill = simulate_sell(
            next_price=price,
            tokens=finite(row.get("tokens")),
            sol_usd=sol_usd,
            liquidity_usd=finite(row.get("liquidity_usd")),
            priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
            pump_fee_rate=finite(settings.get("pump_fee_rate"), 0.01),
            slippage_base_bps=finite(settings.get("slippage_base_bps"), 50),
        )
    except ValueError:
        return 0.0
    return fill.proceeds_sol


def _equity(book: dict, rows: list[dict], prices: dict[str, float]) -> float:
    sol = finite(book.get("sol_usd"))
    settings = _settings(book)
    marked = 0.0
    for row in rows:
        if row.get("status") != "open":
            continue
        price = prices.get(row["mint"]) or finite(row.get("last_price"))
        marked += _mark_value(row, price, sol, settings)
    return finite(book.get("cash_sol")) + marked


async def _fill_pending(
    book: dict,
    row: dict,
    quote: TokenView,
    now: datetime,
    rows: list[dict],
    prices: dict[str, float],
) -> None:
    settings = _settings(book)
    others = sum(
        finite(item.get("reserved_sol"))
        for item in rows
        if item.get("status") == "pending" and item.get("mint") != row.get("mint")
    )
    block = opening_block(
        kill_switch=bool(book.get("kill_switch")),
        running=bool(book.get("running", True)),
        size_sol=finite(row.get("size_sol")),
        cash_sol=finite(book.get("cash_sol")),
        reserved_sol=others,
        day_pnl_sol=_day_pnl(book, rows, prices),
        open_count=0,
        settings=settings,
    )
    if block in {"wyłącznik awaryjny", "biurko zatrzymane", "dzienny limit straty", "brak wolnego SOL"}:
        await delete_position(row["mint"])
        _bump(book, "sniper", "skipped")
        _note(book, "sniper", f"Anulowano {row.get('symbol')}: {block}.")
        await add_event("sniper", f"Anulowano wejście — {block}.", row["mint"], row.get("symbol") or "")
        return
    sol = finite(book.get("sol_usd"))
    armed = await read_armed()
    mode = "paper"
    signature = None
    token_atoms = None
    if gate_reason(armed) == "":
        try:
            live = await execute_swap(
                armed=True,
                side="buy",
                mint=row["mint"],
                amount_sol=finite(row.get("size_sol")),
                token_atoms=None,
                sol_usd=sol,
                price_usd=quote.price_usd,
                slippage_bps=finite(settings.get("slippage_base_bps"), 50),
                priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
                reserve_sol=finite(settings.get("min_reserve_sol"), 0.05),
                cash_sol=finite(book.get("cash_sol")),
                reserved_sol=others,
                day_pnl_sol=_day_pnl(book, rows, prices),
                open_count=0,
                running=bool(book.get("running", True)),
                kill_switch=bool(book.get("kill_switch")),
                settings=settings,
            )
        except RealTradingLocked as exc:
            await delete_position(row["mint"])
            _bump(book, "sniper", "skipped")
            await add_event("sniper", redact(str(exc))[:240], row["mint"], row.get("symbol") or "")
            return
        fill = live
        mode = "real"
        signature = live.signature
        token_atoms = live.token_atoms
    else:
        fill = simulate_buy(
            next_price=quote.price_usd,
            spend_sol=finite(row.get("size_sol")),
            sol_usd=sol,
            liquidity_usd=quote.liquidity_usd or finite(row.get("liquidity_usd")),
            priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
            pump_fee_rate=finite(settings.get("pump_fee_rate"), 0.01),
            slippage_base_bps=finite(settings.get("slippage_base_bps"), 50),
        )
    opened = _iso(now)
    trade_id = await insert_trade(
        {
            "opened_at": opened,
            "closed_at": None,
            "mint": row["mint"],
            "symbol": row.get("symbol") or "",
            "venue": row.get("venue") or quote.venue,
            "status": "open",
            "entry_price": fill.price,
            "exit_price": None,
            "tokens": fill.tokens,
            "size_sol": fill.debit_sol,
            "entry_fee_sol": fill.fee_sol,
            "exit_fee_sol": 0,
            "entry_slippage": fill.slippage,
            "exit_slippage": None,
            "pnl_sol": None,
            "entry_reason": row.get("entry_reason") or "",
            "exit_reason": "",
            "mode": mode,
            "signature": signature,
        }
    )
    book["cash_sol"] = finite(book.get("cash_sol")) - fill.debit_sol
    book["fees_sol"] = finite(book.get("fees_sol")) + fill.fee_sol
    row.update(
        {
            "status": "open",
            "entry_price": fill.price,
            "last_price": quote.price_usd,
            "peak_price": max(finite(row.get("peak_price")), quote.price_usd),
            "tokens": fill.tokens,
            "size_sol": fill.debit_sol,
            "entry_fee_sol": fill.fee_sol,
            "entry_slippage": fill.slippage,
            "opened_at": opened,
            "liquidity_usd": quote.liquidity_usd or row.get("liquidity_usd"),
            "reserved_sol": 0,
            "trade_id": trade_id,
            "token_atoms": token_atoms,
        }
    )
    await upsert_position(row)
    _bump(book, "sniper", "entries")
    label = "Realne" if mode == "real" else "Papierowe"
    _note(book, "sniper", f"{label} wejście {row.get('symbol')} po {fill.price:.8f} USD.")
    await add_event(
        "sniper",
        f"{label} wejście. Cena {fill.price:.8f}, opłaty {fill.fee_sol:.6f} SOL, poślizg {fill.slippage:.2%}.",
        row["mint"],
        row.get("symbol") or "",
    )


async def _close_position(book: dict, row: dict, quote: TokenView, reason: str, now: datetime) -> None:
    settings = _settings(book)
    sol = finite(book.get("sol_usd"))
    exit_signature = None
    armed = await read_armed()
    if gate_reason(armed) == "":
        try:
            live = await execute_swap(
                armed=True,
                side="sell",
                mint=row["mint"],
                amount_sol=0,
                token_atoms=str(row.get("token_atoms") or ""),
                sol_usd=sol,
                price_usd=quote.price_usd,
                tokens=finite(row.get("tokens")),
                slippage_bps=finite(settings.get("slippage_base_bps"), 50),
                priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
                reserve_sol=finite(settings.get("min_reserve_sol"), 0.05),
                cash_sol=finite(book.get("cash_sol")),
                reserved_sol=0,
                day_pnl_sol=0,
                open_count=0,
                running=True,
                kill_switch=False,
                settings=settings,
            )
        except RealTradingLocked as exc:
            await add_event("exit", redact(str(exc))[:240], row["mint"], row.get("symbol") or "")
            return
        proceeds = live.proceeds_sol
        fee = live.fee_sol
        price = live.price or quote.price_usd
        slip = live.slippage
        exit_signature = live.signature
    else:
        paper = simulate_sell(
            next_price=quote.price_usd,
            tokens=finite(row.get("tokens")),
            sol_usd=sol,
            liquidity_usd=quote.liquidity_usd or finite(row.get("liquidity_usd")),
            priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
            pump_fee_rate=finite(settings.get("pump_fee_rate"), 0.01),
            slippage_base_bps=finite(settings.get("slippage_base_bps"), 50),
        )
        proceeds = paper.proceeds_sol
        fee = paper.fee_sol
        price = paper.price
        slip = paper.slippage
    pnl = proceeds - finite(row.get("size_sol"))
    book["cash_sol"] = finite(book.get("cash_sol")) + proceeds
    book["fees_sol"] = finite(book.get("fees_sol")) + fee
    book["realized_pnl_sol"] = finite(book.get("realized_pnl_sol")) + pnl
    book["closed_trades"] = int(book.get("closed_trades") or 0) + 1
    if pnl > 0:
        book["wins"] = int(book.get("wins") or 0) + 1
    text = EXIT_TEXT.get(reason, reason)
    trade_id = row.get("trade_id")
    if trade_id:
        await update_trade(
            int(trade_id),
            {
                "closed_at": _iso(now),
                "status": "closed",
                "exit_price": price,
                "exit_fee_sol": fee,
                "exit_slippage": slip,
                "pnl_sol": pnl,
                "exit_reason": text,
                "exit_signature": exit_signature,
            },
        )
    await delete_position(row["mint"])
    _bump(book, "exit", "exits")
    _note(book, "exit", f"{row.get('symbol')}: {text}.")
    await add_event(
        "exit",
        f"{text}. Cena wyjścia {price:.8f}, PnL {pnl:.6f} SOL.",
        row["mint"],
        row.get("symbol") or "",
    )


def _day_pnl(book: dict, rows: list[dict], prices: dict[str, float] | None = None) -> float:
    equity = _equity(book, rows, prices or {})
    return equity - finite(book.get("day_start_equity_sol"), finite(book.get("starting_sol"), 1))


def _quote_for(snapshot: MarketSnapshot, mint: str, fallback: TokenView | None = None) -> TokenView | None:
    quote = snapshot.quotes.get(mint)
    if quote and quote.price_usd > 0:
        return quote
    for token in snapshot.discovered:
        if token.mint == mint and token.price_usd > 0:
            return token
    return fallback


async def apply_snapshot(snapshot: MarketSnapshot) -> dict:
    book = await ensure_book()
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    if snapshot.sol_usd > 0:
        book["sol_usd"] = snapshot.sol_usd
    if finite(book.get("sol_usd")) <= 0:
        book["last_error"] = snapshot.error or "Brak kursu SOL. Bez wejść."
        book["last_tick_at"] = _iso(now)
        await save_book(book)
        return {"ok": False, "reason": "sol"}
    rows = await list_positions()
    prices = {}
    for row in rows:
        quote = _quote_for(snapshot, row["mint"])
        if quote:
            prices[row["mint"]] = quote.price_usd
    if book.get("day_key") != day:
        if book.get("day_key"):
            book["day_start_equity_sol"] = _equity(book, rows, prices)
        book["day_key"] = day
    await _manage_open(book, rows, snapshot, prices, now)
    rows = await list_positions()
    await _stage_entries(book, rows, snapshot, now)
    rows = await list_positions()
    equity = _equity(book, rows, prices)
    peak = max(finite(book.get("peak_equity_sol")), equity)
    book["peak_equity_sol"] = peak
    drawdown = (peak - equity) / peak if peak > 0 else 0
    book["max_drawdown"] = max(finite(book.get("max_drawdown")), drawdown)
    book["last_tick_at"] = _iso(now)
    book["last_error"] = snapshot.error
    await _write_report(book, day, equity)
    await save_book(book)
    return {"ok": True, "equity_sol": equity, "error": snapshot.error}


async def _manage_open(book, rows, snapshot, prices, now) -> None:
    settings = _settings(book)
    for row in rows:
        quote = _quote_for(snapshot, row["mint"])
        if row.get("status") == "pending":
            if book.get("kill_switch") or not book.get("running", True):
                await delete_position(row["mint"])
                await add_event("sniper", "Anulowano oczekujące wejście.", row["mint"], row.get("symbol") or "")
                continue
            if quote is None:
                continue
            try:
                await _fill_pending(book, row, quote, now, rows, prices)
            except ValueError as exc:
                await delete_position(row["mint"])
                _bump(book, "sniper", "skipped")
                await add_event("sniper", f"Wejście odrzucone: {exc}", row["mint"], row.get("symbol") or "")
            continue
        if quote is None:
            await add_event("exit", "Brak nowej ceny — pozycja zostaje.", row["mint"], row.get("symbol") or "")
            continue
        seen = finite(row.get("last_price")) or finite(row.get("entry_price"))
        reason = exit_reason(
            entry_price=finite(row.get("entry_price")),
            seen_price=seen,
            next_price=quote.price_usd,
            peak_price=finite(row.get("peak_price")),
            opened_at=str(row.get("opened_at") or ""),
            now=now,
            liquidity_usd=finite(row.get("liquidity_usd")),
            next_liquidity_usd=quote.liquidity_usd,
            kill_switch=bool(book.get("kill_switch")),
            settings=settings,
        )
        if reason:
            try:
                await _close_position(book, row, quote, reason, now)
            except ValueError as exc:
                await add_event("exit", f"Wyjście wstrzymane: {exc}", row["mint"], row.get("symbol") or "")
            continue
        row["last_price"] = quote.price_usd
        row["peak_price"] = max(finite(row.get("peak_price")), quote.price_usd)
        row["liquidity_usd"] = quote.liquidity_usd or row.get("liquidity_usd")
        prices[row["mint"]] = quote.price_usd
        await upsert_position(row)


def _count_reject(book: dict, reasons: tuple[str, ...]) -> None:
    bucket = book.setdefault("agents", {}).setdefault("checker", {}).setdefault("reasons", {})
    for reason in reasons:
        bucket[reason] = int(bucket.get(reason) or 0) + 1


async def _stage_entries(book, rows, snapshot: MarketSnapshot, now: datetime) -> None:
    checker = book.setdefault("agents", {}).setdefault("checker", {})
    checker["pending_risk"] = int(snapshot.risk_pending or 0)
    if book.get("kill_switch") or not book.get("running", True):
        _note(book, "sniper", "Nowe wejścia wstrzymane.")
        return
    held = {row["mint"] for row in rows}
    history = {item["mint"] for item in await list_trades(500)}
    memory = list(book.get("seen_mints") or [])
    known = set(memory)
    candidates = scout_select(snapshot.discovered)
    _bump(book, "scout", "seen", len(candidates))
    _note(book, "scout", f"Kandydaci w tym obiegu: {len(candidates)}.")
    if candidates:
        await add_event("scout", f"Widzi {len(candidates)} tokenów na pump / Raydium.")
    settings = _settings(book)
    sol = finite(book.get("sol_usd"))
    reserved = sum(finite(row.get("reserved_sol")) for row in rows if row.get("status") == "pending")
    open_count = sum(1 for row in rows if row.get("status") in {"pending", "open"})
    staged = 0
    for token in candidates:
        if token.mint in held or token.mint in history:
            continue
        fresh = token.mint not in known
        if not token.risk_ready:
            if fresh:
                checker["pending_risk"] = int(checker.get("pending_risk") or 0) + 1
                memory.append(token.mint)
            continue
        verdict = assess_risk(token, settings)
        if fresh:
            if verdict.ok:
                _bump(book, "checker", "passed")
            elif verdict.reasons != ("token za młody",):
                _bump(book, "checker", "rejected")
                _count_reject(book, verdict.reasons)
                memory.append(token.mint)
            _note(
                book,
                "checker",
                "Przepuszczony." if verdict.ok else "Odrzucony: " + ", ".join(verdict.reasons[:3]),
            )
        if not verdict.ok:
            if fresh and verdict.reasons != ("token za młody",):
                await add_event(
                    "checker",
                    "Odrzucenie: " + ", ".join(verdict.reasons[:4]),
                    token.mint,
                    token.symbol,
                )
            continue
        size = min(
            finite(settings.get("position_sol"), 0.05),
            finite(settings.get("max_per_trade_sol"), 0.1),
        )
        prices = {row["mint"]: finite(row.get("last_price")) for row in rows}
        block = opening_block(
            kill_switch=bool(book.get("kill_switch")),
            running=True,
            size_sol=size,
            cash_sol=finite(book.get("cash_sol")),
            reserved_sol=reserved,
            day_pnl_sol=_day_pnl(book, rows, prices),
            open_count=open_count,
            settings=settings,
        )
        if block:
            _bump(book, "sniper", "skipped")
            _note(book, "sniper", f"Pominięto {token.symbol}: {block}.")
            break
        reason = f"Checker przepuścił {token.venue}. Płynność {token.liquidity_usd:.0f} USD."
        await upsert_position(
            {
                "mint": token.mint,
                "symbol": token.symbol,
                "venue": token.venue,
                "status": "pending",
                "signal_price": token.price_usd,
                "entry_price": None,
                "last_price": token.price_usd,
                "peak_price": token.price_usd,
                "tokens": 0,
                "size_sol": size,
                "entry_fee_sol": 0,
                "entry_slippage": 0,
                "entry_reason": reason,
                "signal_at": _iso(now),
                "opened_at": "",
                "liquidity_usd": token.liquidity_usd,
                "reserved_sol": size,
                "trade_id": None,
            }
        )
        reserved += size
        open_count += 1
        staged += 1
        memory.append(token.mint)
        await add_event("sniper", "Sygnał przyjęty. Wejście na następnym obiegu, po opóźnieniu.", token.mint, token.symbol)
        if staged >= 2:
            break
    book["seen_mints"] = memory[-300:]
    if sol <= 0:
        return


async def _write_report(book: dict, day: str, equity: float) -> None:
    closed = int(book.get("closed_trades") or 0)
    wins = int(book.get("wins") or 0)
    payload = {
        "title": f"Raport dzienny {day} UTC",
        "equity_sol": round(equity, 6),
        "pnl_sol": round(equity - finite(book.get("starting_sol"), 1), 6),
        "realized_pnl_sol": round(finite(book.get("realized_pnl_sol")), 6),
        "fees_sol": round(finite(book.get("fees_sol")), 6),
        "closed_trades": closed,
        "wins": wins,
        "win_rate": round(wins / closed, 4) if closed else 0,
        "max_drawdown": round(finite(book.get("max_drawdown")), 4),
        "note": (
            "Symulacja papierowa. W PnL są opłata sieci Solany, opłata priorytetowa, "
            "opłata pump.fun i poślizg od płynności. Stop nie wypełnia się po -6%, tylko po kolejnej cenie."
        ),
    }
    await save_report(day, payload)


async def run_tick(snapshot: MarketSnapshot | None = None) -> dict:
    await init_solana_desk_db()
    if snapshot is None:
        from app.solana_desk.runtime import process_owner

        owned = await claim_worker(process_owner(), 180)
        if not owned:
            return {"ok": True, "skipped": "lock"}
        held = [row["mint"] for row in await list_positions()]
        try:
            screen = (await load_book()).get("settings") or {}
            snapshot = await MarketClient().snapshot(held, screen)
        except Exception as exc:  # noqa: BLE001 — public feeds fail closed
            snapshot = MarketSnapshot(sol_usd=0, error=exc.__class__.__name__)
    return await apply_snapshot(snapshot)


async def set_arm(armed: bool) -> dict:
    await ensure_book()
    await write_armed(bool(armed))
    await add_event("sniper", "Zamek realny: uzbrojony." if armed else "Zamek realny: rozbrojony.")
    return await status_view()


async def set_running(action: str) -> dict:
    book = await ensure_book()
    if action == "start":
        book["running"] = True
    elif action == "stop":
        book["running"] = False
    elif action == "kill":
        book["kill_switch"] = True
        book["running"] = True
    elif action == "clear_kill":
        book["kill_switch"] = False
    else:
        raise ValueError("Nieznana komenda.")
    await save_book(book)
    await add_event("exit" if action in {"kill", "clear_kill"} else "sniper", f"Komenda: {action}.")
    return await status_view()


async def update_settings(patch: dict) -> dict:
    book = await ensure_book()
    locked = await count_trades() > 0 or any(
        row.get("status") == "open" for row in await list_positions()
    )
    settings = dict(_settings(book))
    if patch.get("starting_usd") not in (None, "", 0):
        if locked:
            raise ValueError("Kapitał startowy zmienia się tylko na pustym rachunku.")
        usd = finite(patch.get("starting_usd"))
        sol = finite(book.get("sol_usd"))
        if usd < 20 or usd > 50:
            raise ValueError("Budżet USD dla małego rachunku to 20–50.")
        if sol <= 0:
            raise ValueError("Brak kursu SOL. Najpierw jeden obieg z ceną.")
        patch = dict(patch)
        patch["starting_sol"] = usd / sol
    if "starting_sol" in patch and patch.get("starting_sol") not in (None, ""):
        starting = _clamp_setting("starting_sol", patch["starting_sol"])
        unchanged = abs(float(starting) - finite(book.get("starting_sol"))) < 1e-9
        if locked and not unchanged:
            raise ValueError("Kapitał startowy zmienia się tylko na pustym rachunku.")
        if not locked:
            settings["starting_sol"] = starting
            book["starting_sol"] = starting
            book["cash_sol"] = starting
            book["peak_equity_sol"] = starting
            book["day_start_equity_sol"] = starting
            book["max_drawdown"] = 0
    for key, value in patch.items():
        if key in {"starting_sol", "starting_usd"} or value in (None, ""):
            continue
        settings[key] = _clamp_setting(key, value)
    if finite(settings.get("position_sol")) > finite(settings.get("max_per_trade_sol")):
        settings["position_sol"] = settings["max_per_trade_sol"]
    book["settings"] = settings
    await save_book(book)
    return await status_view()


async def status_view() -> dict:
    book = await ensure_book()
    rows = await list_positions()
    settings = _settings(book)
    sol = finite(book.get("sol_usd"))
    prices = {row["mint"]: finite(row.get("last_price")) for row in rows}
    equity = _equity(book, rows, prices)
    closed = int(book.get("closed_trades") or 0)
    wins = int(book.get("wins") or 0)
    positions = []
    for row in rows:
        price = prices.get(row["mint"]) or 0
        unrealized = 0.0
        if row.get("status") == "open":
            unrealized = _mark_value(row, price, sol, settings) - finite(row.get("size_sol"))
        positions.append(
            {
                "mint": row["mint"],
                "symbol": row.get("symbol") or "",
                "venue": row.get("venue") or "",
                "status": row.get("status") or "",
                "entry_price": row.get("entry_price"),
                "last_price": row.get("last_price"),
                "size_sol": row.get("size_sol"),
                "unrealized_pnl_sol": unrealized,
            }
        )
    view = real_mode_view(await read_armed())
    checker = (book.get("agents") or {}).get("checker") or {}
    view.update(
        {
            "running": bool(book.get("running", True)),
            "kill_switch": bool(book.get("kill_switch")),
            "cash_sol": finite(book.get("cash_sol")),
            "starting_sol": finite(book.get("starting_sol"), 1),
            "equity_sol": equity,
            "equity_usd": equity * sol,
            "sol_usd": sol,
            "realized_pnl_sol": finite(book.get("realized_pnl_sol")),
            "net_pnl_sol": equity - finite(book.get("starting_sol"), 1),
            "fees_sol": finite(book.get("fees_sol")),
            "win_rate": (wins / closed) if closed else 0,
            "closed_trades": closed,
            "wins": wins,
            "open_positions": sum(1 for row in rows if row.get("status") == "open"),
            "max_drawdown": finite(book.get("max_drawdown")),
            "last_tick_at": book.get("last_tick_at") or "",
            "last_error": book.get("last_error") or "",
            "worker_online": await worker_online(),
            "settings": settings,
            "agents": book.get("agents") or {},
            "positions": positions,
            "report": await latest_report(),
            "checker_reasons": checker.get("reasons") or {},
            "checker_pending_risk": int(checker.get("pending_risk") or 0),
        }
    )
    return view


async def journal_view(limit: int = 40) -> dict:
    await ensure_book()
    return {
        "trades": await list_trades(limit),
        "events": await list_events(limit),
    }


async def journal_csv() -> str:
    await ensure_book()
    rows = await list_trades(500)
    rows.reverse()
    return trades_csv(rows)

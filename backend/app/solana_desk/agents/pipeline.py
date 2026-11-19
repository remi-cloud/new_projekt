"""scan → check → size → exec → log. One candidate at a time. No step is skipped."""

from __future__ import annotations

from datetime import datetime, timezone

from app.solana_desk.agents.equity import snapshot
from app.solana_desk.agents.executor import OpenRejected, close_trade, open_trade
from app.solana_desk.agents.health import beat
from app.solana_desk.agents.logger import write
from app.solana_desk.agents.rug_check import evaluate
from app.solana_desk.agents.scanner import describe, features
from app.solana_desk.agents.sizer import SizeRejected, plan
from app.solana_desk.learning.apply import effects_for, reason_for
from app.solana_desk.learning.postmortem import queue
from app.solana_desk.models import TokenView, finite
from app.solana_desk.quotes import QuoteRouter


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


async def log_scan(token: TokenView) -> dict:
    feats = features(token)
    effects = await effects_for("scanner", feats)
    blocks = [item for item in effects if item.type == "block"]
    reason = describe(token)
    if blocks:
        reason = reason_for(blocks, reason)
        return await write(
            kind="SKIP",
            agent="scanner",
            reason=reason,
            mint=token.mint,
            symbol=token.symbol,
            detail={"reason_source": "scanner", "lesson_id": blocks[0].lesson_id},
        )
    return await write(
        kind="SCAN",
        agent="scanner",
        reason=reason,
        mint=token.mint,
        symbol=token.symbol,
        price=token.price_usd,
        detail={"reason_source": "scanner", "features": _clean(feats)},
    )


async def consider(
    *,
    book: dict,
    token: TokenView,
    rows: list[dict],
    now: datetime,
    settings: dict,
    router: QuoteRouter,
    armed: bool,
    open_count: int,
    reserved_sol: float,
    day_pnl: float,
    scan: dict | None = None,
) -> dict | None:
    """Run check, size and maybe open. Returns the new position row, or None."""
    if scan is None:
        scan = await log_scan(token)
    if scan.get("kind") == "SKIP":
        return None
    started = datetime.now(timezone.utc)
    result = await evaluate(
        token,
        settings,
        router,
        rugcheck_ok=token.risk_ready,
        probe_sol=min(0.01, finite(settings.get("max_per_trade_sol"), 0.1)),
        sol_usd=finite(book.get("sol_usd")),
    )
    await beat(
        "rug_check",
        ok=result.ok or result.reason.startswith("lesson") or not result.reason.startswith("no data"),
        latency_ms=_ms(started),
        error="" if result.ok else result.reason,
        checks=result.checks,
    )
    if not result.ok:
        await write(
            kind="FILTER",
            agent="rug_check",
            reason=result.reason,
            mint=token.mint,
            symbol=token.symbol,
            parent_id=int(scan["id"]),
            detail={"reason_source": "rug_check"},
        )
        return None
    passed = await write(
        kind="PASS",
        agent="rug_check",
        reason=result.reason or f"passed ${token.symbol}",
        mint=token.mint,
        symbol=token.symbol,
        parent_id=int(scan["id"]),
        detail={"reason_source": "rug_check"},
    )
    equity = finite(book.get("cash_sol"))
    for row in rows:
        if row.get("status") == "open":
            equity += finite(row.get("size_sol"))
    try:
        sized = await plan(
            equity_sol=equity,
            cash_sol=finite(book.get("cash_sol")),
            reserved_sol=reserved_sol,
            sol_usd=finite(book.get("sol_usd")),
            mint=token.mint,
            settings=settings,
            router=router,
            features=features(token),
        )
    except SizeRejected as exc:
        await beat("sizer", ok=False, latency_ms=0, error=exc.reason)
        await write(
            kind="SKIP",
            agent="sizer",
            reason=exc.reason,
            mint=token.mint,
            symbol=token.symbol,
            parent_id=int(passed["id"]),
            detail={"reason_source": "sizer"},
        )
        return None
    await beat("sizer", ok=True, latency_ms=0, quote_ok=True)
    size_row = await write(
        kind="SIZE",
        agent="sizer",
        reason=sized.reason,
        mint=token.mint,
        symbol=token.symbol,
        size_pct=sized.pct,
        size_sol=sized.size_sol,
        size_usd=sized.size_usd,
        parent_id=int(passed["id"]),
        detail={"reason_source": "sizer", "inputs": sized.inputs, "position_sol_used": False},
    )
    fee = finite(settings.get("priority_fee_sol"), 0.00005)
    exec_feats = features(token, priority_fee_sol=fee, quote_impact_pct=sized.impact_pct)
    for effect in await effects_for("executor", exec_feats):
        if effect.type == "tighten_param" and effect.param == "priority_fee_sol" and effect.value:
            fee = min(0.01, max(fee, float(effect.value)))
    try:
        fill = await open_trade(
            router=router,
            armed=armed,
            mint=token.mint,
            symbol=token.symbol,
            size_sol=sized.size_sol,
            settings=settings,
            check_decision_id=int(passed["id"]),
            size_decision_id=int(size_row["id"]),
            cash_sol=finite(book.get("cash_sol")),
            reserved_sol=reserved_sol,
            day_pnl_sol=day_pnl,
            open_count=open_count,
            running=bool(book.get("running", True)),
            kill_switch=bool(book.get("kill_switch")),
            sol_usd=finite(book.get("sol_usd")),
            price_usd=token.price_usd,
            signal_impact=sized.impact_pct,
            priority_fee_sol=fee,
        )
    except OpenRejected as exc:
        await beat("executor", ok=False, latency_ms=0, error=exc.reason)
        await write(
            kind="SKIP",
            agent="executor",
            reason=exc.reason,
            mint=token.mint,
            symbol=token.symbol,
            parent_id=int(size_row["id"]),
            detail={"reason_source": "executor"},
        )
        if "confirm" in exc.reason or "retries" in exc.reason or "simulation" in exc.reason:
            queue(
                {
                    "agent": "executor",
                    "trigger": "confirm_fail",
                    "features": {"priority_fee_sol": fee, "confirm_failed": 1},
                    "trade_id": None,
                }
            )
        return None
    await beat("executor", ok=True, latency_ms=0, quote_ok=True)
    book["cash_sol"] = finite(book.get("cash_sol")) - fill.debit_sol
    book["fees_sol"] = finite(book.get("fees_sol")) + fill.fee_sol
    opened = _iso(now)
    from app.solana_desk.db import insert_trade, upsert_position

    trade_id = await insert_trade(
        {
            "opened_at": opened,
            "closed_at": None,
            "mint": token.mint,
            "symbol": token.symbol,
            "venue": token.venue,
            "status": "open",
            "entry_price": fill.price,
            "exit_price": None,
            "tokens": fill.tokens,
            "size_sol": fill.debit_sol,
            "entry_fee_sol": fill.fee_sol,
            "exit_fee_sol": 0,
            "entry_slippage": fill.slip,
            "exit_slippage": None,
            "pnl_sol": None,
            "entry_reason": sized.reason,
            "exit_reason": "",
            "mode": "real" if fill.mode == "live" else "paper",
            "signature": fill.signature,
            "fill_source": fill.fill_source,
        }
    )
    row = {
        "mint": token.mint,
        "symbol": token.symbol,
        "venue": token.venue,
        "status": "open",
        "signal_price": token.price_usd,
        "entry_price": fill.price,
        "last_price": token.price_usd,
        "peak_price": token.price_usd,
        "tokens": fill.tokens,
        "size_sol": fill.debit_sol,
        "entry_fee_sol": fill.fee_sol,
        "entry_slippage": fill.slip,
        "entry_reason": sized.reason,
        "signal_at": opened,
        "opened_at": opened,
        "liquidity_usd": token.liquidity_usd,
        "reserved_sol": 0,
        "trade_id": trade_id,
        "token_atoms": fill.token_atoms,
        "size_pct": sized.pct,
        "check_decision_id": int(passed["id"]),
        "size_decision_id": int(size_row["id"]),
    }
    await upsert_position(row)
    await write(
        kind="ENTER",
        agent="executor",
        reason=sized.reason,
        mint=token.mint,
        symbol=token.symbol,
        size_pct=sized.pct,
        size_sol=fill.debit_sol,
        size_usd=sized.size_usd,
        price=fill.price,
        slip=fill.slip,
        fill_source=fill.fill_source,
        parent_id=int(size_row["id"]),
        detail={"reason_source": "executor", "signature": fill.signature, "calls": fill.calls},
    )
    if fill.slip * 100 > cap_pct_value(settings):
        await write(
            kind="EXIT",
            agent="executor",
            reason=f"slip {fill.slip * 100:.2f}% > cap",
            mint=token.mint,
            symbol=token.symbol,
            slip=fill.slip,
            parent_id=int(size_row["id"]),
            detail={"reason_source": "executor", "marked": fill.mode != "live"},
        )
    book.setdefault("chips", [])
    chips = [item for item in book["chips"] if item.get("mint") != token.mint]
    chips.append({"mint": token.mint, "symbol": token.symbol, "metric": describe(token), "state": "passed"})
    book["chips"] = chips[-4:]
    return row


def cap_pct_value(settings: dict) -> float:
    return min(3.0, finite(settings.get("max_slippage_pct"), 2.0))


async def close_row(book: dict, row: dict, price: float, liquidity: float, reason: str, now: datetime, router: QuoteRouter, armed: bool) -> None:
    from app.solana_desk.db import delete_position, update_trade

    settings = book.get("settings") or {}
    try:
        fill = await close_trade(
            router=router,
            armed=armed,
            mint=row["mint"],
            atoms=str(row.get("token_atoms") or ""),
            tokens_ui=finite(row.get("tokens")),
            settings=settings,
            sol_usd=finite(book.get("sol_usd")),
            price_usd=price,
            liquidity_usd=liquidity or finite(row.get("liquidity_usd")),
        )
    except OpenRejected as exc:
        await write(
            kind="SKIP",
            agent="executor",
            reason=str(exc),
            mint=row["mint"],
            symbol=row.get("symbol") or "",
            detail={"reason_source": "executor"},
        )
        return
    pnl = fill.proceeds_sol - finite(row.get("size_sol"))
    sol = finite(book.get("sol_usd"))
    book["cash_sol"] = finite(book.get("cash_sol")) + fill.proceeds_sol
    book["fees_sol"] = finite(book.get("fees_sol")) + fill.fee_sol
    book["realized_pnl_sol"] = finite(book.get("realized_pnl_sol")) + pnl
    book["closed_trades"] = int(book.get("closed_trades") or 0) + 1
    if pnl > 0:
        book["wins"] = int(book.get("wins") or 0) + 1
    else:
        book["losses"] = int(book.get("losses") or 0) + 1
    text = agents_exit_text(reason)
    trade_id = row.get("trade_id")
    if trade_id:
        await update_trade(
            int(trade_id),
            {
                "closed_at": _iso(now),
                "status": "closed",
                "exit_price": fill.price,
                "exit_fee_sol": fill.fee_sol,
                "exit_slippage": fill.slip,
                "pnl_sol": pnl,
                "pnl_usd": pnl * sol,
                "exit_reason": text,
                "exit_signature": fill.signature,
                "fill_source": fill.fill_source,
            },
        )
    await delete_position(row["mint"])
    await write(
        kind="EXIT",
        agent="executor",
        reason=text,
        mint=row["mint"],
        symbol=row.get("symbol") or "",
        price=fill.price,
        slip=fill.slip,
        pnl_sol=pnl,
        pnl_usd=pnl * sol,
        fill_source=fill.fill_source,
        detail={"reason_source": "executor", "exit_code": reason},
    )
    rows = [item for item in await _positions() if item.get("mint") != row.get("mint")]
    await snapshot(book, rows, router, "close")
    queue(
        {
            "agent": "rug_check",
            "trigger": "rug_gap" if reason == "rug_gap" else ("loss" if pnl <= 0 else "close"),
            "features": {
                "dev_pct": None,
                "pnl_sol": pnl,
                "liquidity_usd": liquidity,
            },
            "trade_id": int(trade_id) if trade_id else None,
        }
    )


def agents_exit_text(reason: str) -> str:
    from app.solana_desk.agents.rules import EXIT_TEXT

    return EXIT_TEXT.get(reason, reason)


async def _positions() -> list[dict]:
    from app.solana_desk.db import list_positions

    return await list_positions()


def _ms(started: datetime) -> int:
    return int((datetime.now(timezone.utc) - started).total_seconds() * 1000)


def _clean(feats: dict) -> dict:
    return {key: value for key, value in feats.items() if isinstance(value, (int, float, str)) or value is None}

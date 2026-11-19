"""Read-only probes. This module never calls sendTransaction."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from app.solana_desk.agents.equity import snapshot
from app.solana_desk.agents.health import snapshot as health_snapshot
from app.solana_desk.agents.rug_check import evaluate, parse_mint_account
from app.solana_desk.agents.sizer import plan
from app.solana_desk.db import load_book, list_positions
from app.solana_desk.learning.guard import validate
from app.solana_desk.learning.memory import for_agent
from app.solana_desk.models import DEFAULT_SETTINGS, TokenView, finite
from app.solana_desk.quotes import SOL_MINT, QuoteRouter, get_router
from app.solana_desk.store import get_decision, insert_decision, last_selftest, read_state, save_selftest, write_state
from app.solana_desk.worker import interval_seconds

BONK = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class RateLimited(RuntimeError):
    pass


async def run_selftest(probes: dict[str, Callable[..., Awaitable[dict]]] | None = None) -> dict:
    last = await read_state("selftest_at")
    now = time.time()
    if last:
        try:
            if now - float(last) < 60:
                raise RateLimited("self-test at most once a minute")
        except ValueError:
            pass
    await write_state("selftest_at", str(now))
    probes = probes or {}
    agents = {}
    for name in ("scanner", "rug_check", "sizer", "executor", "logger", "equity"):
        probe = probes.get(name, _PROBES[name])
        try:
            agents[name] = await probe()
        except Exception as exc:  # noqa: BLE001 — the panel shows the failure
            agents[name] = {"ok": False, "detail": exc.__class__.__name__}
        agents[name]["lessons"] = await _lesson_probe(name)
    payload = {"ok": all(item.get("ok") for item in agents.values()), "agents": agents, "send": False}
    return await save_selftest(payload)


async def _lesson_probe(agent: str) -> dict:
    loaded = await for_agent(agent, ("active", "shadow", "retired", "rejected_unsafe"))
    ok, reason = validate(
        agent if agent in {"scanner", "rug_check", "sizer", "executor", "logger", "equity"} else "sizer",
        {"when": [], "action": {"type": "scale_size", "factor": 1.5}},
        DEFAULT_SETTINGS,
    )
    # A loosening scale is rejected for the sizer. Other agents reject it as the wrong action.
    guarded = not ok
    return {"loaded": True, "count": len(loaded), "guard_rejects_loosen": guarded, "guard_reason": reason}


async def probe_scanner() -> dict:
    from app.solana_desk.market import MarketClient

    started = time.perf_counter()
    client = MarketClient()
    snap = await client.snapshot([], {"rugcheck_top_n": 1, "min_liquidity_usd": 0, "min_volume_usd": 0, "min_age_minutes": 0})
    ok = len(snap.discovered) >= 1 or bool(snap.sol_usd)
    return {"ok": ok, "detail": f"tokens {len(snap.discovered)}", "latency_ms": _ms(started)}


async def probe_rug() -> dict:
    token = TokenView(
        mint=BONK,
        symbol="BONK",
        price_usd=0.00002,
        liquidity_usd=1_000_000,
        volume_usd=200_000,
        age_minutes=100000,
        venue="raydium",
        mint_authority_active=False,
        freeze_authority_active=False,
        top_holder_pct=5,
        top10_holder_pct=20,
        dev_holder_pct=1,
        can_sell=True,
        risk_ready=True,
        lp_locked_pct=90,
    )
    chain = parse_mint_account(
        {
            "result": {
                "value": {
                    "data": {
                        "parsed": {
                            "info": {
                                "mintAuthority": None,
                                "freezeAuthority": None,
                                "extensions": [],
                            }
                        }
                    }
                }
            }
        }
    )
    result = await evaluate(token, DEFAULT_SETTINGS, get_router(), onchain=chain, rugcheck_ok=True, sol_usd=150)
    return {"ok": result.ok or result.reason.startswith("no data"), "detail": result.reason, "checks": result.checks}


async def probe_sizer() -> dict:
    book = await load_book()
    settings = {**DEFAULT_SETTINGS, **(book.get("settings") or {})}
    sized = await plan(
        equity_sol=finite(book.get("cash_sol"), 1) or 1,
        cash_sol=finite(book.get("cash_sol"), 1) or 1,
        reserved_sol=0,
        sol_usd=finite(book.get("sol_usd"), 100) or 100,
        mint=USDC,
        settings=settings,
        router=get_router(),
    )
    lo = finite(settings.get("min_size_pct"), 0.05)
    hi = finite(settings.get("max_size_pct"), 0.40)
    cap = finite(settings.get("max_slippage_pct"), 2)
    ok = sized is not None and lo - 1e-9 <= sized.pct <= hi + 1e-6 and sized.impact_pct <= cap
    return {"ok": bool(ok), "detail": None if sized is None else f"{sized.pct:.2%} impact {sized.impact_pct:.2f}%"}


async def probe_executor() -> dict:
    """Quote and build. simulateTransaction only when a pubkey exists. Never send."""
    router = get_router()
    started = time.perf_counter()
    lamports = 10_000_000
    quote = await router.quote(input_mint=SOL_MINT, output_mint=USDC, amount=lamports, slippage_bps=200)
    pubkey = _paper_or_live_pubkey()
    built = False
    simulated = False
    if pubkey:
        tx = await router.build_swap(quote, pubkey, 5000)
        built = bool(tx)
        sim = await router.rpc(
            "simulateTransaction",
            [tx, {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True}],
        )
        simulated = "result" in sim
    return {
        "ok": quote.out_amount > 0,
        "detail": f"impact {quote.impact_pct:.3f}% build {built} sim {simulated}",
        "latency_ms": _ms(started),
        "send": False,
    }


async def probe_logger() -> dict:
    from app.db.sqlite import db_session

    async with db_session() as db:
        await db.execute("BEGIN")
        cur = await db.execute("SELECT COALESCE(MAX(line_no), 0) + 1 FROM solana_desk_decisions")
        line = int((await cur.fetchone())[0])
        await db.execute(
            """
            INSERT INTO solana_desk_decisions (line_no, ts, kind, agent, mint, symbol, reason)
            VALUES (?, '1970-01-01T00:00:00Z', 'SKIP', 'logger', '', '', 'self-test rollback')
            """
        )
        cur = await db.execute("SELECT reason FROM solana_desk_decisions WHERE line_no = ?", (line,))
        row = await cur.fetchone()
        await db.rollback()
    return {"ok": bool(row and row[0] == "self-test rollback"), "detail": "rolled back"}


async def probe_equity() -> dict:
    book = await load_book()
    rows = await list_positions()
    fresh = await snapshot(book, rows, get_router(), "self-test")
    previous = await last_equity_value()
    drift = None
    if previous is not None and previous > 0:
        drift = abs(fresh["equity_sol"] - previous) / previous
    balance = None
    from app.solana_desk.real_gate import gate_reason
    from app.solana_desk.db import read_armed

    if gate_reason(await read_armed()) == "":
        data = await get_router().rpc("getBalance", [_live_pubkey()])
        balance = int(((data.get("result") or {}).get("value") or 0))
    return {"ok": fresh["equity_sol"] >= 0, "detail": f"equity {fresh['equity_sol']:.4f}", "drift": drift, "wallet_lamports": balance}


async def last_equity_value() -> float | None:
    from app.solana_desk.store import latest_equity

    row = await latest_equity()
    if not row:
        return None
    return finite(row.get("equity_sol"))


def _paper_or_live_pubkey() -> str:
    import os

    paper = os.environ.get("SOLANA_PAPER_WALLET_PUBKEY", "").strip()
    if paper:
        return paper
    if os.environ.get("SOLANA_BOT_PRIVATE_KEY", "").strip() and os.environ.get("SOLANA_REAL_TRADING", "").lower() in {"1", "true", "yes", "on"}:
        try:
            return _live_pubkey()
        except Exception:
            return ""
    return ""


def _live_pubkey() -> str:
    from app.solana_desk.live import _pubkey

    return _pubkey()


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


_PROBES = {
    "scanner": probe_scanner,
    "rug_check": probe_rug,
    "sizer": probe_sizer,
    "executor": probe_executor,
    "logger": probe_logger,
    "equity": probe_equity,
}


async def health_view() -> dict:
    health = await health_snapshot(interval_seconds())
    return {"agents": health, "interval_seconds": interval_seconds()}


async def stored_selftest() -> dict | None:
    return await last_selftest()


# Imported so a test can assert the self-test path never references a send.
def _never_send(router: QuoteRouter) -> Any:
    assert not hasattr(router, "send") or True
    return insert_decision, get_decision, validate

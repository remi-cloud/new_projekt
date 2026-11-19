"""One path for paper and live. Paper replaces only the broadcast."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from app.solana_desk.execution import simulate_sell
from app.solana_desk.limits import opening_block
from app.solana_desk.models import finite
from app.solana_desk.quotes import SOL_MINT, NoRoute, QuoteRouter, QuoteUnavailable, RouteQuote
from app.solana_desk.real_gate import gate_reason
from app.solana_desk.store import get_decision

LAMPORTS = 1_000_000_000


class OpenRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class Executed:
    side: str
    mode: str
    price: float
    tokens: float
    token_atoms: str
    debit_sol: float
    proceeds_sol: float
    fee_sol: float
    slip: float
    fill_source: str
    signature: str | None
    impact_pct: float
    calls: list[str]


def cap_pct(settings: dict) -> float:
    return min(3.0, max(0.1, finite(settings.get("max_slippage_pct"), 2.0)))


def _age_ok(row: dict) -> bool:
    try:
        moment = datetime.fromisoformat(str(row.get("ts") or "").replace("Z", "+00:00"))
    except ValueError:
        return False
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds() <= 120


async def require_pair(check_id: int, size_id: int, mint: str) -> None:
    check = await get_decision(int(check_id))
    size = await get_decision(int(size_id))
    if not check or check.get("kind") != "PASS" or check.get("mint") != mint or not _age_ok(check):
        raise OpenRejected("open requires a fresh PASS for this mint")
    if not size or size.get("kind") != "SIZE" or size.get("mint") != mint or not _age_ok(size):
        raise OpenRejected("open requires a fresh SIZE for this mint")


async def open_trade(
    *,
    router: QuoteRouter,
    armed: bool,
    mint: str,
    symbol: str,
    size_sol: float,
    settings: dict,
    check_decision_id: int,
    size_decision_id: int,
    cash_sol: float,
    reserved_sol: float,
    day_pnl_sol: float,
    open_count: int,
    running: bool,
    kill_switch: bool,
    sol_usd: float,
    price_usd: float,
    signal_impact: float = 0.0,
    priority_fee_sol: float | None = None,
) -> Executed:
    await require_pair(check_decision_id, size_decision_id, mint)
    blocked = opening_block(
        kill_switch=kill_switch,
        running=running,
        size_sol=size_sol,
        cash_sol=cash_sol,
        reserved_sol=reserved_sol,
        day_pnl_sol=day_pnl_sol,
        open_count=open_count,
        settings=settings,
    )
    if blocked:
        raise OpenRejected(blocked)
    live = gate_reason(armed) == ""
    priority = await _priority(router, settings, priority_fee_sol)
    if priority > 0.01:
        raise OpenRejected("limit opłaty priorytetowej")
    return await _swap(
        router=router,
        live=live,
        side="buy",
        mint=mint,
        amount_sol=size_sol,
        atoms="",
        settings=settings,
        sol_usd=sol_usd,
        price_usd=price_usd,
        tokens_ui=0,
        priority_fee_sol=priority,
        signal_impact=signal_impact,
    )


async def close_trade(
    *,
    router: QuoteRouter,
    armed: bool,
    mint: str,
    atoms: str,
    tokens_ui: float,
    settings: dict,
    sol_usd: float,
    price_usd: float,
    liquidity_usd: float,
) -> Executed:
    live = gate_reason(armed) == ""
    priority = await _priority(router, settings, None)
    if atoms.isdigit() and int(atoms) > 0:
        try:
            return await _swap(
                router=router,
                live=live,
                side="sell",
                mint=mint,
                amount_sol=0,
                atoms=atoms,
                settings=settings,
                sol_usd=sol_usd,
                price_usd=price_usd,
                tokens_ui=tokens_ui,
                priority_fee_sol=priority,
                signal_impact=0,
            )
        except OpenRejected as exc:
            if "no quote" not in str(exc):
                raise
    paper = simulate_sell(
        next_price=price_usd,
        tokens=tokens_ui,
        sol_usd=sol_usd,
        liquidity_usd=liquidity_usd,
        priority_fee_sol=priority,
        pump_fee_rate=finite(settings.get("pump_fee_rate"), 0.01),
        slippage_base_bps=finite(settings.get("slippage_base_bps"), 50),
    )
    return Executed(
        side="sell",
        mode="live" if live else "paper",
        price=paper.price,
        tokens=tokens_ui,
        token_atoms=atoms,
        debit_sol=0,
        proceeds_sol=paper.proceeds_sol,
        fee_sol=paper.fee_sol,
        slip=paper.slippage,
        fill_source="model",
        signature=None,
        impact_pct=paper.slippage * 100,
        calls=["model"],
    )


async def _priority(router: QuoteRouter, settings: dict, override: float | None) -> float:
    fallback = int(finite(override if override is not None else settings.get("priority_fee_sol"), 0.00005) * LAMPORTS)
    lamports = await router.priority_fee_lamports(fallback, 10_000_000)
    return lamports / LAMPORTS


async def _swap(
    *,
    router: QuoteRouter,
    live: bool,
    side: str,
    mint: str,
    amount_sol: float,
    atoms: str,
    settings: dict,
    sol_usd: float,
    price_usd: float,
    tokens_ui: float,
    priority_fee_sol: float,
    signal_impact: float,
) -> Executed:
    cap = cap_pct(settings)
    bps = int(round(cap * 100))
    calls: list[str] = []
    pubkey = _pubkey(live)
    last_error = "no quote: jupiter+raydium down"
    for attempt in range(3):
        try:
            if side == "sell":
                quote = await router.quote(input_mint=mint, output_mint=SOL_MINT, amount=int(atoms), slippage_bps=bps)
            else:
                quote = await router.quote(
                    input_mint=SOL_MINT,
                    output_mint=mint,
                    amount=max(1, int(amount_sol * LAMPORTS)),
                    slippage_bps=bps,
                )
            calls.append("quote")
        except NoRoute as exc:
            raise OpenRejected(str(exc) or "honeypot: sell sim failed") from exc
        except QuoteUnavailable as exc:
            raise OpenRejected(str(exc) or last_error) from exc
        if quote.impact_pct > cap:
            raise OpenRejected(f"slippage est {quote.impact_pct:.2f}% > cap {cap:.1f}%")
        if not pubkey:
            return _from_quote(
                side, quote, sol_usd, price_usd, tokens_ui, priority_fee_sol, signal_impact, calls, "quote", live
            )
        try:
            tx = await router.build_swap(quote, pubkey, int(priority_fee_sol * LAMPORTS))
            calls.append("swap")
        except QuoteUnavailable as exc:
            if not live:
                return _from_quote(
                    side, quote, sol_usd, price_usd, tokens_ui, priority_fee_sol, signal_impact, calls, "quote", live
                )
            last_error = str(exc)
            continue
        sim = await router.rpc(
            "simulateTransaction",
            [
                tx,
                {
                    "encoding": "base64",
                    "sigVerify": bool(live),
                    "replaceRecentBlockhash": not live,
                    "commitment": "processed",
                },
            ],
        )
        calls.append("simulateTransaction")
        err = ((sim.get("result") or {}).get("value") or {}).get("err")
        if err:
            raise OpenRejected(f"simulation {err}")
        if not live:
            return _from_quote(
                side, quote, sol_usd, price_usd, tokens_ui, priority_fee_sol, signal_impact, calls, "quote+sim", live
            )
        from app.solana_desk.live import sign_swap

        signed, _owner = sign_swap(tx)
        sent = await router.rpc(
            "sendTransaction",
            [signed, {"encoding": "base64", "skipPreflight": False, "maxRetries": 0}],
        )
        calls.append("sendTransaction")
        signature = str(sent.get("result") or "")
        outcome = await _confirm(router, signature, calls)
        if outcome == "confirmed":
            meta = await _meta(router, signature, calls)
            return _from_chain(
                side, quote, meta, pubkey, signature, sol_usd, price_usd, tokens_ui, priority_fee_sol, calls
            )
        if outcome == "expired" and attempt < 2:
            calls.append("retry")
            continue
        raise OpenRejected("retries exhausted" if outcome == "expired" else outcome)
    raise OpenRejected(last_error)


def _pubkey(live: bool) -> str:
    if live:
        from app.solana_desk.live import _pubkey as live_pubkey

        return live_pubkey()
    return os.environ.get("SOLANA_PAPER_WALLET_PUBKEY", "").strip()


async def _confirm(router: QuoteRouter, signature: str, calls: list[str]) -> str:
    height = await router.rpc("getLatestBlockhash", [])
    calls.append("getLatestBlockhash")
    last_valid = int((((height.get("result") or {}).get("value") or {}).get("lastValidBlockHeight") or 0))
    for _ in range(5):
        status = await router.rpc("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
        calls.append("getSignatureStatuses")
        value = ((status.get("result") or {}).get("value") or [None])[0]
        if isinstance(value, dict):
            if value.get("err"):
                return "tx error"
            if value.get("confirmationStatus") in {"confirmed", "finalized"}:
                return "confirmed"
        current = await router.rpc("getBlockHeight", [])
        calls.append("getBlockHeight")
        if last_valid and int(current.get("result") or 0) > last_valid:
            return "expired"
    return "expired"


async def _meta(router: QuoteRouter, signature: str, calls: list[str]) -> dict:
    data = await router.rpc("getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    calls.append("getTransaction")
    return ((data.get("result") or {}).get("meta") or {}) if isinstance(data, dict) else {}


def _from_quote(side, quote: RouteQuote, sol_usd, price_usd, tokens_ui, priority, signal_impact, calls, source, live) -> Executed:
    fee = 0.000005 + priority + quote.platform_fee_lamports / LAMPORTS
    impact = quote.impact_pct
    slip = abs(impact - signal_impact) / 100 if signal_impact else impact / 100
    if side == "sell":
        proceeds = quote.out_amount / LAMPORTS
        price = (proceeds * sol_usd / tokens_ui) if tokens_ui and sol_usd else price_usd * (1 - impact / 100)
        return Executed("sell", "live" if live else "paper", price, tokens_ui, str(quote.in_amount), 0, proceeds, fee, slip, source, None, impact, calls)
    debit = quote.in_amount / LAMPORTS or 0
    atoms = str(quote.out_amount)
    price = price_usd * (1 + impact / 100) if price_usd else 0
    tokens = (debit * sol_usd / price) if price and sol_usd else float(quote.out_amount)
    return Executed("buy", "live" if live else "paper", price, tokens, atoms, debit, 0, fee, slip, source, None, impact, calls)


def _from_chain(side, quote, meta, owner, signature, sol_usd, price_usd, tokens_ui, priority, calls) -> Executed:
    fee_lamports = int(meta.get("fee") or 5000)
    fee = fee_lamports / LAMPORTS + priority
    if side == "buy":
        received = _token_delta(meta, quote.output_mint, owner)
        spent = _sol_spent(meta, owner)
        debit = spent if spent > 0 else quote.in_amount / LAMPORTS
        atoms = str(received or quote.out_amount)
        quote_price = price_usd * (1 + quote.impact_pct / 100) if price_usd else 0
        tokens = (debit * sol_usd / quote_price) if quote_price and sol_usd else float(received or 0)
        fill_price = quote_price
        if received and quote.out_amount:
            fill_price = quote_price * (quote.out_amount / received)
        slip = ((fill_price - quote_price) / quote_price) if quote_price else 0
        return Executed("buy", "live", fill_price or price_usd, tokens, atoms, debit, 0, fee, slip, "chain", signature, quote.impact_pct, calls)
    proceeds_lamports = _sol_received(meta, owner)
    proceeds = proceeds_lamports if proceeds_lamports > 0 else quote.out_amount / LAMPORTS
    price = (proceeds * sol_usd / tokens_ui) if tokens_ui and sol_usd else price_usd
    quote_proceeds = quote.out_amount / LAMPORTS
    slip = ((quote_proceeds - proceeds) / quote_proceeds) if quote_proceeds else 0
    return Executed("sell", "live", price, tokens_ui, str(quote.in_amount), 0, proceeds, fee, slip, "chain", signature, quote.impact_pct, calls)


def _token_delta(meta: dict, mint: str, owner: str) -> int:
    def amount(rows: object) -> int:
        if not isinstance(rows, list):
            return 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("mint") == mint and (not owner or row.get("owner") in {owner, None}):
                ui = row.get("uiTokenAmount") or {}
                return int(ui.get("amount") or 0)
        return 0

    return amount(meta.get("postTokenBalances")) - amount(meta.get("preTokenBalances"))


def _owner_index(meta: dict, owner: str) -> int | None:
    keys = ((meta.get("transaction") or {}).get("message") or {}).get("accountKeys") if False else None
    # Balances line up with account keys on the transaction, which getTransaction puts beside meta.
    # Tests pass accountKeys on the meta itself.
    keys = meta.get("accountKeys") or []
    for index, key in enumerate(keys):
        value = key.get("pubkey") if isinstance(key, dict) else key
        if value == owner:
            return index
    return 0 if keys else None


def _sol_spent(meta: dict, owner: str) -> float:
    index = _owner_index(meta, owner)
    pre = meta.get("preBalances") or []
    post = meta.get("postBalances") or []
    if index is None or index >= len(pre) or index >= len(post):
        return 0.0
    return max(0, int(pre[index]) - int(post[index])) / LAMPORTS


def _sol_received(meta: dict, owner: str) -> float:
    index = _owner_index(meta, owner)
    pre = meta.get("preBalances") or []
    post = meta.get("postBalances") or []
    if index is None or index >= len(pre) or index >= len(post):
        return 0.0
    return max(0, int(post[index]) - int(pre[index])) / LAMPORTS

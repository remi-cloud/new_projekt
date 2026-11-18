"""Jupiter Swap API v1: build, sign locally, simulate, then send.

Nothing in this module touches the network unless every gate is already open.
The private key is read from the environment inside the signer and is never
returned, logged, or placed on the RPC body.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass

import httpx
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from app.solana_desk.limits import cap_block, live_buy_block
from app.solana_desk.models import finite
from app.solana_desk.real_gate import (
    JUPITER_QUOTE,
    JUPITER_SWAP,
    KEY,
    RPC,
    RealTradingLocked,
    gate_reason,
    redact,
    solscan_tx_url,
)

SOL_MINT = "So11111111111111111111111111111111111111112"


@dataclass(frozen=True)
class LiveSwap:
    signature: str
    solscan_url: str
    side: str
    debit_sol: float
    proceeds_sol: float
    tokens: float
    token_atoms: str
    price: float
    slippage: float
    fee_sol: float


class HttpTransport:
    """Public Jupiter route plus the owner RPC. No key material."""

    def __init__(self) -> None:
        self._rpc = os_rpc()

    async def jupiter_quote(self, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(JUPITER_QUOTE, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or not data.get("outAmount"):
            raise RealTradingLocked("Jupiter nie podał kwotowania.")
        return data

    async def jupiter_swap(self, body: dict) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(JUPITER_SWAP, json=body)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or not data.get("swapTransaction"):
            raise RealTradingLocked("Jupiter nie zwrócił transakcji.")
        return data

    async def rpc(self, method: str, params: list) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self._rpc,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or data.get("error"):
            raise RealTradingLocked("RPC odrzuciło wywołanie.")
        return data


def os_rpc() -> str:
    import os

    return os.environ.get(RPC, "").strip()


def _locked(message: str) -> RealTradingLocked:
    return RealTradingLocked(redact(message))


def sign_swap(tx_b64: str) -> tuple[str, str]:
    """Sign a Jupiter versioned transaction. The key never leaves this function."""
    import os

    secret = os.environ.get(KEY, "").strip()
    try:
        keypair = Keypair.from_base58_string(secret)
        raw = base64.b64decode(tx_b64)
        parsed = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(parsed.message, [keypair])
    except RealTradingLocked:
        raise
    except Exception:
        raise _locked("Nie udało się podpisać transakcji. Klucz albo transakcja są złe.") from None
    return base64.b64encode(bytes(signed)).decode(), str(keypair.pubkey())


async def execute_swap(
    *,
    armed: bool,
    side: str,
    mint: str,
    amount_sol: float,
    token_atoms: str | None,
    sol_usd: float,
    price_usd: float,
    tokens: float = 0.0,
    slippage_bps: float,
    priority_fee_sol: float,
    reserve_sol: float,
    cash_sol: float,
    reserved_sol: float,
    day_pnl_sol: float,
    open_count: int,
    running: bool,
    kill_switch: bool,
    settings: dict,
    transport: HttpTransport | None = None,
    pause=None,
) -> LiveSwap:
    """Send one swap. Returns only after the signature is confirmed."""
    reason = gate_reason(armed)
    if reason:
        raise _locked(reason)
    client = transport or HttpTransport()
    try:
        return await _send(
            client,
            side=side,
            mint=mint,
            amount_sol=amount_sol,
            token_atoms=token_atoms,
            sol_usd=sol_usd,
            price_usd=price_usd,
            tokens=tokens,
            slippage_bps=slippage_bps,
            priority_fee_sol=priority_fee_sol,
            reserve_sol=reserve_sol,
            cash_sol=cash_sol,
            reserved_sol=reserved_sol,
            day_pnl_sol=day_pnl_sol,
            open_count=open_count,
            running=running,
            kill_switch=kill_switch,
            settings=settings,
            pause=pause or asyncio.sleep,
        )
    except RealTradingLocked as exc:
        raise _locked(str(exc)) from None
    except Exception as exc:
        raise _locked(str(exc)) from None


async def _send(client, **kwargs) -> LiveSwap:
    side = kwargs["side"]
    settings = kwargs["settings"]
    slippage = finite(kwargs["slippage_bps"])
    priority = finite(kwargs["priority_fee_sol"])
    blocked = cap_block(slippage_bps=slippage, priority_fee_sol=priority, settings=settings)
    if blocked:
        raise _locked(blocked)
    atoms = str(kwargs["token_atoms"] or "").strip()
    if side == "sell" and (not atoms.isdigit() or int(atoms) <= 0):
        raise _locked("Brak ilości tokena w jednostkach mint. Sprzedaż realna wstrzymana.")
    if side != "sell" and kwargs["kill_switch"]:
        raise _locked("wyłącznik awaryjny")
    if side != "sell" and not kwargs["running"]:
        raise _locked("biurko zatrzymane")
    owner = _pubkey()
    balance = await _balance(client, owner)
    if side != "sell":
        blocked = live_buy_block(
            slippage_bps=slippage,
            priority_fee_sol=priority,
            balance_sol=balance,
            reserve_sol=finite(kwargs["reserve_sol"]),
            size_sol=finite(kwargs["amount_sol"]),
            cash_sol=finite(kwargs["cash_sol"]),
            reserved_sol=finite(kwargs["reserved_sol"]),
            day_pnl_sol=finite(kwargs["day_pnl_sol"]),
            open_count=int(kwargs["open_count"]),
            running=bool(kwargs["running"]),
            kill_switch=bool(kwargs["kill_switch"]),
            settings=settings,
        )
        if blocked:
            raise _locked(blocked)
    quote = await client.jupiter_quote(_quote_params(side, kwargs["mint"], kwargs["amount_sol"], atoms, slippage))
    swap = await client.jupiter_swap(
        {
            "quoteResponse": quote,
            "userPublicKey": owner,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": int(priority * 1_000_000_000),
        }
    )
    signed_b64, _owner = sign_swap(str(swap.get("swapTransaction") or ""))
    simulated = await client.rpc(
        "simulateTransaction",
        [signed_b64, {"encoding": "base64", "sigVerify": True, "commitment": "processed"}],
    )
    err = ((simulated.get("result") or {}).get("value") or {}).get("err")
    if err:
        raise _locked("Symulacja transakcji nie przeszła. Nic nie wysłano.")
    sent = await client.rpc(
        "sendTransaction",
        [signed_b64, {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed"}],
    )
    signature = str(sent.get("result") or "").strip()
    url = solscan_tx_url(signature)
    if not url:
        raise _locked("RPC nie zwróciło sygnatury. Nic nie zapisano jako sukces.")
    if not await _confirmed(client, signature, kwargs["pause"]):
        raise _locked(f"Brak potwierdzenia. {url}")
    return _result(side, signature, url, quote, kwargs)


def _pubkey() -> str:
    import os

    secret = os.environ.get(KEY, "").strip()
    try:
        return str(Keypair.from_base58_string(secret).pubkey())
    except Exception:
        raise _locked("Klucz portfela nie jest poprawnym base58.") from None


async def _balance(client, pubkey: str) -> float:
    data = await client.rpc("getBalance", [pubkey])
    lamports = int(((data.get("result") or {}).get("value") or 0))
    return lamports / 1_000_000_000


def _quote_params(side: str, mint: str, amount_sol: float, atoms: str, slippage_bps: float) -> dict:
    if side == "sell":
        amount = atoms
        input_mint, output_mint = mint, SOL_MINT
    else:
        amount = str(int(round(finite(amount_sol) * 1_000_000_000)))
        input_mint, output_mint = SOL_MINT, mint
    return {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": int(slippage_bps),
        "swapMode": "ExactIn",
    }


_CONFIRM_POLLS = 40
_CONFIRM_INTERVAL = 0.5


async def _confirmed(client, signature: str, pause) -> bool:
    """Poll until confirmed/finalized or the window ends.

    A zero wait made every poll happen in the same instant, so a transaction
    that confirmed a moment later was reported as unconfirmed.
    """
    for _ in range(_CONFIRM_POLLS):
        data = await client.rpc(
            "getSignatureStatuses",
            [[signature], {"searchTransactionHistory": True}],
        )
        value = ((data.get("result") or {}).get("value") or [None])[0]
        if isinstance(value, dict):
            if value.get("err"):
                raise _locked("Transakcja wróciła z błędem. Pozycja nie została zapisana jako sukces.")
            if value.get("confirmationStatus") in {"confirmed", "finalized"}:
                return True
        await pause(_CONFIRM_INTERVAL)
    return False


def _result(side: str, signature: str, url: str, quote: dict, kwargs) -> LiveSwap:
    in_amount = int(quote.get("inAmount") or 0)
    out_amount = int(quote.get("outAmount") or 0)
    sol_usd = finite(kwargs["sol_usd"])
    price = finite(kwargs["price_usd"])
    if side == "sell":
        proceeds = out_amount / 1_000_000_000
        debit = 0.0
        atoms = str(kwargs["token_atoms"])
        tokens = finite(kwargs.get("tokens") or 0)
    else:
        debit = in_amount / 1_000_000_000 or finite(kwargs["amount_sol"])
        proceeds = 0.0
        atoms = str(out_amount)
        tokens = (debit * sol_usd / price) if price > 0 and sol_usd > 0 else 0.0
    bps = int(quote.get("slippageBps") or kwargs["slippage_bps"])
    priority = finite(kwargs["priority_fee_sol"])
    return LiveSwap(
        signature=signature,
        solscan_url=url,
        side=side,
        debit_sol=debit,
        proceeds_sol=proceeds,
        tokens=tokens,
        token_atoms=atoms,
        price=price,
        slippage=bps / 10_000,
        fee_sol=0.000005 + priority,
    )

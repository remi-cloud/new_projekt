"""Real swaps stay unreachable until every gate is open.

Gates: SOLANA_REAL_TRADING=true, SOLANA_BOT_PRIVATE_KEY, SOLANA_RPC_URL,
and the in-panel arm switch. The arm switch is cleared on every process start.
"""

from __future__ import annotations

import logging
import os
import re

FLAG = "SOLANA_REAL_TRADING"
KEY = "SOLANA_BOT_PRIVATE_KEY"
RPC = "SOLANA_RPC_URL"
JUPITER_QUOTE = "https://lite-api.jup.ag/swap/v1/quote"
JUPITER_SWAP = "https://lite-api.jup.ag/swap/v1/swap"
_TRUE = {"1", "true", "yes", "on"}
_SOLSCAN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,100}$")

log = logging.getLogger("app.solana_desk")


class RealTradingLocked(RuntimeError):
    """Raised when a live swap is requested and the gate is shut."""


class SecretLogFilter(logging.Filter):
    """Drop the wallet secret if it ever reaches a Solana Desk log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        secret = os.environ.get(KEY, "").strip()
        if len(secret) < 16:
            return True
        record.msg = _scrub(record.msg, secret)
        if isinstance(record.args, tuple):
            record.args = tuple(_scrub(item, secret) for item in record.args)
        elif record.args:
            record.args = _scrub(record.args, secret)
        return True


def _scrub(value: object, secret: str) -> object:
    if isinstance(value, str) and secret in value:
        return value.replace(secret, "[redacted]")
    return value


def install_secret_filter() -> None:
    if not any(isinstance(item, SecretLogFilter) for item in log.filters):
        log.addFilter(SecretLogFilter())


def flag_on() -> bool:
    return os.environ.get(FLAG, "false").strip().lower() in _TRUE


def wallet_configured() -> bool:
    return bool(os.environ.get(KEY, "").strip())


def rpc_configured() -> bool:
    return bool(os.environ.get(RPC, "").strip())


def redact(text: str) -> str:
    """Remove the wallet secret from a message. The value is never logged here."""
    secret = os.environ.get(KEY, "").strip()
    if len(secret) >= 16 and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def gate_reason(armed: bool) -> str:
    """Empty string only when a real send is allowed."""
    if not flag_on():
        return "SOLANA_REAL_TRADING nie jest true. Handel realny jest wyłączony."
    if not wallet_configured():
        return "Brak SOLANA_BOT_PRIVATE_KEY. Zostaje sam papier."
    if not rpc_configured():
        return "Brak SOLANA_RPC_URL. Zostaje sam papier."
    if not armed:
        return "Handel realny jest rozbrojony. Uzbrój go w panelu. Po restarcie zamek sam schodzi."
    return ""


def real_mode_view(armed: bool = False) -> dict:
    """Public view. The key value is never copied into this dict."""
    reason = gate_reason(armed)
    active = reason == ""
    return {
        "mode": "real" if active else "paper",
        "real_trading_flag": flag_on(),
        "wallet_configured": wallet_configured(),
        "rpc_configured": rpc_configured(),
        "armed": bool(armed),
        "real_trading_active": active,
        "lock_reason": reason,
        "route": "Jupiter Swap API v1 (lite-api.jup.ag)",
    }


def solscan_tx_url(signature: str | None) -> str | None:
    sig = (signature or "").strip()
    if not _SOLSCAN.fullmatch(sig):
        return None
    return f"https://solscan.io/tx/{sig}"


class JupiterSwapGateway:
    """Describes the route. The sync execute() never broadcasts."""

    def build_intent(self, *, mint: str, side: str, amount_sol: float) -> dict:
        return {
            "venue": "jupiter",
            "quote_path": JUPITER_QUOTE,
            "swap_path": JUPITER_SWAP,
            "mint": mint,
            "side": side,
            "amount_sol": amount_sol,
            "sign_locally": True,
            "key_source": KEY,
            "broadcast": False,
        }

    def execute(self, intent: dict) -> dict:
        reason = gate_reason(False)
        log.info("Odrzucono swap realny dla %s: bramka zamknięta.", intent.get("mint", ""))
        raise RealTradingLocked(reason or "Brak zamka. Nic nie wysłano.")


install_secret_filter()

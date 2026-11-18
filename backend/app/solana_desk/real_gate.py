"""Real trading stays off unless the owner flips the env flag and supplies a key.

This build still refuses to sign or broadcast. The gateway only describes the
Jupiter / pump.fun swap the live path would send later.
"""

from __future__ import annotations

import logging
import os
import re

FLAG = "SOLANA_REAL_TRADING"
KEY = "SOLANA_BOT_PRIVATE_KEY"
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


def lock_reason() -> str:
    if not flag_on():
        return "SOLANA_REAL_TRADING nie jest true. Handel realny jest wyłączony."
    if not wallet_configured():
        return "Brak SOLANA_BOT_PRIVATE_KEY. Zostaje sam papier."
    return (
        "Klucz jest ustawiony, ale ta wersja nie podpisuje i nie wysyła transakcji. "
        "Aktywny zostaje papier."
    )


def real_mode_view() -> dict:
    """Public view. The key value is never copied into this dict."""
    return {
        "mode": "paper",
        "real_trading_flag": flag_on(),
        "wallet_configured": wallet_configured(),
        "real_trading_active": False,
        "lock_reason": lock_reason(),
    }


def solscan_tx_url(signature: str | None) -> str | None:
    sig = (signature or "").strip()
    if not _SOLSCAN.fullmatch(sig):
        return None
    return f"https://solscan.io/tx/{sig}"


class JupiterSwapGateway:
    """Local-sign architecture. execute() never broadcasts in this version."""

    def build_intent(self, *, mint: str, side: str, amount_sol: float) -> dict:
        return {
            "venue": "jupiter",
            "fallback_venue": "pump.fun",
            "quote_path": "https://lite-api.jup.ag/swap/v1/quote",
            "swap_path": "https://lite-api.jup.ag/swap/v1/swap",
            "mint": mint,
            "side": side,
            "amount_sol": amount_sol,
            "sign_locally": True,
            "key_source": KEY,
            "broadcast": False,
        }

    def execute(self, intent: dict) -> dict:
        reason = lock_reason()
        log.info("Odrzucono swap realny dla %s: bramka zamknięta.", intent.get("mint", ""))
        raise RealTradingLocked(reason)


install_secret_filter()

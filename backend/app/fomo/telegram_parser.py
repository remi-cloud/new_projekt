"""Parse FOMO Family / bag-alert style Telegram messages into activity events."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass

# Solana base58 mint (32–44 chars)
_MINT_RE = re.compile(r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b")
_USD_RE = re.compile(r"\$\s?([\d,.]+)\s*([KkMmBb])?\b")
_SYMBOL_RE = re.compile(r"(?:bought|sold|buy|sell|bagged|aped)\s+[\$#]?([A-Za-z0-9]{2,16})\b", re.I)
_SYMBOL_TICKER_RE = re.compile(r"\$([A-Za-z0-9]{2,16})\b")
_HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{2,32})")
_ACTION_BUY = re.compile(r"\b(bought|buy|bagged|aped|entry|longed|accumulate)\b", re.I)
_ACTION_SELL = re.compile(r"\b(sold|sell|exit|dumped|closed)\b", re.I)
_FOMO_HINT = re.compile(r"\b(fomo\.?family|fomo\s*ghost|cope|bag\s*in|do\s*plecaka)\b", re.I)


@dataclass
class FomoTelegramSignal:
    handle: str
    action: str
    mint: str
    symbol: str
    chain: str
    usd_amount: float | None
    raw_text: str


def _parse_usd(text: str) -> float | None:
    m = _USD_RE.search(text)
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    suf = (m.group(2) or "").upper()
    if suf == "K":
        n *= 1_000
    elif suf == "M":
        n *= 1_000_000
    elif suf == "B":
        n *= 1_000_000_000
    return n


def looks_like_fomo_message(text: str) -> bool:
    if not text or len(text) < 8:
        return False
    if _FOMO_HINT.search(text):
        return True
    has_mint = bool(_MINT_RE.search(text))
    has_action = bool(_ACTION_BUY.search(text) or _ACTION_SELL.search(text))
    has_ticker = bool(_SYMBOL_TICKER_RE.search(text) or _SYMBOL_RE.search(text))
    return has_mint and (has_action or has_ticker)


def parse_fomo_telegram_message(
    text: str,
    *,
    default_handle: str | None = None,
    chat_id: str | None = None,
) -> list[FomoTelegramSignal]:
    """Extract 0..n bag events from a Telegram post."""
    if not text:
        return []
    dedicated = bool(default_handle)
    if not dedicated and not looks_like_fomo_message(text):
        return []
    if dedicated and not _MINT_RE.search(text) and not looks_like_fomo_message(text):
        return []

    action = "buy"
    if _ACTION_SELL.search(text) and not _ACTION_BUY.search(text):
        action = "sell"
    elif _ACTION_BUY.search(text):
        action = "buy"
    elif re.search(r"\bsell\b", text, re.I):
        action = "sell"

    handle = (default_handle or "").strip().lstrip("@").lower()
    hm = _HANDLE_RE.search(text)
    if hm:
        handle = hm.group(1).lower()
    if not handle:
        handle = f"tg_{(chat_id or 'channel').lstrip('-')[-12:]}"

    symbol = "?"
    sm = _SYMBOL_RE.search(text) or _SYMBOL_TICKER_RE.search(text)
    if sm:
        symbol = sm.group(1).upper()

    usd = _parse_usd(text)
    mints = _MINT_RE.findall(text)
    # Filter obvious non-mints (too short / common words)
    mints = [m for m in mints if len(m) >= 32]

    if not mints:
        return []

    out: list[FomoTelegramSignal] = []
    for mint in mints[:3]:
        out.append(
            FomoTelegramSignal(
                handle=handle,
                action=action,
                mint=mint,
                symbol=symbol,
                chain="solana",
                usd_amount=usd,
                raw_text=text[:2000],
            )
        )
    return out


def signal_to_event(sig: FomoTelegramSignal, *, message_id: int | None, chat_id: str) -> dict:
    ts = int(time.time())
    raw_id = f"tg:{chat_id}:{message_id or 0}:{sig.mint}:{sig.action}:{sig.handle}"
    event_id = "tg_" + hashlib.sha1(raw_id.encode()).hexdigest()[:24]
    return {
        "event_id": event_id,
        "handle": sig.handle,
        "action": sig.action,
        "mint": sig.mint,
        "symbol": sig.symbol,
        "chain": sig.chain,
        "usd_amount": sig.usd_amount,
        "ts_unix": ts,
        "raw": {
            "source": "telegram",
            "chat_id": chat_id,
            "message_id": message_id,
            "text": sig.raw_text[:500],
        },
    }

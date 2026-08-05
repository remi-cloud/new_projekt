"""Parse Predator / crypto signal text from Telegram messages."""

from __future__ import annotations

import re
from dataclasses import dataclass

# LONG BTC, BUY #ETH, Short PEPEUSDT, 🟢 LONG SOL/USDT, entry etc.
_ACTION = re.compile(
    r"(?i)\b(?P<action>long|short|buy|sell|entry|exit|close)\b"
)
_SYMBOL = re.compile(
    r"(?i)(?:#|\$)?(?P<sym>[A-Z]{2,12})(?:[\-/]?USDT|[\-/]?USD|/USDT)?\b"
)
_SKIP = {
    "LONG", "SHORT", "BUY", "SELL", "ENTRY", "EXIT", "CLOSE", "USDT", "USD",
    "SPOT", "FUTURES", "LEVERAGE", "TP", "SL", "STOP", "TARGET", "SIGNAL",
    "PREDATOR", "CRYPTO", "FREE", "VIP", "CHANNEL", "HTTP", "HTTPS", "WWW",
}


@dataclass(frozen=True)
class ParsedPredatorSignal:
    action: str  # buy | sell | watch
    symbol: str  # e.g. BTC-USD
    raw_symbol: str
    confidence: float
    reason: str


def _map_action(raw: str) -> str:
    a = raw.lower()
    if a in ("long", "buy", "entry"):
        return "buy"
    if a in ("short", "sell", "exit", "close"):
        return "sell"
    return "watch"


def _to_yahoo(sym: str) -> str:
    s = sym.upper().replace("USDT", "").replace("USD", "").strip("-/")
    if not s:
        return ""
    # Prefer crypto desk tickers
    return f"{s}-USD"


def parse_predator_message(text: str) -> list[ParsedPredatorSignal]:
    if not text or not text.strip():
        return []
    cleaned = re.sub(r"https?://\S+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    actions = list(_ACTION.finditer(cleaned))
    if not actions:
        # Soft glance only with explicit alert keywords (not the word "signal" alone in prose)
        if re.search(r"(?i)\b(predator|sygnał|#signal|entry zone|okazja|alert:)\b", cleaned):
            syms = []
            for m in _SYMBOL.finditer(cleaned):
                raw = m.group("sym").upper()
                if raw in _SKIP:
                    continue
                yahoo = _to_yahoo(raw)
                if yahoo:
                    syms.append(
                        ParsedPredatorSignal(
                            action="watch",
                            symbol=yahoo,
                            raw_symbol=raw,
                            confidence=55.0,
                            reason=f"Predator glance: {cleaned[:160]}",
                        )
                    )
            return syms[:3]
        return []

    out: list[ParsedPredatorSignal] = []
    for act in actions:
        action = _map_action(act.group("action"))
        # Prefer symbol after the action word
        window = cleaned[act.end() : act.end() + 48]
        sym_m = _SYMBOL.search(window) or _SYMBOL.search(cleaned)
        if not sym_m:
            continue
        raw = sym_m.group("sym").upper()
        if raw in _SKIP:
            continue
        yahoo = _to_yahoo(raw)
        if not yahoo:
            continue
        conf = 72.0 if action in ("buy", "sell") else 58.0
        out.append(
            ParsedPredatorSignal(
                action=action,
                symbol=yahoo,
                raw_symbol=raw,
                confidence=conf,
                reason=f"Telegram Predator: {act.group('action').upper()} {raw} — {cleaned[:140]}",
            )
        )
    # Dedupe by symbol keep first
    seen: set[str] = set()
    unique: list[ParsedPredatorSignal] = []
    for s in out:
        if s.symbol in seen:
            continue
        seen.add(s.symbol)
        unique.append(s)
    return unique[:5]

"""Degraded FOMO Ghost buffer when Cope Capital API is unreachable."""

from __future__ import annotations

import hashlib
import time
from typing import Any

# Handles inspired by public Cope/fomo docs examples + plausible top-book names.
# Used only when api.cope.capital is down — replaced by live leaderboard on recovery.
_SEED_HANDLES: list[tuple[str, float, float, int]] = [
    ("frankdegods", 295066.84, 67.0, 1404),
    ("Stacco", 182400.0, 71.2, 890),
    ("quotes", 156220.0, 84.6, 640),
    ("ansem", 142800.0, 62.4, 2100),
    ("blknoiz06", 128500.0, 58.1, 1750),
    ("traderpow", 119200.0, 69.0, 980),
    ("cryptojack", 105600.0, 64.5, 1120),
    ("threadguy", 98400.0, 55.8, 1540),
    ("loomdart", 87200.0, 61.0, 720),
    ("hsakatrades", 81500.0, 59.3, 880),
    ("gainzy", 76400.0, 66.2, 990),
    ("orangie", 72100.0, 57.4, 1340),
    ("whale_alert_x", 68900.0, 52.0, 430),
    ("solana_max", 65200.0, 60.8, 760),
    ("bagholder_pro", 61800.0, 48.5, 2100),
    ("base_whale", 58400.0, 63.1, 540),
    ("memecoin_king", 55100.0, 51.2, 3200),
    ("degen_alpha", 51900.0, 56.7, 1880),
    ("smart_bags", 49200.0, 70.4, 410),
    ("fomo_top", 46800.0, 54.0, 990),
    ("chain_scout", 44100.0, 58.9, 670),
    ("pump_radar", 41900.0, 49.6, 2400),
    ("liquidity_fox", 39700.0, 65.5, 520),
    ("theta_hunter", 37600.0, 61.8, 780),
    ("volume_viper", 35400.0, 53.3, 1450),
    ("alpha_nest", 33200.0, 68.0, 390),
    ("sol_sniper", 31100.0, 50.1, 1670),
    ("base_bull", 28900.0, 57.9, 610),
    ("ghost_entry", 26800.0, 62.6, 440),
    ("plecak_max", 24700.0, 55.0, 830),
]

_SEED_TOKENS: list[tuple[str, str, str]] = [
    ("BONK", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "solana"),
    ("WIF", "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "solana"),
    ("POPCAT", "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr", "solana"),
    ("MOODENG", "ED5nyyWUvgsJiS1DQ2B8u77bLXFzS48L5xA1pKo5UFHt", "solana"),
    ("PNUT", "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump", "solana"),
    ("KELLY", "0xKellyDemoMint000000000000000000000001", "base"),
    ("MUSHU", "MushuDemoMint1111111111111111111111111111", "solana"),
    ("FARTCOIN", "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", "solana"),
]


def seed_traders(limit: int = 30) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, (handle, pnl, win, trades) in enumerate(_SEED_HANDLES[: max(1, min(50, limit))], start=1):
        out.append(
            {
                "rank": i,
                "handle": handle,
                "pnl": pnl,
                "win_rate": win,
                "trades": trades,
                "raw": {"source": "offline_seed", "handle": handle},
            }
        )
    return out


def seed_bag_events(handles: list[str], *, now_ts: int | None = None, n: int = 3) -> list[dict[str, Any]]:
    """A few deterministic bag-ins for the current minute bucket (idempotent per bucket)."""
    ts = int(now_ts or time.time())
    bucket = ts // 60
    if not handles:
        return []
    events: list[dict[str, Any]] = []
    for i in range(max(1, min(8, n))):
        h = handles[(bucket + i) % len(handles)]
        sym, mint, chain = _SEED_TOKENS[(bucket + i) % len(_SEED_TOKENS)]
        usd = 800 + ((bucket * 17 + i * 113) % 9200)
        event_id = f"offline:{bucket}:{i}:{h}:{mint[:8]}"
        events.append(
            {
                "event_id": event_id,
                "handle": h,
                "action": "buy",
                "mint": mint,
                "symbol": sym,
                "chain": chain,
                "usd_amount": float(usd),
                "ts_unix": ts - i * 17,
                "raw": {"source": "offline_seed", "bucket": bucket},
            }
        )
    return events


def is_cope_unreachable(exc: BaseException | str) -> bool:
    text = str(exc).lower()
    markers = (
        "530",
        "1033",
        "cloudflare tunnel",
        "error code: 1033",
        "connecterror",
        "timed out",
        "timeout",
        "connection refused",
        "name or service not known",
        "temporary failure in name resolution",
        "network is unreachable",
        "non-json response",
    )
    return any(m in text for m in markers)


def humanize_cope_error(exc: BaseException | str) -> str:
    if is_cope_unreachable(exc):
        return (
            "Cope Capital API offline (Cloudflare tunnel 1033/530). "
            "Ghost runs in degraded buffer until upstream recovers."
        )
    msg = str(exc).strip().replace("\n", " ")
    return msg[:280] if msg else "Cope request failed"


def stable_demo_hint() -> str:
    return hashlib.sha256(b"fomo-ghost-offline").hexdigest()[:8]

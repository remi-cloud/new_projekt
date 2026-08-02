"""
Whale / large-player flow scanner for crypto.

Uses public endpoints (no API keys):
  - Binance aggTrades → large CEX market buys/sells (whale prints)
  - Binance futures taker long/short ratio → aggression
  - Binance futures global long/short account ratio
  - mempool.space recent txs (BTC) → on-chain large transfers

Bias:
  accumulate = big players buying / net aggressive buy
  distribute = big players selling / net aggressive sell
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "CyclicalTrader/2.1 (+whale-scanner)",
    "Accept": "application/json",
}

BINANCE_SYMBOLS = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
}

# Minimum notional (USD) to count as a whale print on CEX
WHALE_NOTIONAL_USD = {
    "BTC-USD": 150_000.0,
    "ETH-USD": 75_000.0,
    "SOL-USD": 35_000.0,
}

# BTC on-chain: satoshis threshold (~$250k at ~$65k/BTC ≈ 3.8 BTC → use 2.5 BTC)
BTC_ONCHAIN_SATS = int(2.5 * 100_000_000)

SPOT_TRADE_URLS = (
    "https://data-api.binance.vision/api/v3/aggTrades",
    "https://api.binance.com/api/v3/aggTrades",
)

FUTURES_TAKER_URLS = (
    "https://fapi.binance.com/futures/data/takerlongshortRatio",
    "https://data-api.binance.vision/futures/data/takerlongshortRatio",
)

FUTURES_LS_URLS = (
    "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
    "https://data-api.binance.vision/futures/data/globalLongShortAccountRatio",
)

CACHE_TTL_SECONDS = 90
_cache: dict[str, Any] = {"at": 0.0, "by_symbol": {}}


def _fmt_usd(n: float) -> str:
    abs_n = abs(n)
    if abs_n >= 1_000_000:
        return f"${n / 1_000_000:+.2f}M"
    if abs_n >= 1_000:
        return f"${n / 1_000:+.0f}k"
    return f"${n:+.0f}"


async def _get_json(
    client: httpx.AsyncClient,
    urls: tuple[str, ...],
    params: dict,
) -> Any | None:
    last_exc: Exception | None = None
    for url in urls:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code in (403, 418, 429, 451):
                last_exc = RuntimeError(f"{url} → {resp.status_code}")
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc:
        logger.debug("whale fetch failed %s: %s", urls[0], last_exc)
    return None


async def _fetch_large_prints(
    client: httpx.AsyncClient,
    catalog_symbol: str,
    bsym: str,
    threshold: float,
) -> dict[str, Any]:
    """Scan recent aggTrades for whale-sized market buys/sells."""
    data = await _get_json(
        client,
        SPOT_TRADE_URLS,
        {"symbol": bsym, "limit": 1000},
    )
    buys = 0
    sells = 0
    buy_usd = 0.0
    sell_usd = 0.0
    largest = 0.0
    if isinstance(data, list):
        for t in data:
            try:
                price = float(t["p"])
                qty = float(t["q"])
                notional = price * qty
                if notional < threshold:
                    continue
                # m=True → buyer is maker → aggressive sell; m=False → aggressive buy
                is_sell = bool(t.get("m"))
                if is_sell:
                    sells += 1
                    sell_usd += notional
                else:
                    buys += 1
                    buy_usd += notional
                largest = max(largest, notional)
            except (KeyError, TypeError, ValueError):
                continue
    net = buy_usd - sell_usd
    return {
        "large_buys": buys,
        "large_sells": sells,
        "buy_usd": round(buy_usd, 2),
        "sell_usd": round(sell_usd, 2),
        "net_usd": round(net, 2),
        "largest_usd": round(largest, 2),
        "threshold_usd": threshold,
        "source": "binance_aggTrades",
    }


async def _fetch_futures_ratios(
    client: httpx.AsyncClient,
    bsym: str,
) -> dict[str, Any]:
    taker = await _get_json(
        client,
        FUTURES_TAKER_URLS,
        {"symbol": bsym, "period": "1h", "limit": 2},
    )
    ls = await _get_json(
        client,
        FUTURES_LS_URLS,
        {"symbol": bsym, "period": "1h", "limit": 2},
    )
    out: dict[str, Any] = {"source": "binance_futures"}
    if isinstance(taker, list) and taker:
        row = taker[-1]
        try:
            buy_vol = float(row.get("buyVol", 0) or 0)
            sell_vol = float(row.get("sellVol", 0) or 0)
            ratio = float(row.get("buySellRatio", 0) or 0)
            out["taker_buy_vol"] = buy_vol
            out["taker_sell_vol"] = sell_vol
            out["taker_buy_sell_ratio"] = ratio
        except (TypeError, ValueError):
            pass
    if isinstance(ls, list) and ls:
        row = ls[-1]
        try:
            out["accounts_long_ratio"] = float(row.get("longAccount", 0) or 0)
            out["accounts_short_ratio"] = float(row.get("shortAccount", 0) or 0)
            out["accounts_long_short_ratio"] = float(row.get("longShortRatio", 0) or 0)
        except (TypeError, ValueError):
            pass
    return out


async def _fetch_btc_mempool_whales(client: httpx.AsyncClient) -> dict[str, Any]:
    """Recent large unconfirmed BTC transfers from mempool.space."""
    try:
        resp = await client.get("https://mempool.space/api/mempool/recent")
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("mempool.space recent failed: %s", exc)
        return {"large_txs": 0, "total_btc": 0.0, "source": "mempool.space", "ok": False}

    large = 0
    total_sats = 0
    if isinstance(data, list):
        for tx in data:
            try:
                # value can be in sats under vsize-related fields; prefer 'value'
                val = int(tx.get("value") or 0)
                if val >= BTC_ONCHAIN_SATS:
                    large += 1
                    total_sats += val
            except (TypeError, ValueError):
                continue
    return {
        "large_txs": large,
        "total_btc": round(total_sats / 1e8, 4),
        "threshold_btc": BTC_ONCHAIN_SATS / 1e8,
        "source": "mempool.space",
        "ok": True,
    }


def classify_whale_bias(
    prints: dict[str, Any],
    futures: dict[str, Any],
    onchain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Combine CEX prints + futures aggression (+ optional BTC on-chain) into a bias.
    Returns strength 0–100 and bias accumulate|distribute|neutral.
    """
    score = 0.0  # + accumulate / − distribute
    factors: list[str] = []

    net = float(prints.get("net_usd") or 0)
    buys = int(prints.get("large_buys") or 0)
    sells = int(prints.get("large_sells") or 0)
    thr = float(prints.get("threshold_usd") or 1)

    if buys + sells > 0:
        # Normalize net vs threshold × count
        score += max(-40, min(40, (net / max(thr * 3, 1)) * 12))
        if net > thr:
            factors.append(f"Whale printy CEX: net BUY {_fmt_usd(net)} ({buys}↑/{sells}↓)")
        elif net < -thr:
            factors.append(f"Whale printy CEX: net SELL {_fmt_usd(net)} ({buys}↑/{sells}↓)")
        else:
            factors.append(f"Whale printy CEX: mieszane ({buys}↑/{sells}↓, net {_fmt_usd(net)})")
    else:
        factors.append("Brak świeżych whale printów powyżej progu na CEX")

    taker = float(futures.get("taker_buy_sell_ratio") or 0)
    if taker > 0:
        # >1 = more aggressive buys
        if taker >= 1.15:
            score += 18
            factors.append(f"Taker futures agresywny BUY (ratio {taker:.2f})")
        elif taker <= 0.85:
            score -= 18
            factors.append(f"Taker futures agresywny SELL (ratio {taker:.2f})")
        else:
            factors.append(f"Taker futures neutralny (ratio {taker:.2f})")

    ls = float(futures.get("accounts_long_short_ratio") or 0)
    if ls > 0:
        # Crowded long → distribute risk; crowded short → squeeze/accumulate risk
        if ls >= 1.35:
            score -= 8
            factors.append(f"Tłok LONG na kontach (L/S {ls:.2f}) — ryzyko dystrybucji")
        elif ls <= 0.75:
            score += 8
            factors.append(f"Tłok SHORT na kontach (L/S {ls:.2f}) — ryzyko short-squeeze")

    if onchain and onchain.get("ok"):
        n = int(onchain.get("large_txs") or 0)
        btc = float(onchain.get("total_btc") or 0)
        if n >= 3:
            # Large on-chain activity without direction → intensity bump toward distribute
            # (big moves often precede exchange dumps); mild penalty
            score -= min(12, n * 2)
            factors.append(f"On-chain BTC: {n} duże tx (≥{onchain.get('threshold_btc')} BTC), Σ {btc:.2f} BTC w mempool")
        elif n > 0:
            factors.append(f"On-chain BTC: {n} duży transfer w mempool (Σ {btc:.2f} BTC)")
        else:
            factors.append("On-chain BTC: brak dużych transferów w świeżym mempool")

    if score >= 12:
        bias = "accumulate"
    elif score <= -12:
        bias = "distribute"
    else:
        bias = "neutral"

    strength = min(100.0, round(abs(score) * 1.6 + (8 if buys + sells >= 3 else 0), 1))
    if bias == "neutral":
        strength = min(strength, 35.0)

    if bias == "accumulate":
        summary = f"Wielcy gracze: WEJŚCIE / akumulacja (siła {strength:.0f})"
        side_hint = "long"
    elif bias == "distribute":
        summary = f"Wielcy gracze: WYJŚCIE / dystrybucja (siła {strength:.0f})"
        side_hint = "short"
    else:
        summary = f"Wielcy gracze: brak wyraźnego flow (siła {strength:.0f})"
        side_hint = "neutral"

    return {
        "bias": bias,
        "side_hint": side_hint,
        "strength": strength,
        "score": round(score, 2),
        "summary": summary,
        "factors": factors,
        "prints": prints,
        "futures": futures,
        "onchain": onchain,
    }


async def fetch_whale_for_symbol(
    symbol: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> Optional[dict[str, Any]]:
    sym = symbol.strip().upper()
    bsym = BINANCE_SYMBOLS.get(sym)
    if not bsym:
        return None
    thr = WHALE_NOTIONAL_USD.get(sym, 100_000.0)
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=14, headers=HEADERS)
    assert client is not None
    try:
        prints_t = _fetch_large_prints(client, sym, bsym, thr)
        fut_t = _fetch_futures_ratios(client, bsym)
        if sym == "BTC-USD":
            prints, futures, onchain = await asyncio.gather(
                prints_t, fut_t, _fetch_btc_mempool_whales(client)
            )
        else:
            prints, futures = await asyncio.gather(prints_t, fut_t)
            onchain = None
        classified = classify_whale_bias(prints, futures, onchain)
        return {
            "symbol": sym,
            "binance_symbol": bsym,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **classified,
        }
    except Exception as exc:
        logger.warning("Whale scan failed for %s: %s", sym, exc)
        return None
    finally:
        if owns_client:
            await client.aclose()


async def fetch_whale_snapshot(
    symbols: list[str] | None = None,
    *,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Return {SYMBOL: whale_signal} for crypto catalog symbols.
    Cached ~90s to keep scans snappy.
    """
    now = time.time()
    if not force and _cache["by_symbol"] and now - float(_cache["at"]) < CACHE_TTL_SECONDS:
        return dict(_cache["by_symbol"])

    wanted = [s.upper() for s in (symbols or list(BINANCE_SYMBOLS.keys()))]
    wanted = [s for s in wanted if s in BINANCE_SYMBOLS]
    if not wanted:
        return {}

    async with httpx.AsyncClient(timeout=14, headers=HEADERS) as client:
        results = await asyncio.gather(
            *[fetch_whale_for_symbol(s, client=client) for s in wanted]
        )

    by_sym: dict[str, dict[str, Any]] = {}
    for row in results:
        if row:
            by_sym[row["symbol"]] = row

    _cache["at"] = now
    _cache["by_symbol"] = by_sym
    logger.info(
        "Whale snapshot: %d symbols — %s",
        len(by_sym),
        ", ".join(
            f"{s}:{v['bias']}/{v['strength']:.0f}" for s, v in by_sym.items()
        ),
    )
    return dict(by_sym)


def get_cached_whale(symbol: str) -> Optional[dict[str, Any]]:
    return _cache["by_symbol"].get(symbol.strip().upper())

"""Bid/ask and liquidation heatmap helpers."""

from __future__ import annotations

import logging
import math
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

BINANCE_SYMBOLS = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
}

# Common futures leverage bands used to estimate liq clusters
LEVERAGE_BANDS = (5, 10, 20, 25, 50, 75, 100)


async def fetch_binance_book(symbol: str) -> Optional[dict]:
    """Return bid/ask/mid from Binance USDT-M futures bookTicker."""
    bsym = BINANCE_SYMBOLS.get(symbol)
    if not bsym:
        return None
    url = "https://fapi.binance.com/fapi/v1/ticker/bookTicker"
    try:
        async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params={"symbol": bsym})
            resp.raise_for_status()
            data = resp.json()
        bid = float(data["bidPrice"])
        ask = float(data["askPrice"])
        if bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid) * 100
        return {
            "bid": round(bid, 6),
            "ask": round(ask, 6),
            "mid": round(mid, 6),
            "spread_pct": round(spread_pct, 4),
            "source": "binance_futures",
        }
    except Exception as exc:
        logger.warning("Binance book failed for %s: %s", symbol, exc)
        return None


async def fetch_yahoo_bid_ask(symbol: str) -> Optional[dict]:
    """Pull bid/ask from Yahoo chart meta when available."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "1d", "interval": "1m"}
    try:
        async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            result = resp.json()["chart"]["result"]
            if not result:
                return None
            meta = result[0].get("meta") or {}
        bid = meta.get("bid")
        ask = meta.get("ask")
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if bid is None and ask is None:
            # Approximate thin spread around last when exchange doesn't publish BBO
            if not price:
                return None
            price = float(price)
            # Wider estimate for less liquid classes
            half = price * 0.0004
            bid, ask = price - half, price + half
            source = "yahoo_estimated"
        else:
            bid = float(bid) if bid is not None else float(price)
            ask = float(ask) if ask is not None else float(price)
            source = "yahoo"
        if bid <= 0 or ask <= 0:
            return None
        if ask < bid:
            bid, ask = ask, bid
        mid = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid) * 100 if mid else 0
        return {
            "bid": round(bid, 6),
            "ask": round(ask, 6),
            "mid": round(mid, 6),
            "spread_pct": round(spread_pct, 4),
            "source": source,
        }
    except Exception as exc:
        logger.warning("Yahoo bid/ask failed for %s: %s", symbol, exc)
        return None


async def fetch_bid_ask(symbol: str, asset_class: str) -> Optional[dict]:
    if asset_class == "crypto" or symbol in BINANCE_SYMBOLS:
        book = await fetch_binance_book(symbol)
        if book:
            return book
    return await fetch_yahoo_bid_ask(symbol)


def estimate_liquidation_heatmap(
    price: float,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[float] | None = None,
    bins: int = 48,
) -> dict:
    """
    Build a horizontal liquidation heatmap around current price.

    - Long liquidations sit BELOW price (green)
    - Short liquidations sit ABOVE price (red)
    Intensity blends leverage-band density with local volume concentration.
    """
    if price <= 0:
        return {"price": price, "bins": [], "max_intensity": 0}

    # Range: ±12% around mid (typical dense liq zone)
    span = price * 0.12
    lo = price - span
    hi = price + span
    step = (hi - lo) / bins

    long_intensity = [0.0] * bins
    short_intensity = [0.0] * bins

    # 1) Leverage liquidation anchors
    for lev in LEVERAGE_BANDS:
        # Isolated-ish approx: long liq ≈ price * (1 - 1/lev), short ≈ price * (1 + 1/lev)
        long_liq = price * (1 - 1 / lev)
        short_liq = price * (1 + 1 / lev)
        # Higher leverage = tighter to price = often denser retail cluster
        weight = math.sqrt(lev) / 2.5
        _accumulate(long_intensity, lo, step, bins, long_liq, weight, side="long", mid=price)
        _accumulate(short_intensity, lo, step, bins, short_liq, weight, side="short", mid=price)

    # 2) Volume-profile proxy near recent extremes (magnets for stops/liqs)
    if highs and lows and volumes and len(highs) == len(lows) == len(volumes):
        max_vol = max(volumes) or 1.0
        for h, l, v in zip(highs, lows, volumes):
            if h is None or l is None or v is None:
                continue
            mid_bar = (float(h) + float(l)) / 2
            vol_w = (float(v) / max_vol) * 1.8
            if mid_bar < price:
                _accumulate(long_intensity, lo, step, bins, mid_bar, vol_w, side="long", mid=price)
            elif mid_bar > price:
                _accumulate(short_intensity, lo, step, bins, mid_bar, vol_w, side="short", mid=price)

    # Soft peak around ±2–4% (classic cascade zone)
    for offset, w in ((-0.025, 1.4), (-0.04, 1.1), (0.025, 1.4), (0.04, 1.1)):
        lvl = price * (1 + offset)
        if offset < 0:
            _accumulate(long_intensity, lo, step, bins, lvl, w, side="long", mid=price)
        else:
            _accumulate(short_intensity, lo, step, bins, lvl, w, side="short", mid=price)

    max_i = max(max(long_intensity), max(short_intensity), 0.01)
    out_bins = []
    for i in range(bins):
        price_level = lo + (i + 0.5) * step
        li = long_intensity[i] / max_i
        si = short_intensity[i] / max_i
        out_bins.append(
            {
                "price": round(price_level, 6),
                "long_intensity": round(li, 4),
                "short_intensity": round(si, 4),
                "dominant": "long" if li >= si else "short",
                "intensity": round(max(li, si), 4),
            }
        )

    return {
        "price": round(price, 6),
        "range_low": round(lo, 6),
        "range_high": round(hi, 6),
        "bins": out_bins,
        "max_intensity": 1.0,
    }


def _accumulate(
    arr: list[float],
    lo: float,
    step: float,
    bins: int,
    level: float,
    weight: float,
    side: str,
    mid: float,
) -> None:
    if step <= 0:
        return
    # Gaussian-ish spread across neighboring bins
    center = (level - lo) / step
    sigma = max(bins * 0.035, 1.2)
    for i in range(bins):
        # Keep long mass below mid, short mass above mid
        price_i = lo + (i + 0.5) * step
        if side == "long" and price_i >= mid:
            continue
        if side == "short" and price_i <= mid:
            continue
        dist = abs(i - center)
        arr[i] += weight * math.exp(-(dist**2) / (2 * sigma**2))


async def fetch_volume_profile(symbol: str, asset_class: str) -> dict:
    """Recent OHLC + volume for heatmap weighting."""
    highs: list[float] = []
    lows: list[float] = []
    volumes: list[float] = []

    bsym = BINANCE_SYMBOLS.get(symbol)
    if bsym:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {"symbol": bsym, "interval": "1h", "limit": 72}
        try:
            async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                rows = resp.json()
            for row in rows:
                highs.append(float(row[2]))
                lows.append(float(row[3]))
                volumes.append(float(row[5]))
            return {"highs": highs, "lows": lows, "volumes": volumes, "source": "binance"}
        except Exception as exc:
            logger.warning("Binance klines failed for %s: %s", symbol, exc)

    # Yahoo fallback
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "5d", "interval": "1h"}
    try:
        async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            result = resp.json()["chart"]["result"]
            if not result:
                return {"highs": [], "lows": [], "volumes": [], "source": "none"}
            q = result[0]["indicators"]["quote"][0]
            for h, l, v in zip(q.get("high") or [], q.get("low") or [], q.get("volume") or []):
                if h is None or l is None:
                    continue
                highs.append(float(h))
                lows.append(float(l))
                volumes.append(float(v or 0))
        return {"highs": highs, "lows": lows, "volumes": volumes, "source": "yahoo"}
    except Exception as exc:
        logger.warning("Yahoo volume profile failed for %s: %s", symbol, exc)
        return {"highs": [], "lows": [], "volumes": [], "source": "none"}

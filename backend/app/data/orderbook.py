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


# Spot data API works from geo-restricted hosts where fapi.binance.com returns 451.
BINANCE_BOOK_URLS = (
    "https://data-api.binance.vision/api/v3/ticker/bookTicker",
    "https://api.binance.com/api/v3/ticker/bookTicker",
    "https://fapi.binance.com/fapi/v1/ticker/bookTicker",
)
BINANCE_KLINE_URLS = (
    ("https://data-api.binance.vision/api/v3/klines", {"interval": "1h", "limit": 72}),
    ("https://api.binance.com/api/v3/klines", {"interval": "1h", "limit": 72}),
    ("https://fapi.binance.com/fapi/v1/klines", {"interval": "1h", "limit": 72}),
)


async def fetch_binance_book(symbol: str) -> Optional[dict]:
    """Return bid/ask/mid — prefer Binance spot data-api (avoids futures 451)."""
    bsym = BINANCE_SYMBOLS.get(symbol)
    if not bsym:
        return None
    last_exc: Exception | None = None
    try:
        async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
            for url in BINANCE_BOOK_URLS:
                try:
                    resp = await client.get(url, params={"symbol": bsym})
                    resp.raise_for_status()
                    data = resp.json()
                    bid = float(data["bidPrice"])
                    ask = float(data["askPrice"])
                    if bid <= 0 or ask <= 0:
                        continue
                    mid = (bid + ask) / 2
                    spread_pct = ((ask - bid) / mid) * 100
                    source = "binance_spot" if "fapi" not in url else "binance_futures"
                    return {
                        "bid": round(bid, 6),
                        "ask": round(ask, 6),
                        "mid": round(mid, 6),
                        "spread_pct": round(spread_pct, 4),
                        "source": source,
                    }
                except Exception as exc:
                    last_exc = exc
                    continue
    except Exception as exc:
        last_exc = exc
    logger.warning("Binance book failed for %s: %s", symbol, last_exc)
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


def _column_intensities(
    mid: float,
    lo: float,
    step: float,
    bins: int,
    highs: list[float] | None,
    lows: list[float] | None,
    volumes: list[float] | None,
    slice_start: int = 0,
    slice_end: int | None = None,
) -> tuple[list[float], list[float]]:
    """Build long/short intensity arrays for one time column around mid price."""
    long_intensity = [0.0] * bins
    short_intensity = [0.0] * bins

    for lev in LEVERAGE_BANDS:
        long_liq = mid * (1 - 1 / lev)
        short_liq = mid * (1 + 1 / lev)
        weight = math.sqrt(lev) / 2.5
        _accumulate(long_intensity, lo, step, bins, long_liq, weight, side="long", mid=mid)
        _accumulate(short_intensity, lo, step, bins, short_liq, weight, side="short", mid=mid)

    if highs and lows and volumes and len(highs) == len(lows) == len(volumes):
        end = slice_end if slice_end is not None else len(highs)
        start = max(0, min(slice_start, end))
        segment_v = volumes[start:end] or [1.0]
        max_vol = max(segment_v) or 1.0
        for h, l, v in zip(highs[start:end], lows[start:end], volumes[start:end]):
            if h is None or l is None or v is None:
                continue
            mid_bar = (float(h) + float(l)) / 2
            vol_w = (float(v) / max_vol) * 1.8
            if mid_bar < mid:
                _accumulate(long_intensity, lo, step, bins, mid_bar, vol_w, side="long", mid=mid)
            elif mid_bar > mid:
                _accumulate(short_intensity, lo, step, bins, mid_bar, vol_w, side="short", mid=mid)

    for offset, w in ((-0.025, 1.4), (-0.04, 1.1), (0.025, 1.4), (0.04, 1.1)):
        lvl = mid * (1 + offset)
        if offset < 0:
            _accumulate(long_intensity, lo, step, bins, lvl, w, side="long", mid=mid)
        else:
            _accumulate(short_intensity, lo, step, bins, lvl, w, side="short", mid=mid)

    return long_intensity, short_intensity


def estimate_liquidation_heatmap(
    price: float,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[float] | None = None,
    bins: int = 48,
    time_cols: int = 24,
) -> dict:
    """
    Build a CoinGlass-style 2D liquidation heatmap (time × price).

    - Long liquidations sit BELOW price (green)
    - Short liquidations sit ABOVE price (red)
    Intensity blends leverage-band density with local volume concentration.

    Returns:
      bins: latest 1D slice (compat / markers)
      columns: list of time columns, each a list of cells (low→high price)
    """
    if price <= 0:
        return {
            "price": price,
            "bins": [],
            "columns": [],
            "max_intensity": 0,
            "range_low": 0,
            "range_high": 0,
        }

    span = price * 0.12
    lo = price - span
    hi = price + span
    if highs and lows:
        try:
            hist_lo = min(float(x) for x in lows if x is not None)
            hist_hi = max(float(x) for x in highs if x is not None)
            lo = min(lo, hist_lo)
            hi = max(hi, hist_hi)
        except ValueError:
            pass
    step = (hi - lo) / bins if bins else 1.0

    n = len(highs) if highs and lows and volumes else 0
    cols = max(1, time_cols)
    columns: list[list[dict]] = []
    global_max = 0.01

    raw_cols: list[tuple[list[float], list[float]]] = []
    for c in range(cols):
        if n >= 4:
            # Expanding window ending near "now" so clusters evolve left→right
            end = max(1, int((c + 1) / cols * n))
            start = max(0, end - max(4, n // 8))
            mid = (float(highs[end - 1]) + float(lows[end - 1])) / 2
        else:
            start, end = 0, n
            mid = price
        li, si = _column_intensities(mid, lo, step, bins, highs, lows, volumes, start, end)
        raw_cols.append((li, si))
        global_max = max(global_max, max(li or [0]), max(si or [0]))

    for li, si in raw_cols:
        col_bins = []
        for i in range(bins):
            price_level = lo + (i + 0.5) * step
            l_norm = li[i] / global_max
            s_norm = si[i] / global_max
            col_bins.append(
                {
                    "price": round(price_level, 6),
                    "long_intensity": round(l_norm, 4),
                    "short_intensity": round(s_norm, 4),
                    "dominant": "long" if l_norm >= s_norm else "short",
                    "intensity": round(max(l_norm, s_norm), 4),
                }
            )
        columns.append(col_bins)

    out_bins = columns[-1] if columns else []

    return {
        "price": round(price, 6),
        "range_low": round(lo, 6),
        "range_high": round(hi, 6),
        "bins": out_bins,
        "columns": columns,
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
        last_exc: Exception | None = None
        try:
            async with httpx.AsyncClient(timeout=12, headers=YAHOO_HEADERS) as client:
                for url, extra in BINANCE_KLINE_URLS:
                    try:
                        resp = await client.get(
                            url, params={"symbol": bsym, **extra}
                        )
                        resp.raise_for_status()
                        rows = resp.json()
                        for row in rows:
                            highs.append(float(row[2]))
                            lows.append(float(row[3]))
                            volumes.append(float(row[5]))
                        return {
                            "highs": highs,
                            "lows": lows,
                            "volumes": volumes,
                            "source": "binance",
                        }
                    except Exception as exc:
                        last_exc = exc
                        highs.clear()
                        lows.clear()
                        volumes.clear()
                        continue
        except Exception as exc:
            last_exc = exc
        logger.warning("Binance klines failed for %s: %s", symbol, last_exc)

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

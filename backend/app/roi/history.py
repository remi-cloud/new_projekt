"""Long-range OHLCV history (Yahoo period1/period2) for ROI backtests."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from urllib.parse import quote as url_quote

import httpx

from app.data.assets import MONITORED_ASSETS
from app.models.schemas import ChartCandle

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

# Earliest sensible defaults per class (Yahoo may start later)
DEFAULT_FROM: dict[str, date] = {
    "crypto": date(2014, 1, 1),
    "stock": date(2000, 1, 1),
    "etf": date(2000, 1, 1),
    "index": date(2000, 1, 1),
    "bond": date(2000, 1, 1),
    "commodity": date(2000, 1, 1),
    "forex": date(2000, 1, 1),
}

_cache: dict[str, tuple[float, list[ChartCandle]]] = {}
_CACHE_TTL = 3600 * 6  # 6h


def _to_unix(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def _pick_interval(start: date, end: date) -> str:
    days = (end - start).days
    if days <= 730:
        return "1d"
    if days <= 3650:
        return "1wk"
    return "1mo"


def _parse_candles(result: dict) -> list[ChartCandle]:
    r = result[0]
    timestamps = r.get("timestamp") or []
    q = r["indicators"]["quote"][0]
    candles: list[ChartCandle] = []
    for i, ts in enumerate(timestamps):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if o is None or h is None or l is None or c is None:
            continue
        vol = q.get("volume", [None] * len(timestamps))[i]
        candles.append(
            ChartCandle(
                time=int(ts),
                open=round(float(o), 6),
                high=round(float(h), 6),
                low=round(float(l), 6),
                close=round(float(c), 6),
                volume=float(vol) if vol else None,
            )
        )
    return candles


async def fetch_long_history(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
) -> tuple[list[ChartCandle], date | None, date | None]:
    """
    Fetch weekly/daily history from Yahoo from ~2000 (or crypto ~2014).
    Returns (candles, data_start, data_end).
    """
    meta = ASSET_MAP.get(symbol)
    if not meta:
        raise ValueError(f"Unknown symbol: {symbol}")

    asset_class = meta.get("asset_class", "stock")
    today = datetime.now(timezone.utc).date()
    end = end or today
    start = start or DEFAULT_FROM.get(asset_class, date(2000, 1, 1))
    if start > end:
        start, end = end, start

    cache_key = f"{symbol}:{start.isoformat()}:{end.isoformat()}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        candles = cached[1]
        if candles:
            return (
                candles,
                datetime.fromtimestamp(candles[0].time, tz=timezone.utc).date(),
                datetime.fromtimestamp(candles[-1].time, tz=timezone.utc).date(),
            )
        return candles, None, None

    interval = _pick_interval(start, end)
    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    params = {
        "period1": _to_unix(start),
        "period2": _to_unix(end) + 86400,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }

    candles: list[ChartCandle] = []
    try:
        async with httpx.AsyncClient(timeout=40, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params=params, follow_redirects=True)
            resp.raise_for_status()
            payload = resp.json()
            result = payload.get("chart", {}).get("result")
            if result:
                candles = _parse_candles(result)
    except Exception as exc:
        logger.warning("Long history fetch failed %s: %s", symbol, exc)
        candles = []

    # Soft fallback: try max range weekly if empty
    if not candles:
        try:
            async with httpx.AsyncClient(timeout=40, headers=YAHOO_HEADERS) as client:
                resp = await client.get(
                    url,
                    params={"range": "max", "interval": "1wk"},
                    follow_redirects=True,
                )
                resp.raise_for_status()
                result = resp.json().get("chart", {}).get("result")
                if result:
                    candles = _parse_candles(result)
                    # trim to requested window
                    t0, t1 = _to_unix(start), _to_unix(end) + 86400
                    candles = [c for c in candles if t0 <= c.time <= t1]
        except Exception as exc:
            logger.warning("Long history fallback failed %s: %s", symbol, exc)

    _cache[cache_key] = (time.time(), candles)
    if not candles:
        return [], None, None
    data_start = datetime.fromtimestamp(candles[0].time, tz=timezone.utc).date()
    data_end = datetime.fromtimestamp(candles[-1].time, tz=timezone.utc).date()
    return candles, data_start, data_end

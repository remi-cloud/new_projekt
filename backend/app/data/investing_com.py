"""Investing.com data client for Polish market (api.investing.com + curl_cffi)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from curl_cffi import requests as cf_requests

from app.data.polish_investing_map import POLISH_INVESTING_IDS, POLISH_INVESTING_SEARCH
from app.models.schemas import AssetClass, AssetQuote, ChartCandle, ChartResponse

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "polish_investing_cache.json"

INVESTING_CHART_PRESETS: dict[str, tuple[str, str, int]] = {
    "1D": ("P1D", "PT5M", 160),
    "1W": ("P5D", "PT1H", 160),
    "1M": ("P1M", "PT1H", 160),
    "3M": ("P3M", "P1D", 90),
    "1Y": ("P1Y", "P1D", 120),
    "MAX": ("MAX", "P1W", 120),
}

QUOTE_CHART = ("P1Y", "P1D", 120)

_session: cf_requests.Session | None = None
_session_lock = asyncio.Lock()
_last_request_at = 0.0
_min_interval_s = 0.35


def _get_session() -> cf_requests.Session:
    global _session
    if _session is None:
        _session = cf_requests.Session(impersonate="chrome120")
    return _session


def _load_cache() -> dict[str, int]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return {k: int(v) for k, v in json.loads(CACHE_PATH.read_text()).items()}
    except Exception:
        return {}


def _save_cache(cache: dict[str, int]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def get_investing_id(symbol: str) -> int | None:
    if symbol in POLISH_INVESTING_IDS:
        return POLISH_INVESTING_IDS[symbol]
    return _load_cache().get(symbol)


def uses_investing(symbol: str, region: str | None = None) -> bool:
    return region == "pl" or symbol in POLISH_INVESTING_IDS or symbol in POLISH_INVESTING_SEARCH


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _min_interval_s:
        time.sleep(_min_interval_s - elapsed)
    _last_request_at = time.monotonic()


def _warm_session(session: cf_requests.Session) -> None:
    headers = {
        "Accept": "application/json",
        "Domain-Id": "pl",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    _throttle()
    session.get(
        "https://api.investing.com/api/search/v2/search?q=PKO&lang=pl&type=quotes",
        headers=headers,
        timeout=25,
    )


def _search_pair_id_sync(query: str) -> int | None:
    session = _get_session()
    _warm_session(session)
    headers = {
        "Accept": "application/json",
        "Domain-Id": "pl",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    url = (
        "https://api.investing.com/api/search/v2/search?"
        f"q={quote(query)}&lang=pl&type=quotes"
    )
    _throttle()
    resp = session.get(url, headers=headers, timeout=25)
    if resp.status_code != 200:
        return None
    quotes = resp.json().get("quotes") or []
    pick = next(
        (q for q in quotes if q.get("exchange") == "Warszawa" or "Warszawa" in q.get("type", "")),
        quotes[0] if quotes else None,
    )
    return int(pick["id"]) if pick else None


def _resolve_pair_id_sync(symbol: str) -> int | None:
    pair_id = get_investing_id(symbol)
    if pair_id:
        return pair_id
    query = POLISH_INVESTING_SEARCH.get(symbol)
    if not query:
        return None
    cache = _load_cache()
    if symbol in cache:
        return cache[symbol]
    found = _search_pair_id_sync(query)
    if found:
        cache[symbol] = found
        _save_cache(cache)
    return found


def _fetch_chart_sync(
    pair_id: int,
    period: str,
    interval: str,
    pointscount: int,
) -> list[list[Any]] | None:
    session = _get_session()
    _warm_session(session)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Domain-Id": "pl",
        "Origin": "https://pl.investing.com",
        "Referer": "https://pl.investing.com/",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    url = (
        f"https://api.investing.com/api/financialdata/{pair_id}/historical/chart/"
        f"?period={period}&interval={interval}&pointscount={pointscount}"
    )
    for attempt in range(3):
        _throttle()
        resp = session.get(url, headers=headers, timeout=25)
        if resp.status_code == 200:
            payload = resp.json()
            data = payload.get("data") or []
            return data if data else None
        if resp.status_code == 500 and "point count" in resp.text:
            # Retry with allowed point count from error message
            for pc in (120, 90, 160, 60):
                retry_url = (
                    f"https://api.investing.com/api/financialdata/{pair_id}/historical/chart/"
                    f"?period={period}&interval={interval}&pointscount={pc}"
                )
                _throttle()
                retry = session.get(retry_url, headers=headers, timeout=25)
                if retry.status_code == 200:
                    data = retry.json().get("data") or []
                    return data if data else None
        if resp.status_code == 403:
            time.sleep(0.8 * (attempt + 1))
            _warm_session(session)
            continue
        logger.warning("Investing chart %s failed: %s %s", pair_id, resp.status_code, resp.text[:120])
        break
    return None


def _parse_quote_from_candles(
    candles: list[list[Any]],
) -> tuple[float, float | None, float | None, dict[str, float | None]]:
    closes = [float(c[4]) for c in candles if c and c[4] is not None]
    highs = [float(c[2]) for c in candles if c and c[2] is not None]
    lows = [float(c[3]) for c in candles if c and c[3] is not None]
    if not closes:
        raise ValueError("No closes in investing.com chart")

    price = closes[-1]
    change_24h = None
    change_7d = None
    if len(closes) >= 2:
        change_24h = round(((price - closes[-2]) / closes[-2]) * 100, 2)
    if len(closes) >= 6:
        change_7d = round(((price - closes[-6]) / closes[-6]) * 100, 2)
    elif len(closes) >= 2:
        change_7d = round(((price - closes[0]) / closes[0]) * 100, 2)

    stats = {
        "high_52w": max(highs) if highs else None,
        "low_52w": min(lows) if lows else None,
    }
    return price, change_24h, change_7d, stats


def _candles_to_chart_response(
    symbol: str,
    name: str,
    preset: str,
    interval: str,
    raw: list[list[Any]],
) -> ChartResponse | None:
    candles: list[ChartCandle] = []
    for row in raw:
        if not row or len(row) < 5:
            continue
        ts_ms, o, h, l, c = row[0], row[1], row[2], row[3], row[4]
        vol = row[5] if len(row) > 5 else None
        if None in (o, h, l, c):
            continue
        candles.append(
            ChartCandle(
                time=int(ts_ms // 1000),
                open=round(float(o), 6),
                high=round(float(h), 6),
                low=round(float(l), 6),
                close=round(float(c), 6),
                volume=float(vol) if vol else None,
            )
        )
    if not candles:
        return None

    current = candles[-1].close
    prev = candles[-2].close if len(candles) >= 2 else current
    change = round(current - prev, 6)
    change_pct = round((change / prev) * 100, 2) if prev else 0.0

    return ChartResponse(
        symbol=symbol,
        name=name,
        interval=interval,
        range=preset,
        currency="PLN",
        candles=candles,
        current_price=current,
        change=change,
        change_pct=change_pct,
        day_high=candles[-1].high,
        day_low=candles[-1].low,
        prev_close=round(prev, 6),
    )


async def fetch_investing_quote(
    asset: dict,
    now: datetime | None = None,
) -> tuple[AssetQuote | None, dict]:
    now = now or datetime.now(timezone.utc)
    symbol = asset["symbol"]
    pair_id = await asyncio.to_thread(_resolve_pair_id_sync, symbol)
    if not pair_id:
        return None, {}

    period, interval, points = QUOTE_CHART
    raw = await asyncio.to_thread(_fetch_chart_sync, pair_id, period, interval, points)
    if not raw:
        return None, {}

    try:
        price, change_24h, change_7d, stats = _parse_quote_from_candles(raw)
    except ValueError:
        return None, {}

    quote = AssetQuote(
        symbol=symbol,
        name=asset["name"],
        asset_class=AssetClass(asset["asset_class"]),
        price=round(price, 4),
        change_pct_24h=change_24h,
        change_pct_7d=change_7d,
        currency="PLN",
        updated_at=now,
    )
    return quote, stats


async def fetch_investing_chart(symbol: str, preset: str, meta: dict) -> ChartResponse | None:
    if preset not in INVESTING_CHART_PRESETS:
        preset = "3M"
    period, interval, points = INVESTING_CHART_PRESETS[preset]
    pair_id = await asyncio.to_thread(_resolve_pair_id_sync, symbol)
    if not pair_id:
        return None
    raw = await asyncio.to_thread(_fetch_chart_sync, pair_id, period, interval, points)
    if not raw:
        return None
    return _candles_to_chart_response(symbol, meta.get("name", symbol), preset, interval, raw)

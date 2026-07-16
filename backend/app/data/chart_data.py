"""Chart data fetching from Yahoo Finance."""

import logging
from urllib.parse import quote as url_quote

import httpx

from app.data.assets import MONITORED_ASSETS
from app.data.investing_com import INVESTING_CHART_PRESETS, fetch_investing_chart, uses_investing
from app.models.schemas import ChartCandle, ChartResponse

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

# preset -> (yahoo_range, yahoo_interval, max_candles, aggregate_n)
# Crypto 24/7: Yahoo often returns 0 bars for range=1d on 1m/5m — use 5d+.
CHART_PRESETS: dict[str, tuple[str, str, int | None, int]] = {
    "1m": ("5d", "1m", 180, 1),      # ~3 h of 1-min bars
    "5m": ("5d", "5m", 144, 1),      # ~12 h
    "15m": ("5d", "15m", 96, 1),     # ~24 h
    "30m": ("1mo", "30m", 96, 1),    # ~2 days
    "1H": ("1mo", "60m", 168, 1),    # ~1 week hourly
    "4H": ("3mo", "60m", 180, 4),    # 4 x 1h → 4h candles
    "1D": ("1mo", "30m", None, 1),
    "1W": ("3mo", "1h", None, 1),
    "1M": ("6mo", "1d", None, 1),
    "3M": ("1y", "1d", None, 1),
    "1Y": ("2y", "1d", None, 1),
    "MAX": ("5y", "1wk", None, 1),
    "10Y": ("10y", "1wk", None, 1),
}

# Fallback Yahoo ranges when primary returns empty (common for crypto).
PRESET_RANGE_FALLBACKS: dict[str, list[str]] = {
    "1m": ["5d", "7d", "1mo"],
    "5m": ["5d", "1mo"],
    "15m": ["5d", "1mo", "3mo"],
    "30m": ["1mo", "3mo"],
    "1H": ["1mo", "3mo", "6mo"],
    "4H": ["3mo", "6mo", "1y"],
}

INTRADAY_PRESETS = frozenset({"1m", "5m", "15m", "30m", "1H", "4H"})


def _aggregate_candles(candles: list[ChartCandle], group: int) -> list[ChartCandle]:
    if group <= 1:
        return candles
    merged: list[ChartCandle] = []
    for i in range(0, len(candles), group):
        chunk = candles[i : i + group]
        if len(chunk) < group:
            break
        vols = [c.volume for c in chunk if c.volume is not None]
        merged.append(
            ChartCandle(
                time=chunk[0].time,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(vols) if vols else None,
            )
        )
    return merged


def _parse_yahoo_candles(result: dict) -> tuple[list[ChartCandle], dict]:
    r = result[0]
    m = r["meta"]
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
    return candles, m


async def _fetch_yahoo_candles(
    client: httpx.AsyncClient,
    symbol: str,
    yahoo_range: str,
    interval: str,
) -> tuple[list[ChartCandle], dict | None]:
    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    params = {"range": yahoo_range, "interval": interval}

    resp = await client.get(url, params=params)
    resp.raise_for_status()
    payload = resp.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        return [], None

    candles, meta = _parse_yahoo_candles(result)
    return candles, meta


def _ranges_for_preset(preset: str, primary_range: str) -> list[str]:
    fallbacks = PRESET_RANGE_FALLBACKS.get(preset, [])
    ordered: list[str] = []
    for r in [primary_range, *fallbacks]:
        if r not in ordered:
            ordered.append(r)
    return ordered


async def fetch_chart(symbol: str, preset: str = "3M") -> ChartResponse | None:
    """Fetch OHLCV candles for a symbol."""
    if preset not in CHART_PRESETS:
        preset = "3M"
    yahoo_range, interval, max_candles, aggregate_n = CHART_PRESETS[preset]
    meta_info = ASSET_MAP.get(symbol, {"name": symbol, "symbol": symbol})

    if (
        uses_investing(symbol, meta_info.get("region"))
        and preset not in INTRADAY_PRESETS
        and preset in INVESTING_CHART_PRESETS
    ):
        investing_chart = await fetch_investing_chart(symbol, preset, meta_info)
        if investing_chart:
            return investing_chart
        logger.warning("Investing.com chart fallback to Yahoo for %s", symbol)

    ranges_to_try = _ranges_for_preset(preset, yahoo_range)

    try:
        async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
            candles: list[ChartCandle] = []
            ymeta: dict | None = None
            used_range = yahoo_range

            for yr in ranges_to_try:
                candles, ymeta = await _fetch_yahoo_candles(client, symbol, yr, interval)
                if candles:
                    used_range = yr
                    break
                logger.info(
                    "Yahoo empty for %s preset=%s range=%s interval=%s — trying fallback",
                    symbol,
                    preset,
                    yr,
                    interval,
                )

            if not candles or ymeta is None:
                return None

            if max_candles:
                candles = candles[-max_candles:]
            if aggregate_n > 1:
                candles = _aggregate_candles(candles, aggregate_n)
            if not candles:
                return None

            display_interval = preset.lower() if preset in INTRADAY_PRESETS else interval

            current = float(ymeta.get("regularMarketPrice") or candles[-1].close)
            prev = float(
                ymeta.get("chartPreviousClose")
                or ymeta.get("previousClose")
                or (candles[-2].close if len(candles) >= 2 else current)
            )
            change = round(current - prev, 6)
            change_pct = round((change / prev) * 100, 2) if prev else 0.0

            return ChartResponse(
                symbol=symbol,
                name=meta_info.get("name", symbol),
                interval=display_interval,
                range=preset,
                currency=ymeta.get("currency", "USD"),
                candles=candles,
                current_price=round(current, 6),
                change=change,
                change_pct=change_pct,
                day_high=float(ymeta["regularMarketDayHigh"])
                if ymeta.get("regularMarketDayHigh")
                else None,
                day_low=float(ymeta["regularMarketDayLow"])
                if ymeta.get("regularMarketDayLow")
                else None,
                prev_close=round(prev, 6),
            )
    except Exception as exc:
        logger.warning("Chart fetch failed for %s preset=%s: %s", symbol, preset, exc)
        return None

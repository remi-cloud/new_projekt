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
# aggregate_n: merge N consecutive bars (used for 4H from 1h data)
CHART_PRESETS: dict[str, tuple[str, str, int | None, int]] = {
    "1m": ("1d", "1m", 60, 1),       # ~1 h of 1-min bars
    "5m": ("1d", "5m", 48, 1),       # ~4 h
    "15m": ("1d", "15m", 16, 1),     # ~4 h
    "30m": ("5d", "30m", 8, 1),      # ~4 h
    "1H": ("5d", "60m", 12, 1),     # ~12 h hourly
    "4H": ("1mo", "60m", 48, 4),     # 4 x 1h → 4h candles (~8 days)
    "1D": ("1d", "5m", None, 1),
    "1W": ("5d", "15m", None, 1),
    "1M": ("1mo", "1h", None, 1),
    "3M": ("3mo", "1d", None, 1),
    "1Y": ("1y", "1d", None, 1),
    "MAX": ("5y", "1wk", None, 1),
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


async def fetch_chart(symbol: str, preset: str = "3M") -> ChartResponse | None:
    """Fetch OHLCV candles for a symbol."""
    if preset not in CHART_PRESETS:
        preset = "3M"
    yahoo_range, interval, max_candles, aggregate_n = CHART_PRESETS[preset]
    meta = ASSET_MAP.get(symbol, {"name": symbol, "symbol": symbol})

    if (
        uses_investing(symbol, meta.get("region"))
        and preset not in INTRADAY_PRESETS
        and preset in INVESTING_CHART_PRESETS
    ):
        investing_chart = await fetch_investing_chart(symbol, preset, meta)
        if investing_chart:
            return investing_chart
        logger.warning("Investing.com chart fallback to Yahoo for %s", symbol)

    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    params = {"range": yahoo_range, "interval": interval}

    try:
        async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            result = resp.json()["chart"]["result"]
            if not result:
                return None

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

            if not candles:
                return None

            if max_candles:
                candles = candles[-max_candles:]
            if aggregate_n > 1:
                candles = _aggregate_candles(candles, aggregate_n)
            if not candles:
                return None

            display_interval = preset.lower() if preset in INTRADAY_PRESETS else interval

            current = float(m.get("regularMarketPrice") or candles[-1].close)
            prev = float(m.get("chartPreviousClose") or m.get("previousClose") or candles[-2].close if len(candles) >= 2 else current)
            change = round(current - prev, 6)
            change_pct = round((change / prev) * 100, 2) if prev else 0.0

            return ChartResponse(
                symbol=symbol,
                name=meta.get("name", symbol),
                interval=display_interval,
                range=preset,
                currency=m.get("currency", "USD"),
                candles=candles,
                current_price=round(current, 6),
                change=change,
                change_pct=change_pct,
                day_high=float(m["regularMarketDayHigh"]) if m.get("regularMarketDayHigh") else None,
                day_low=float(m["regularMarketDayLow"]) if m.get("regularMarketDayLow") else None,
                prev_close=round(prev, 6),
            )
    except Exception as exc:
        logger.warning("Chart fetch failed for %s: %s", symbol, exc)
        return None

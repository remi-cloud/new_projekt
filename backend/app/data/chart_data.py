"""Chart data fetching from Yahoo Finance."""

import logging
from urllib.parse import quote as url_quote

import httpx

from app.data.assets import MONITORED_ASSETS
from app.models.schemas import ChartCandle, ChartResponse

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

CHART_PRESETS: dict[str, tuple[str, str]] = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "15m"),
    "1M": ("1mo", "1h"),
    "3M": ("3mo", "1d"),
    "1Y": ("1y", "1d"),
    "MAX": ("5y", "1wk"),
}


async def fetch_chart(symbol: str, preset: str = "3M") -> ChartResponse | None:
    """Fetch OHLCV candles for a symbol."""
    if preset not in CHART_PRESETS:
        preset = "3M"
    yahoo_range, interval = CHART_PRESETS[preset]
    meta = ASSET_MAP.get(symbol, {"name": symbol, "symbol": symbol})

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

            current = float(m.get("regularMarketPrice") or candles[-1].close)
            prev = float(m.get("chartPreviousClose") or m.get("previousClose") or candles[-2].close if len(candles) >= 2 else current)
            change = round(current - prev, 6)
            change_pct = round((change / prev) * 100, 2) if prev else 0.0

            return ChartResponse(
                symbol=symbol,
                name=meta.get("name", symbol),
                interval=interval,
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

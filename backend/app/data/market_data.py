import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.data.assets import MONITORED_ASSETS
from app.models.schemas import AssetClass, AssetQuote

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

COINGECKO_IDS = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
}

MS_PER_DAY = 86_400_000


def pct_change(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def closest_price_before(
    series: list[tuple[int, float]], target_ms: int
) -> float | None:
    """Return the price at the latest point at or before target_ms."""
    candidate: float | None = None
    for ts, price in series:
        if ts <= target_ms:
            candidate = price
        else:
            break
    return candidate


async def fetch_bitcoin_ath() -> tuple[date, float, float]:
    """Return (ath_date, ath_price, current_price) via CoinGecko."""
    url = f"{settings.coingecko_base_url}/coins/bitcoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    }
    async with httpx.AsyncClient(timeout=20, headers=YAHOO_HEADERS) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    market = data["market_data"]
    ath_price = float(market["ath"]["usd"])
    ath_ts = market["ath_date"]["usd"]
    ath_date = datetime.fromisoformat(ath_ts.replace("Z", "+00:00")).date()
    current_price = float(market["current_price"]["usd"])
    return ath_date, ath_price, current_price


async def fetch_quotes() -> list[AssetQuote]:
    now = datetime.now(timezone.utc)
    quotes: list[AssetQuote] = []

    async with httpx.AsyncClient(timeout=20, headers=YAHOO_HEADERS) as client:
        tasks = [_fetch_single_quote(client, asset, now) for asset in MONITORED_ASSETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, AssetQuote):
            quotes.append(result)
        elif isinstance(result, Exception):
            logger.warning("Quote fetch error: %s", result)

    return quotes


async def _fetch_single_quote(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> Optional[AssetQuote]:
    symbol = asset["symbol"]
    if symbol in COINGECKO_IDS:
        return await _fetch_coingecko_quote(client, asset, now)
    return await _fetch_yahoo_quote(client, asset, now)


async def _fetch_coingecko_quote(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> Optional[AssetQuote]:
    coin_id = COINGECKO_IDS[asset["symbol"]]
    url = f"{settings.coingecko_base_url}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": "7"}
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        prices = resp.json().get("prices", [])
        if not prices:
            return None

        series = [(int(p[0]), float(p[1])) for p in prices]
        price = series[-1][1]
        now_ms = series[-1][0]
        change_24h = pct_change(price, closest_price_before(series, now_ms - MS_PER_DAY))
        change_7d = pct_change(price, series[0][1])

        return AssetQuote(
            symbol=asset["symbol"],
            name=asset["name"],
            asset_class=AssetClass(asset["asset_class"]),
            price=round(price, 4),
            change_pct_24h=change_24h,
            change_pct_7d=change_7d,
            updated_at=now,
        )
    except Exception as exc:
        logger.warning("CoinGecko quote failed for %s: %s", asset["symbol"], exc)
        return None


async def _fetch_yahoo_quote(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> Optional[AssetQuote]:
    symbol = asset["symbol"]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "1mo", "interval": "1d"}
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"]
        if not result:
            return None

        meta = result[0]["meta"]
        timestamps = result[0].get("timestamp") or []
        closes_raw = result[0]["indicators"]["quote"][0]["close"]
        series = [
            (int(ts) * 1000, float(close))
            for ts, close in zip(timestamps, closes_raw)
            if close is not None
        ]

        if not series:
            price = float(meta.get("regularMarketPrice", 0))
            if not price:
                return None
            return AssetQuote(
                symbol=symbol,
                name=asset["name"],
                asset_class=AssetClass(asset["asset_class"]),
                price=round(price, 4),
                updated_at=now,
            )

        price = series[-1][1]
        now_ms = series[-1][0]
        change_24h = pct_change(price, closest_price_before(series, now_ms - MS_PER_DAY))
        change_7d = pct_change(price, closest_price_before(series, now_ms - 7 * MS_PER_DAY))
        if change_7d is None and len(series) >= 2:
            change_7d = pct_change(price, series[0][1])

        return AssetQuote(
            symbol=symbol,
            name=asset["name"],
            asset_class=AssetClass(asset["asset_class"]),
            price=round(price, 4),
            change_pct_24h=change_24h,
            change_pct_7d=change_7d,
            updated_at=now,
        )
    except Exception as exc:
        logger.warning("Yahoo quote failed for %s: %s", symbol, exc)
        return None

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote as url_quote

import httpx

from app.config import settings
from app.data.assets import MONITORED_ASSETS
from app.data.investing_com import fetch_investing_quote, uses_investing
from app.models.schemas import AssetClass, AssetQuote

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

FETCH_SEMAPHORE = asyncio.Semaphore(12)
INVESTING_SEMAPHORE = asyncio.Semaphore(2)


async def fetch_bitcoin_ath() -> tuple:
    """Return (ath_date, ath_price, current_price) via CoinGecko."""
    from datetime import date

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


async def fetch_quotes_with_stats() -> tuple[list[AssetQuote], dict[str, dict]]:
    """Fetch quotes and 52-week price stats for all monitored assets."""
    now = datetime.now(timezone.utc)
    quotes: list[AssetQuote] = []
    price_stats: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
        tasks = [_fetch_asset(client, asset, now) for asset in MONITORED_ASSETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, tuple):
            asset_quote, stats = result
            if asset_quote:
                quotes.append(asset_quote)
                if stats:
                    price_stats[asset_quote.symbol] = stats
        elif isinstance(result, Exception):
            logger.warning("Asset fetch error: %s", result)

    return quotes, price_stats


async def fetch_quotes() -> list[AssetQuote]:
    quotes, _ = await fetch_quotes_with_stats()
    return quotes


async def _fetch_asset(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> tuple[Optional[AssetQuote], dict]:
    if uses_investing(asset["symbol"], asset.get("region")):
        async with INVESTING_SEMAPHORE:
            quote, stats = await fetch_investing_quote(asset, now)
            if quote:
                return quote, stats
            logger.warning("Investing.com fallback to Yahoo for %s", asset["symbol"])

    async with FETCH_SEMAPHORE:
        return await _fetch_yahoo_asset(client, asset, now)


async def _fetch_yahoo_asset(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> tuple[Optional[AssetQuote], dict]:
    symbol = asset["symbol"]
    encoded = url_quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    params = {"range": "1y", "interval": "1d"}
    stats: dict = {}

    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"]
        if not result:
            return None, stats

        meta = result[0]["meta"]
        highs = [h for h in result[0]["indicators"]["quote"][0].get("high", []) if h]
        lows = [l for l in result[0]["indicators"]["quote"][0].get("low", []) if l]
        closes = [c for c in result[0]["indicators"]["quote"][0]["close"] if c is not None]

        high_52w = float(meta.get("fiftyTwoWeekHigh") or (max(highs) if highs else 0)) or None
        low_52w = float(meta.get("fiftyTwoWeekLow") or (min(lows) if lows else 0)) or None

        if high_52w:
            stats = {"high_52w": high_52w, "low_52w": low_52w}

        if not closes:
            price = float(meta.get("regularMarketPrice", 0))
            if not price:
                return None, stats
            return AssetQuote(
                symbol=symbol,
                name=asset["name"],
                asset_class=AssetClass(asset["asset_class"]),
                price=round(price, 4),
                updated_at=now,
            ), stats

        price = float(closes[-1])
        change_24h = None
        change_7d = None
        if len(closes) >= 2:
            change_24h = round(((price - closes[-2]) / closes[-2]) * 100, 2)
        if len(closes) >= 6:
            change_7d = round(((price - closes[-6]) / closes[-6]) * 100, 2)
        elif len(closes) >= 2:
            change_7d = round(((price - closes[0]) / closes[0]) * 100, 2)

        asset_quote = AssetQuote(
            symbol=symbol,
            name=asset["name"],
            asset_class=AssetClass(asset["asset_class"]),
            price=round(price, 4),
            change_pct_24h=change_24h,
            change_pct_7d=change_7d,
            updated_at=now,
        )
        return asset_quote, stats

    except Exception as exc:
        logger.warning("Yahoo fetch failed for %s: %s", symbol, exc)
        return None, stats

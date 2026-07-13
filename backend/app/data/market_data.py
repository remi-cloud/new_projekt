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

        closes = [p[1] for p in prices]
        price = float(closes[-1])
        change_24h = None
        change_7d = None
        if len(closes) >= 2:
            change_24h = round(((price - closes[-2]) / closes[-2]) * 100, 2)
        if len(closes) >= 2:
            change_7d = round(((price - closes[0]) / closes[0]) * 100, 2)

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
    params = {"range": "5d", "interval": "1d"}
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"]
        if not result:
            return None

        meta = result[0]["meta"]
        closes = [
            c for c in result[0]["indicators"]["quote"][0]["close"] if c is not None
        ]
        if not closes:
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

        price = float(closes[-1])
        change_24h = None
        change_7d = None
        if len(closes) >= 2:
            change_24h = round(((price - closes[-2]) / closes[-2]) * 100, 2)
        if len(closes) >= 2:
            change_7d = round(((price - closes[0]) / closes[0]) * 100, 2)

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


async def fetch_coingecko_price(coin_id: str = "bitcoin") -> Optional[float]:
    url = f"{settings.coingecko_base_url}/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return float(resp.json()[coin_id]["usd"])
    except Exception as exc:
        logger.warning("CoinGecko fetch failed: %s", exc)
        return None

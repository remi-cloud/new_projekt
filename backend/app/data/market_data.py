import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.data.assets import DEFAULT_ASSETS, REGION_LABELS, resolve_region
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


async def fetch_quotes(assets: list[dict] | None = None) -> list[AssetQuote]:
    now = datetime.now(timezone.utc)
    quotes: list[AssetQuote] = []
    universe = assets if assets is not None else DEFAULT_ASSETS

    async with httpx.AsyncClient(timeout=20, headers=YAHOO_HEADERS) as client:
        tasks = [_fetch_single_quote(client, asset, now) for asset in universe]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    got: set[str] = set()
    for result in results:
        if isinstance(result, AssetQuote):
            quotes.append(result)
            got.add(result.symbol.upper())
        elif isinstance(result, Exception):
            logger.warning("Quote fetch error: %s", result)

    # TradingView fallback for anything Yahoo blocked / empty ("brak dostępu")
    missing = [a for a in universe if a["symbol"].upper() not in got]
    if missing:
        try:
            from app.data.tradingview import fetch_tradingview_quotes

            async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
                tv_map = await fetch_tradingview_quotes(
                    client, [a["symbol"] for a in missing]
                )
            by_asset = {a["symbol"].upper(): a for a in missing}
            for sym_u, row in tv_map.items():
                asset = by_asset.get(sym_u)
                if not asset:
                    continue
                quotes.append(
                    _quote_from_asset(
                        asset,
                        price=float(row["close"]),
                        now=now,
                        change_24h=row.get("change_pct"),
                        change_7d=None,
                        live=True,
                        quote_source="tradingview",
                    )
                )
                got.add(sym_u)
            logger.info(
                "TradingView filled %d / %d missing quotes",
                len(tv_map),
                len(missing),
            )
        except Exception as exc:
            logger.warning("TradingView fallback failed: %s", exc)

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

        region = resolve_region(asset)
        return AssetQuote(
            symbol=asset["symbol"],
            name=asset["name"],
            asset_class=AssetClass(asset["asset_class"]),
            price=round(price, 4),
            change_pct_24h=change_24h,
            change_pct_7d=change_7d,
            updated_at=now,
            region=region,
            region_label=REGION_LABELS.get(region, region),
            live=True,
            quote_source="coingecko",
        )
    except Exception as exc:
        logger.warning("CoinGecko quote failed for %s: %s", asset["symbol"], exc)
        return None


def _quote_from_asset(
    asset: dict,
    *,
    price: float,
    now: datetime,
    change_24h: float | None = None,
    change_7d: float | None = None,
    live: bool = True,
    quote_source: str = "yahoo",
) -> AssetQuote:
    region = resolve_region(asset)
    return AssetQuote(
        symbol=asset["symbol"],
        name=asset["name"],
        asset_class=AssetClass(asset["asset_class"]),
        price=round(price, 4) if price else 0.0,
        change_pct_24h=change_24h,
        change_pct_7d=change_7d,
        updated_at=now,
        region=region,
        region_label=REGION_LABELS.get(region, region),
        live=live,
        quote_source=quote_source,
    )


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

        meta = result[0].get("meta") or {}
        timestamps = result[0].get("timestamp") or []
        indicators = result[0].get("indicators") or {}
        quote_rows = indicators.get("quote") or [{}]
        closes_raw = (quote_rows[0] or {}).get("close") or []
        series = [
            (int(ts) * 1000, float(close))
            for ts, close in zip(timestamps, closes_raw)
            if close is not None
        ]

        if not series:
            # MOEX / some EM tickers often return price in meta with null closes.
            price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
            if not price:
                return None
            return _quote_from_asset(asset, price=price, now=now, live=True)

        price = series[-1][1]
        now_ms = series[-1][0]
        change_24h = pct_change(price, closest_price_before(series, now_ms - MS_PER_DAY))
        change_7d = pct_change(price, closest_price_before(series, now_ms - 7 * MS_PER_DAY))
        if change_7d is None and len(series) >= 2:
            change_7d = pct_change(price, series[0][1])

        return _quote_from_asset(
            asset,
            price=price,
            now=now,
            change_24h=change_24h,
            change_7d=change_7d,
            live=True,
        )
    except Exception as exc:
        logger.warning("Yahoo quote failed for %s: %s", symbol, exc)
        return None


def stub_quote(asset: dict, now: datetime | None = None) -> AssetQuote:
    """Catalog stub so Markets always lists the instrument even without a live quote."""
    return _quote_from_asset(
        asset,
        price=0.0,
        now=now or datetime.now(timezone.utc),
        live=False,
        quote_source="stub",
    )


async def build_markets_quotes(
    assets: list[dict],
    cached: list[AssetQuote] | None = None,
    *,
    fetch_missing: bool = True,
    max_cache_age_seconds: int = 120,
) -> list[AssetQuote]:
    """Merge catalog with live quotes; refetch stale cache; stubs for gaps."""
    now = datetime.now(timezone.utc)
    by_sym: dict[str, AssetQuote] = {}
    for q in cached or []:
        updated = q.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = (now - updated).total_seconds()
        if q.live and q.price > 0 and age <= max_cache_age_seconds:
            by_sym[q.symbol.upper()] = q

    missing = [a for a in assets if a["symbol"].upper() not in by_sym]
    if fetch_missing and missing:
        fresh = await fetch_quotes(missing)
        for q in fresh:
            by_sym[q.symbol.upper()] = q

    out: list[AssetQuote] = []
    for asset in assets:
        sym = asset["symbol"].upper()
        quote = by_sym.get(sym)
        if quote is None:
            out.append(stub_quote(asset, now))
            continue
        if not quote.region:
            region = resolve_region(asset)
            quote = quote.model_copy(
                update={
                    "region": region,
                    "region_label": REGION_LABELS.get(region, region),
                }
            )
        out.append(quote)
    return out

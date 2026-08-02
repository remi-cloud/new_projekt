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
    """
    Live quote pipeline (100% coverage target):
      1) TradingView scanner (batch, primary live tape)
      2) Yahoo 1m chart for anything TV missed
      3) CoinGecko for crypto if still missing
    """
    now = datetime.now(timezone.utc)
    universe = assets if assets is not None else DEFAULT_ASSETS
    by_asset = {a["symbol"].upper(): a for a in universe}
    quotes_by: dict[str, AssetQuote] = {}

    # ── 1. TradingView first (true multi-exchange live) ─────────────────
    try:
        from app.data.tradingview import fetch_tradingview_quotes

        async with httpx.AsyncClient(timeout=25, headers=YAHOO_HEADERS) as client:
            tv_map = await fetch_tradingview_quotes(
                client, [a["symbol"] for a in universe]
            )
        for sym_u, row in tv_map.items():
            asset = by_asset.get(sym_u)
            if not asset:
                continue
            quotes_by[sym_u] = _quote_from_asset(
                asset,
                price=float(row["close"]),
                now=now,
                change_24h=row.get("change_pct"),
                change_7d=None,
                live=True,
                quote_source="tradingview",
            )
        logger.info("TradingView live: %d / %d", len(tv_map), len(universe))
    except Exception as exc:
        logger.warning("TradingView primary failed: %s", exc)

    # ── 2. Yahoo / CoinGecko for gaps ───────────────────────────────────
    missing = [a for a in universe if a["symbol"].upper() not in quotes_by]
    if missing:
        async with httpx.AsyncClient(timeout=20, headers=YAHOO_HEADERS) as client:
            tasks = [_fetch_single_quote(client, asset, now) for asset in missing]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        filled = 0
        for result in results:
            if isinstance(result, AssetQuote):
                quotes_by[result.symbol.upper()] = result
                filled += 1
            elif isinstance(result, Exception):
                logger.warning("Gap quote error: %s", result)
        logger.info("Yahoo/CG filled gaps: %d / %d", filled, len(missing))

    return list(quotes_by.values())


async def probe_market_providers() -> dict:
    """Return live connectivity status for each market data provider."""
    status: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}
    async with httpx.AsyncClient(timeout=15, headers=YAHOO_HEADERS) as client:
        # TradingView
        try:
            from app.data.tradingview import probe_tradingview

            tv = await probe_tradingview(client)
            status["tradingview"] = tv
        except Exception as exc:
            status["tradingview"] = {"ok": False, "error": str(exc)}

        # Yahoo
        try:
            resp = await client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
                params={"range": "1d", "interval": "1m"},
            )
            ok = resp.status_code == 200
            price = None
            if ok:
                result = resp.json().get("chart", {}).get("result") or []
                if result:
                    price = (result[0].get("meta") or {}).get("regularMarketPrice")
            status["yahoo"] = {"ok": bool(ok and price), "sample_price": price}
        except Exception as exc:
            status["yahoo"] = {"ok": False, "error": str(exc)}

        # CoinGecko
        try:
            resp = await client.get(
                f"{settings.coingecko_base_url}/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
            )
            data = resp.json() if resp.status_code == 200 else {}
            btc = (data.get("bitcoin") or {}).get("usd")
            status["coingecko"] = {"ok": bool(btc), "sample_price": btc}
        except Exception as exc:
            status["coingecko"] = {"ok": False, "error": str(exc)}

    status["connected"] = any(
        (status.get(k) or {}).get("ok") for k in ("tradingview", "yahoo", "coingecko")
    )
    return status


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


async def _yahoo_chart_result(
    client: httpx.AsyncClient, symbol: str, *, range_: str, interval: str
) -> dict | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    resp = await client.get(url, params={"range": range_, "interval": interval})
    resp.raise_for_status()
    result = resp.json().get("chart", {}).get("result") or []
    return result[0] if result else None


async def _fetch_yahoo_quote(
    client: httpx.AsyncClient, asset: dict, now: datetime
) -> Optional[AssetQuote]:
    """Prefer 1m intraday last for live tape; fall back to daily bars."""
    symbol = asset["symbol"]
    try:
        chart = await _yahoo_chart_result(client, symbol, range_="1d", interval="1m")
        if chart is None:
            chart = await _yahoo_chart_result(client, symbol, range_="5d", interval="1d")
        if chart is None:
            return None

        meta = chart.get("meta") or {}
        timestamps = chart.get("timestamp") or []
        indicators = chart.get("indicators") or {}
        quote_rows = indicators.get("quote") or [{}]
        closes_raw = (quote_rows[0] or {}).get("close") or []
        series = [
            (int(ts) * 1000, float(close))
            for ts, close in zip(timestamps, closes_raw)
            if close is not None
        ]

        # Prefer meta last when present (true live) over last bar close
        meta_price = float(meta.get("regularMarketPrice") or 0) or None

        if not series:
            price = meta_price or float(meta.get("previousClose") or 0)
            if not price:
                return None
            return _quote_from_asset(
                asset, price=price, now=now, live=True, quote_source="yahoo"
            )

        price = meta_price or series[-1][1]
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
            quote_source="yahoo",
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

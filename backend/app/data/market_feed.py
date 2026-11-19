"""Free quotes and candles for the whole board, with a source named on every miss.

Yahoo is tried by the chart and quote callers first. This module is the next
step: Binance, CoinGecko and CoinCap for crypto; Stooq for equities, indices,
FX and commodities; FRED's key-free CSV for the Fed funds rate, CPI and the
US 10-year. Results are cached. API keys are not used and not logged.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.data.assets import MONITORED_ASSETS
from app.models.schemas import ChartCandle

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CyklicznyTrader/1.0)", "Accept": "application/json,text/csv"}
_CANDLE_TTL = 180.0
_OVERVIEW_TTL = 90.0
_CACHE: dict[str, tuple[float, Any]] = {}
_LAST_ERRORS: dict[str, list[str]] = {}

# coingecko id, coincap id, binance pair
CRYPTO: dict[str, tuple[str, str, str]] = {
    "BTC-USD": ("bitcoin", "bitcoin", "BTCUSDT"),
    "ETH-USD": ("ethereum", "ethereum", "ETHUSDT"),
    "SOL-USD": ("solana", "solana", "SOLUSDT"),
    "XRP-USD": ("ripple", "xrp", "XRPUSDT"),
    "BNB-USD": ("binancecoin", "binance-coin", "BNBUSDT"),
    "DOGE-USD": ("dogecoin", "dogecoin", "DOGEUSDT"),
    "ADA-USD": ("cardano", "cardano", "ADAUSDT"),
    "AVAX-USD": ("avalanche-2", "avalanche", "AVAXUSDT"),
    "LINK-USD": ("chainlink", "chainlink", "LINKUSDT"),
    "DOT-USD": ("polkadot", "polkadot", "DOTUSDT"),
    "LTC-USD": ("litecoin", "litecoin", "LTCUSDT"),
    "TON-USD": ("the-open-network", "toncoin", "TONUSDT"),
    "TRX-USD": ("tron", "tron", "TRXUSDT"),
    "BCH-USD": ("bitcoin-cash", "bitcoin-cash", "BCHUSDT"),
    "UNI-USD": ("uniswap", "uniswap", "UNIUSDT"),
    "ATOM-USD": ("cosmos", "cosmos", "ATOMUSDT"),
    "NEAR-USD": ("near", "near-protocol", "NEARUSDT"),
    "APT-USD": ("aptos", "aptos", "APTUSDT"),
    "SUI-USD": ("sui", "sui", "SUIUSDT"),
}

# app symbol, stooq symbol, display name
TRADITIONAL: tuple[tuple[str, str, str], ...] = (
    ("^GSPC", "^spx", "S&P 500"),
    ("^DJI", "^dji", "Dow Jones"),
    ("^IXIC", "^ndq", "Nasdaq"),
    ("^NDX", "^ndx", "Nasdaq 100"),
    ("^GDAXI", "^dax", "DAX"),
    ("WIG20.WA", "wig20", "WIG20"),
    ("^N225", "^nkx", "Nikkei 225"),
    ("AAPL", "aapl.us", "Apple"),
    ("TSLA", "tsla.us", "Tesla"),
    ("NVDA", "nvda.us", "NVIDIA"),
    ("GC=F", "gc.f", "Gold"),
    ("SI=F", "si.f", "Silver"),
    ("CL=F", "cl.f", "WTI"),
    ("EURUSD=X", "eurusd", "EUR/USD"),
    ("USDPLN=X", "usdpln", "USD/PLN"),
    ("DX-Y.NYB", "dx.f", "DXY"),
    ("^TNX", "10yus.b", "US 10Y"),
)

FRED_SERIES = (
    ("FEDFUNDS", "Fed funds rate"),
    ("CPIAUCSL", "US CPI"),
    ("DGS10", "US 10Y yield"),
)

EXTRA_ALIASES = {
    "xrp": "XRP-USD",
    "ripple": "XRP-USD",
    "bnb": "BNB-USD",
    "doge": "DOGE-USD",
    "dogecoin": "DOGE-USD",
    "ada": "ADA-USD",
    "cardano": "ADA-USD",
    "avax": "AVAX-USD",
    "silver": "SI=F",
    "srebro": "SI=F",
    "złoto": "GC=F",
    "zloto": "GC=F",
    "wti": "CL=F",
    "ropa": "CL=F",
    "eurusd": "EURUSD=X",
    "usdpln": "USDPLN=X",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "us10": "^TNX",
    "tnx": "^TNX",
    "nikkei": "^N225",
    "dow": "^DJI",
    "spx": "^GSPC",
    "s&p500": "^GSPC",
    "nasdaq": "^IXIC",
}

PRIORITY_SYMBOLS = frozenset([*CRYPTO.keys(), *[row[0] for row in TRADITIONAL]])
_STOOQ = {symbol: stooq for symbol, stooq, _name in TRADITIONAL}
_NAMES = {symbol: name for symbol, _stooq, name in TRADITIONAL}
_NAMES.update({symbol: symbol for symbol in CRYPTO})


def clear_feed_cache() -> None:
    _CACHE.clear()
    _LAST_ERRORS.clear()


def chart_source_errors(symbol: str) -> list[str]:
    return list(_LAST_ERRORS.get(symbol.upper(), []))


def _remember(symbol: str, errors: list[str]) -> None:
    _LAST_ERRORS[symbol.upper()] = errors[-8:]


def _cache_get(key: str) -> Any | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time.monotonic() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: float) -> None:
    _CACHE[key] = (time.monotonic() + ttl, value)


def _fail(source: str, reason: str) -> str:
    text = f"{source}: {reason}".replace("\n", " ")
    return text[:180]


def _daily_limit(preset: str) -> int:
    return {
        "1D": 5,
        "1W": 12,
        "1M": 32,
        "3M": 120,
        "1Y": 370,
        "MAX": 1000,
        "10Y": 1000,
    }.get(preset, 120)


def _cg_days(preset: str) -> int:
    need = _daily_limit(preset)
    for allowed in (1, 7, 14, 30, 90, 180, 365):
        if allowed >= min(need, 365):
            return allowed
    return 365


def is_crypto(symbol: str) -> bool:
    upper = symbol.upper()
    return upper in CRYPTO or (upper.endswith("-USD") and "=" not in upper and not upper.startswith("^"))


def binance_pair(symbol: str) -> str | None:
    upper = symbol.upper()
    mapped = CRYPTO.get(upper)
    if mapped:
        return mapped[2]
    if upper.endswith("-USD"):
        base = upper[: -len("-USD")]
        if base.isascii() and base.isalnum() and 2 <= len(base) <= 12:
            return f"{base}USDT"
    return None


def stooq_symbol(symbol: str) -> str | None:
    upper = symbol.upper()
    if upper in _STOOQ:
        return _STOOQ[upper]
    if upper.endswith(".WA"):
        return upper.split(".", 1)[0].lower()
    if upper.isascii() and upper.isalpha() and 1 <= len(upper) <= 5:
        return f"{upper.lower()}.us"
    return None


def search_symbols(query: str, limit: int = 12) -> list[dict[str, str]]:
    """Match a typed name or ticker against the catalog and the feed aliases."""
    raw = (query or "").strip()
    if not raw:
        return []
    q = raw.lower()
    hits: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(symbol: str, name: str, why: str) -> None:
        key = symbol.upper()
        if key in seen:
            return
        seen.add(key)
        hits.append({"symbol": key, "name": name, "match": why})

    alias = EXTRA_ALIASES.get(q)
    if alias:
        add(alias, _NAMES.get(alias, alias), "alias")
    for asset in MONITORED_ASSETS:
        symbol = str(asset["symbol"])
        name = str(asset.get("name") or symbol)
        if q == symbol.lower() or q == name.lower():
            add(symbol, name, "exact")
        elif q in symbol.lower() or q in name.lower():
            add(symbol, name, "partial")
        if len(hits) >= limit:
            break
    return hits[:limit]


def _candle(ts: int, open_: float, high: float, low: float, close: float, volume: float | None = None) -> ChartCandle:
    return ChartCandle(time=int(ts), open=open_, high=high, low=low, close=close, volume=volume)


def _from_ohlc_rows(rows: list, ms: bool = True) -> list[ChartCandle]:
    candles: list[ChartCandle] = []
    for row in rows:
        try:
            ts = int(row[0])
            if ms:
                ts //= 1000
            o, h, low, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        except (TypeError, ValueError, IndexError):
            continue
        vol = None
        if len(row) > 5 and row[5] not in (None, ""):
            try:
                vol = float(row[5])
            except (TypeError, ValueError):
                vol = None
        candles.append(_candle(ts, o, h, low, c, vol))
    return candles


async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None) -> httpx.Response:
    return await client.get(url, params=params, headers=HEADERS)


async def _binance_candles(client: httpx.AsyncClient, symbol: str, preset: str) -> tuple[list[ChartCandle], str | None]:
    pair = binance_pair(symbol)
    if not pair:
        return [], _fail("binance", "no pair")
    if preset in {"1m", "5m", "15m", "30m", "1H", "4H"}:
        interval, limit = "1h", 240
    else:
        interval, limit = "1d", min(1000, _daily_limit(preset))
    try:
        resp = await _get(
            client,
            "https://api.binance.com/api/v3/klines",
            {"symbol": pair, "interval": interval, "limit": limit},
        )
    except httpx.HTTPError as exc:
        return [], _fail("binance", type(exc).__name__)
    if resp.status_code >= 400:
        return [], _fail("binance", f"HTTP {resp.status_code}")
    try:
        rows = resp.json()
    except ValueError:
        return [], _fail("binance", "bad JSON")
    if not isinstance(rows, list) or not rows:
        return [], _fail("binance", "empty")
    candles = _from_ohlc_rows(rows, ms=True)
    if not candles:
        return [], _fail("binance", "no rows")
    return candles, None


async def _coingecko_candles(client: httpx.AsyncClient, symbol: str, preset: str) -> tuple[list[ChartCandle], str | None]:
    mapped = CRYPTO.get(symbol.upper())
    if not mapped:
        return [], _fail("coingecko", "no id")
    try:
        resp = await _get(
            client,
            f"https://api.coingecko.com/api/v3/coins/{mapped[0]}/ohlc",
            {"vs_currency": "usd", "days": _cg_days(preset)},
        )
    except httpx.HTTPError as exc:
        return [], _fail("coingecko", type(exc).__name__)
    if resp.status_code >= 400:
        return [], _fail("coingecko", f"HTTP {resp.status_code}")
    try:
        rows = resp.json()
    except ValueError:
        return [], _fail("coingecko", "bad JSON")
    candles = _from_ohlc_rows(rows if isinstance(rows, list) else [], ms=True)
    if not candles:
        return [], _fail("coingecko", "empty")
    return candles, None


async def _coincap_candles(client: httpx.AsyncClient, symbol: str, preset: str) -> tuple[list[ChartCandle], str | None]:
    mapped = CRYPTO.get(symbol.upper())
    asset = mapped[1] if mapped else ""
    if not asset and symbol.upper().endswith("-USD"):
        asset = symbol.split("-", 1)[0].lower()
    if not asset:
        return [], _fail("coincap", "no id")
    try:
        resp = await _get(
            client,
            f"https://api.coincap.io/v2/assets/{asset}/history",
            {"interval": "d1"},
        )
    except httpx.HTTPError as exc:
        return [], _fail("coincap", type(exc).__name__)
    if resp.status_code >= 400:
        return [], _fail("coincap", f"HTTP {resp.status_code}")
    try:
        payload = resp.json()
    except ValueError:
        return [], _fail("coincap", "bad JSON")
    points = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(points, list) or not points:
        return [], _fail("coincap", "empty")
    candles: list[ChartCandle] = []
    prev: float | None = None
    for point in points:
        try:
            price = float(point["priceUsd"])
            ts = int(point.get("time") or 0)
            if ts > 10_000_000_000:
                ts //= 1000
        except (TypeError, ValueError, KeyError):
            continue
        open_ = prev if prev is not None else price
        candles.append(_candle(ts, open_, max(open_, price), min(open_, price), price))
        prev = price
    candles = candles[-_daily_limit(preset) :]
    if not candles:
        return [], _fail("coincap", "no rows")
    return candles, None


def _parse_date(value: str) -> int | None:
    text = value.strip()
    try:
        if "-" in text:
            year, month, day = (int(part) for part in text.split("-")[:3])
        elif len(text) >= 8 and text[:8].isdigit():
            year, month, day = int(text[:4]), int(text[4:6]), int(text[6:8])
        else:
            return None
        return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


def parse_stooq_daily(text: str, limit: int) -> list[ChartCandle]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines or "brak danych" in lines[0].lower() or lines[0].lower().startswith("no data"):
        return []
    start = 1 if any(token in lines[0].lower() for token in ("date", "data", "symbol")) else 0
    candles: list[ChartCandle] = []
    for line in lines[start:]:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue
        # Daily history is Date,Open,High,Low,Close[,Volume]. A quote line leads with the symbol.
        offset = 0
        ts = _parse_date(parts[0])
        if ts is None and len(parts) >= 6:
            offset = 1
            ts = _parse_date(parts[1])
        if ts is None or len(parts) < offset + 5:
            continue
        try:
            open_, high, low, close = (float(parts[offset + i]) for i in range(1, 5))
        except ValueError:
            continue
        volume = None
        if len(parts) > offset + 5 and parts[offset + 5] not in {"", "0"}:
            try:
                volume = float(parts[offset + 5])
            except ValueError:
                volume = None
        candles.append(_candle(ts, open_, high, low, close, volume))
    return candles[-limit:]


async def _stooq_candles(client: httpx.AsyncClient, symbol: str, preset: str) -> tuple[list[ChartCandle], str | None]:
    stooq = stooq_symbol(symbol)
    if not stooq:
        return [], _fail("stooq", "no symbol")
    errors: list[str] = []
    for host in ("stooq.com", "stooq.pl"):
        try:
            resp = await _get(client, f"https://{host}/q/d/", {"s": stooq, "i": "d"})
        except httpx.HTTPError as exc:
            errors.append(_fail(host, type(exc).__name__))
            continue
        if resp.status_code >= 400:
            errors.append(_fail(host, f"HTTP {resp.status_code}"))
            continue
        candles = parse_stooq_daily(resp.text, _daily_limit(preset))
        if candles:
            return candles, None
        errors.append(_fail(host, "empty"))
    return [], errors[-1] if errors else _fail("stooq", "empty")


async def _fred_candles(client: httpx.AsyncClient, series: str) -> tuple[list[ChartCandle], str | None]:
    try:
        resp = await _get(client, "https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series})
    except httpx.HTTPError as exc:
        return [], _fail("fred", type(exc).__name__)
    if resp.status_code >= 400:
        return [], _fail("fred", f"HTTP {resp.status_code}")
    candles: list[ChartCandle] = []
    for line in resp.text.splitlines()[1:]:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2 or parts[1] in {"", "."}:
            continue
        ts = _parse_date(parts[0])
        try:
            value = float(parts[1])
        except ValueError:
            continue
        if ts is None:
            continue
        candles.append(_candle(ts, value, value, value, value))
    if not candles:
        return [], _fail("fred", f"{series} empty")
    return candles, None


async def load_fallback_candles(
    symbol: str,
    preset: str = "3M",
    client: httpx.AsyncClient | None = None,
) -> tuple[list[ChartCandle], str, list[str]]:
    """Candles after Yahoo missed. `(candles, source, errors)`."""
    key = f"c:{symbol.upper()}:{preset}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    async def _run(http: httpx.AsyncClient) -> tuple[list[ChartCandle], str, list[str]]:
        errors: list[str] = []
        if is_crypto(symbol):
            steps = (
                ("binance", lambda: _binance_candles(http, symbol, preset)),
                ("coingecko", lambda: _coingecko_candles(http, symbol, preset)),
                ("coincap", lambda: _coincap_candles(http, symbol, preset)),
            )
        else:
            steps = (("stooq", lambda: _stooq_candles(http, symbol, preset)),)
            if symbol.upper() == "^TNX":
                steps = (*steps, ("fred", lambda: _fred_candles(http, "DGS10")))
        for source, factory in steps:
            candles, error = await factory()
            if error:
                errors.append(error)
            if candles:
                _remember(symbol, errors)
                packed = (candles, source, errors)
                _cache_set(key, packed, _CANDLE_TTL)
                return packed
        _remember(symbol, errors)
        return [], "", errors

    if client is not None:
        return await _run(client)
    async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as owned:
        return await _run(owned)


def _quote_from_candles(candles: list[ChartCandle], source: str, errors: list[str]) -> dict[str, Any]:
    last = candles[-1]
    prev = candles[-2].close if len(candles) > 1 else last.open
    week = candles[-6].close if len(candles) > 5 else candles[0].close
    change = round((last.close - prev) / prev * 100, 2) if prev else None
    change_7d = round((last.close - week) / week * 100, 2) if week else None
    return {
        "price": last.close,
        "change_pct_24h": change,
        "change_pct_7d": change_7d,
        "closes": [c.close for c in candles],
        "source": source,
        "errors": errors,
    }


async def quote_one(symbol: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as client:
        return await supplement_quote(client, symbol)


async def supplement_quote(client: httpx.AsyncClient, symbol: str) -> dict[str, Any] | None:
    """Daily history for one symbol after Yahoo missed. Callers decide who is worth the request."""
    cached = _cache_get(f"q:{symbol.upper()}")
    if cached is not None:
        return cached
    candles, source, errors = await load_fallback_candles(symbol, "1Y", client)
    if not candles:
        return {"price": None, "source": None, "errors": errors, "closes": []}
    quote = _quote_from_candles(candles, source, errors)
    _cache_set(f"q:{symbol.upper()}", quote, _CANDLE_TTL)
    return quote


async def _crypto_board(client: httpx.AsyncClient) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    ids = ",".join(row[0] for row in CRYPTO.values())
    board: dict[str, Any] = {"coins": [], "total_market_cap_usd": None, "btc_dominance_pct": None}
    try:
        global_resp = await _get(client, "https://api.coingecko.com/api/v3/global")
        if global_resp.status_code >= 400:
            errors.append(_fail("coingecko", f"global HTTP {global_resp.status_code}"))
        else:
            data = (global_resp.json() or {}).get("data") or {}
            caps = data.get("total_market_cap") or {}
            share = data.get("market_cap_percentage") or {}
            board["total_market_cap_usd"] = caps.get("usd")
            board["btc_dominance_pct"] = share.get("btc")
            board["market_cap_change_24h_pct"] = data.get("market_cap_change_percentage_24h_usd")
    except (httpx.HTTPError, ValueError) as exc:
        errors.append(_fail("coingecko", f"global {type(exc).__name__}"))
    try:
        markets = await _get(
            client,
            "https://api.coingecko.com/api/v3/coins/markets",
            {
                "vs_currency": "usd",
                "ids": ids,
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1,
                "price_change_percentage": "24h",
            },
        )
        if markets.status_code >= 400:
            errors.append(_fail("coingecko", f"markets HTTP {markets.status_code}"))
        else:
            rows = markets.json()
            if isinstance(rows, list):
                by_id = {spec[0]: symbol for symbol, spec in CRYPTO.items()}
                for row in rows:
                    symbol = by_id.get(str(row.get("id")))
                    if not symbol:
                        continue
                    board["coins"].append(
                        {
                            "symbol": symbol,
                            "name": row.get("name"),
                            "price": row.get("current_price"),
                            "change_pct_24h": row.get("price_change_percentage_24h"),
                            "market_cap": row.get("market_cap"),
                            "source": "coingecko",
                        }
                    )
    except (httpx.HTTPError, ValueError) as exc:
        errors.append(_fail("coingecko", f"markets {type(exc).__name__}"))
    if board["coins"]:
        return board, errors
    # CoinGecko missed. Binance last price for the same majors.
    for symbol, spec in CRYPTO.items():
        try:
            resp = await _get(client, "https://api.binance.com/api/v3/ticker/24hr", {"symbol": spec[2]})
        except httpx.HTTPError as exc:
            errors.append(_fail("binance", f"{spec[2]} {type(exc).__name__}"))
            continue
        if resp.status_code >= 400:
            errors.append(_fail("binance", f"{spec[2]} HTTP {resp.status_code}"))
            continue
        try:
            row = resp.json()
            board["coins"].append(
                {
                    "symbol": symbol,
                    "name": symbol,
                    "price": float(row["lastPrice"]),
                    "change_pct_24h": float(row.get("priceChangePercent") or 0),
                    "market_cap": None,
                    "source": "binance",
                }
            )
        except (TypeError, ValueError, KeyError):
            errors.append(_fail("binance", f"{spec[2]} bad JSON"))
    return board, errors


def _parse_stooq_quotes(text: str) -> dict[str, float]:
    prices: dict[str, float] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return prices
    start = 1 if "symbol" in lines[0].lower() or "data" in lines[0].lower() else 0
    for line in lines[start:]:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            close = float(parts[6])
        except ValueError:
            continue
        prices[parts[0].lower()] = close
    return prices


async def _traditional_board(client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    symbols = "+".join(stooq for _app, stooq, _name in TRADITIONAL)
    prices: dict[str, float] = {}
    try:
        resp = await _get(
            client,
            "https://stooq.com/q/l/",
            {"s": symbols, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
        )
        if resp.status_code >= 400:
            errors.append(_fail("stooq", f"HTTP {resp.status_code}"))
        else:
            prices = _parse_stooq_quotes(resp.text)
            if not prices:
                errors.append(_fail("stooq", "empty quote"))
    except httpx.HTTPError as exc:
        errors.append(_fail("stooq", type(exc).__name__))
    rows: list[dict[str, Any]] = []
    for symbol, stooq, name in TRADITIONAL:
        price = prices.get(stooq.lower())
        if price is None:
            candles, source, nested = await load_fallback_candles(symbol, "1M", client)
            if candles:
                rows.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "price": candles[-1].close,
                        "source": source,
                    }
                )
                continue
            errors.extend(nested)
            rows.append({"symbol": symbol, "name": name, "price": None, "source": None, "error": nested[-1] if nested else _fail("stooq", "missing")})
            continue
        rows.append({"symbol": symbol, "name": name, "price": price, "source": "stooq"})
    return rows, errors


async def _macro_board(client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for series, name in FRED_SERIES:
        candles, error = await _fred_candles(client, series)
        if error or not candles:
            errors.append(error or _fail("fred", f"{series} empty"))
            rows.append({"series": series, "name": name, "value": None, "source": None, "error": error})
            continue
        latest = candles[-1].close
        yoy = None
        if series == "CPIAUCSL" and len(candles) > 12 and candles[-13].close:
            yoy = round((latest / candles[-13].close - 1) * 100, 2)
        as_of = datetime.fromtimestamp(candles[-1].time, tz=timezone.utc).date().isoformat()
        rows.append(
            {
                "series": series,
                "name": name,
                "value": latest,
                "as_of": as_of,
                "yoy_pct": yoy,
                "source": "fred",
            }
        )
    return rows, errors


async def market_overview() -> dict[str, Any]:
    """Whole-board snapshot: crypto cap and dominance, indices, stocks, FX, commodities, macro."""
    cached = _cache_get("overview")
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as client:
        crypto, crypto_errors = await _crypto_board(client)
        traditional, trad_errors = await _traditional_board(client)
        macro, macro_errors = await _macro_board(client)
    payload = {
        "as_of": date.today().isoformat(),
        "crypto": crypto,
        "traditional": traditional,
        "macro": macro,
        "source_errors": [*crypto_errors, *trad_errors, *macro_errors],
        "how_to_use": (
            "Prices come from the named source. A null price means that source failed; "
            "read source_errors. Do not invent a number that is missing here."
        ),
    }
    _cache_set("overview", payload, _OVERVIEW_TTL)
    logger.info(
        "Market overview: %d coins, %d traditional, %d macro, %d source errors",
        len(crypto.get("coins") or []),
        len(traditional),
        len(macro),
        len(payload["source_errors"]),
    )
    return payload

"""TradingView scanner — primary live quotes (+ Yahoo fallback in market_data)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TV_SCAN_URL = "https://scanner.tradingview.com/global/scan"
TV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Yahoo / catalog symbol → TradingView `EXCHANGE:SYMBOL` (verified live)
TV_SYMBOL_MAP: dict[str, str] = {
    # Crypto
    "BTC-USD": "BITSTAMP:BTCUSD",
    "ETH-USD": "BITSTAMP:ETHUSD",
    "SOL-USD": "BINANCE:SOLUSDT",
    # US indexes / ETFs
    "^GSPC": "SP:SPX",
    "^DJI": "TVC:DJI",
    "^IXIC": "NASDAQ:IXIC",
    "^RUT": "TVC:RUT",
    "SPY": "AMEX:SPY",
    "QQQ": "NASDAQ:QQQ",
    "IWM": "AMEX:IWM",
    "DIA": "AMEX:DIA",
    # Americas
    "^GSPTSE": "TSX:TSX",
    "^BVSP": "BMFBOVESPA:IBOV",
    "^MXX": "BMV:ME",
    "^IPSA": "BCS:IPSA",
    "EWZ": "AMEX:EWZ",
    "EWC": "AMEX:EWC",
    "EWW": "AMEX:EWW",
    # Europe
    "^FTSE": "TVC:UKX",
    "^GDAXI": "XETR:DAX",
    "^FCHI": "TVC:CAC40",
    "^STOXX50E": "TVC:SX5E",
    "^IBEX": "BME:IB",
    "^AEX": "TVC:AEX",
    "^SSMI": "SIX:SMI",
    "^OMXSPI": "OMXSTO:OMXSPI",
    "WIG20.WA": "GPW:WIG20",
    "EWG": "AMEX:EWG",
    "EWU": "AMEX:EWU",
    "EZU": "AMEX:EZU",
    # Russia
    "IMOEX.ME": "RUS:IMOEX",
    "RTSI.ME": "RUS:RTSI",
    "ERUS": "AMEX:ERUS",
    "RSX": "AMEX:RSX",
    "SBER.ME": "RUS:SBER",
    "GAZP.ME": "RUS:GAZP",
    # Asia
    "^N225": "TVC:NI225",
    "^HSI": "TVC:HSI",
    "000001.SS": "SSE:000001",
    "399001.SZ": "SZSE:399001",
    "^KS11": "TVC:KOSPI",
    "^TWII": "TVC:TWII",
    "^BSESN": "BSE:SENSEX",
    "^NSEI": "NSE:NIFTY",
    "^STI": "TVC:STI",
    "^JKSE": "IDX:COMPOSITE",
    "^KLSE": "MYX:FBMKLCI",
    "^AXJO": "ASX:XJO",
    "^NZ50": "NZX:NZ50",
    "EWJ": "AMEX:EWJ",
    "FXI": "AMEX:FXI",
    "MCHI": "NASDAQ:MCHI",
    "EWY": "AMEX:EWY",
    "EWT": "AMEX:EWT",
    "INDA": "AMEX:INDA",
    "EWA": "AMEX:EWA",
    # MEA
    "^TA125.TA": "TASE:TA125",
    "^CASE30": "EGX:EGX30",
    "^J203.JO": "JSE:J203",
    "EZA": "AMEX:EZA",
    # World / EM
    "EFA": "AMEX:EFA",
    "EEM": "AMEX:EEM",
    "VXUS": "NASDAQ:VXUS",
    "IEFA": "AMEX:IEFA",
    "ACWX": "NASDAQ:ACWX",
    "VWO": "AMEX:VWO",
    "IEMG": "AMEX:IEMG",
    # US stocks
    "AAPL": "NASDAQ:AAPL",
    "MSFT": "NASDAQ:MSFT",
    "NVDA": "NASDAQ:NVDA",
    "JPM": "NYSE:JPM",
    "TSLA": "NASDAQ:TSLA",
    "AMZN": "NASDAQ:AMZN",
    "META": "NASDAQ:META",
    "GOOGL": "NASDAQ:GOOGL",
    # Bonds
    "TLT": "NASDAQ:TLT",
    "IEF": "NASDAQ:IEF",
    "LQD": "AMEX:LQD",
    "HYG": "AMEX:HYG",
    # Commodities
    "GC=F": "COMEX:GC1!",
    "SI=F": "COMEX:SI1!",
    "CL=F": "NYMEX:CL1!",
    "NG=F": "NYMEX:NG1!",
    # Forex
    "EURUSD=X": "FX_IDC:EURUSD",
    "GBPUSD=X": "FX_IDC:GBPUSD",
    "USDJPY=X": "FX_IDC:USDJPY",
    "USDBRL=X": "FX_IDC:USDBRL",
    "USDCNY=X": "FX_IDC:USDCNY",
    "USDRUB=X": "FX_IDC:USDRUB",
    "DX-Y.NYB": "TVC:DXY",
}

TV_COLUMNS = ["close", "change", "change_abs", "name", "description", "volume"]


def tv_ticker_for(symbol: str) -> str | None:
    key = symbol.strip()
    return TV_SYMBOL_MAP.get(key.upper()) or TV_SYMBOL_MAP.get(key)


async def fetch_tradingview_quotes(
    client: httpx.AsyncClient,
    symbols: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Batch-fetch live quotes from TradingView scanner.
    Returns map: catalog_symbol → {close, change_pct, name, tv_symbol, source}.
    """
    pairs: list[tuple[str, str]] = []
    for sym in symbols:
        tv = tv_ticker_for(sym)
        if tv:
            pairs.append((sym, tv))
    if not pairs:
        return {}

    out: dict[str, dict[str, Any]] = {}
    chunk_size = 40
    reverse = {tv: cat for cat, tv in pairs}

    for i in range(0, len(pairs), chunk_size):
        chunk = pairs[i : i + chunk_size]
        payload = {
            "symbols": {"tickers": [tv for _, tv in chunk], "query": {"types": []}},
            "columns": TV_COLUMNS,
        }
        try:
            resp = await client.post(TV_SCAN_URL, headers=TV_HEADERS, json=payload, timeout=25)
            resp.raise_for_status()
            data = resp.json().get("data") or []
            for row in data:
                tv_sym = row.get("s") or ""
                cols = row.get("d") or []
                cat = reverse.get(tv_sym)
                if not cat or len(cols) < 1 or cols[0] is None:
                    continue
                change = cols[1] if len(cols) > 1 else None
                out[cat.upper()] = {
                    "close": float(cols[0]),
                    "change_pct": float(change) if change is not None else None,
                    "name": cols[3] if len(cols) > 3 else cat,
                    "tv_symbol": tv_sym,
                    "source": "tradingview",
                }
        except Exception as exc:
            logger.warning("TradingView scan failed (chunk %d): %s", i // chunk_size, exc)

    return out


async def probe_tradingview(client: httpx.AsyncClient) -> dict[str, Any]:
    """Health probe — one liquid ticker."""
    try:
        data = await fetch_tradingview_quotes(client, ["AAPL"])
        ok = "AAPL" in data and data["AAPL"]["close"] > 0
        return {"ok": ok, "sample": data.get("AAPL")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

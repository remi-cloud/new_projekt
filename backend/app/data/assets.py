"""Global markets universe — symbols tradeable via Yahoo Finance / CoinGecko."""

from app.data.regional_universe import REGIONAL_UNIVERSE
from app.data.tokenized_universe import CRYPTO_ETF_UNIVERSE, TOKENIZED_UNIVERSE


def _dedupe_assets(assets: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in assets:
        sym = item["symbol"]
        if sym in seen:
            for existing in out:
                if existing["symbol"] == sym:
                    for k, v in item.items():
                        if k == "symbol":
                            continue
                        if k not in existing or existing.get(k) in (None, "", [], {}):
                            existing[k] = v
                        elif k == "tags":
                            existing[k] = list(dict.fromkeys(list(existing.get("tags") or []) + list(v or [])))
                        elif k == "related":
                            existing[k] = list(dict.fromkeys(list(existing.get("related") or []) + list(v or [])))
                    break
            continue
        seen.add(sym)
        out.append(dict(item))
    return out


_BASE_ASSETS = [
    # ── CRYPTO ──
    {"symbol": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto", "region": "global"},
    {"symbol": "ETH-USD", "name": "Ethereum", "asset_class": "crypto", "region": "global"},
    {"symbol": "SOL-USD", "name": "Solana", "asset_class": "crypto", "region": "global"},
    {"symbol": "BNB-USD", "name": "BNB", "asset_class": "crypto", "region": "global"},
    {"symbol": "XRP-USD", "name": "XRP", "asset_class": "crypto", "region": "global"},
    {"symbol": "ADA-USD", "name": "Cardano", "asset_class": "crypto", "region": "global"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "asset_class": "crypto", "region": "global"},
    {"symbol": "AVAX-USD", "name": "Avalanche", "asset_class": "crypto", "region": "global"},
    {"symbol": "LINK-USD", "name": "Chainlink", "asset_class": "crypto", "region": "global"},
    {"symbol": "DOT-USD", "name": "Polkadot", "asset_class": "crypto", "region": "global"},
    # ── US INDICES ──
    {"symbol": "^GSPC", "name": "S&P 500", "asset_class": "index", "region": "us"},
    {"symbol": "^DJI", "name": "Dow Jones", "asset_class": "index", "region": "us"},
    {"symbol": "^IXIC", "name": "NASDAQ", "asset_class": "index", "region": "us"},
    {"symbol": "^RUT", "name": "Russell 2000", "asset_class": "index", "region": "us"},
    {"symbol": "^NDX", "name": "NASDAQ 100", "asset_class": "index", "region": "us"},
    {"symbol": "^VIX", "name": "VIX (wolatylność)", "asset_class": "index", "region": "us"},
    {"symbol": "^NYA", "name": "NYSE Composite", "asset_class": "index", "region": "us"},
    {"symbol": "^W5000", "name": "Wilshire 5000", "asset_class": "index", "region": "us"},
    # ── EUROPE INDICES ──
    {"symbol": "^GDAXI", "name": "DAX (Niemcy)", "asset_class": "index", "region": "eu"},
    {"symbol": "^FTSE", "name": "FTSE 100 (UK)", "asset_class": "index", "region": "eu"},
    {"symbol": "^FCHI", "name": "CAC 40 (Francja)", "asset_class": "index", "region": "eu"},
    {"symbol": "^STOXX50E", "name": "Euro Stoxx 50", "asset_class": "index", "region": "eu"},
    {"symbol": "^IBEX", "name": "IBEX 35 (Hiszpania)", "asset_class": "index", "region": "eu"},
    {"symbol": "^AEX", "name": "AEX (Holandia)", "asset_class": "index", "region": "eu"},
    {"symbol": "^SSMI", "name": "SMI (Szwajcaria)", "asset_class": "index", "region": "eu"},
    # ── ASIA-PACIFIC INDICES ──
    {"symbol": "^N225", "name": "Nikkei 225 (Japonia)", "asset_class": "index", "region": "asia"},
    {"symbol": "^HSI", "name": "Hang Seng (Hong Kong)", "asset_class": "index", "region": "asia"},
    {"symbol": "000001.SS", "name": "SSE Composite (Chiny)", "asset_class": "index", "region": "asia"},
    {"symbol": "^KS11", "name": "KOSPI (Korea)", "asset_class": "index", "region": "asia"},
    {"symbol": "^TWII", "name": "TAIEX (Tajwan)", "asset_class": "index", "region": "asia"},
    {"symbol": "^BSESN", "name": "BSE Sensex (Indie)", "asset_class": "index", "region": "asia"},
    {"symbol": "^STI", "name": "STI (Singapur)", "asset_class": "index", "region": "asia"},
    {"symbol": "^AXJO", "name": "ASX 200 (Australia)", "asset_class": "index", "region": "asia"},
    # ── EMERGING MARKETS ──
    {"symbol": "^BVSP", "name": "Bovespa (Brazylia)", "asset_class": "index", "region": "em"},
    {"symbol": "^MXX", "name": "IPC (Meksyk)", "asset_class": "index", "region": "em"},
    {"symbol": "^JKSE", "name": "Jakarta Composite", "asset_class": "index", "region": "em"},
    {"symbol": "^TA125.TA", "name": "TA-125 (Izrael)", "asset_class": "index", "region": "em"},
    # ── MAGNIFICENT SEVEN (Mag7) ──
    {"symbol": "AAPL", "name": "Apple (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "MSFT", "name": "Microsoft (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "GOOGL", "name": "Alphabet (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "AMZN", "name": "Amazon (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "NVDA", "name": "NVIDIA (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "META", "name": "Meta (Mag7)", "asset_class": "stock", "region": "us"},
    {"symbol": "TSLA", "name": "Tesla (Mag7)", "asset_class": "stock", "region": "us"},
    # ── ELON MUSK ECOSYSTEM (SpaceX IPO Jun 2026 — Nasdaq SPCX) ──
    {"symbol": "SPCX", "name": "SpaceX (Space Exploration Technologies)", "asset_class": "stock", "region": "us"},
    # Alias card → same live SPCX tape (not ARKX)
    {"symbol": "SPACEX", "name": "SpaceX (alias → SPCX)", "asset_class": "stock", "region": "us", "yahoo_symbol": "SPCX"},
    {"symbol": "ARKX", "name": "ARK Space Exploration ETF", "asset_class": "stock", "region": "us"},
    {"symbol": "RKLB", "name": "Rocket Lab (kosmos)", "asset_class": "stock", "region": "us"},
    {"symbol": "IRDM", "name": "Iridium (satelity)", "asset_class": "stock", "region": "us"},
    {"symbol": "ASTS", "name": "AST SpaceMobile (satelity)", "asset_class": "stock", "region": "us"},
    {"symbol": "GSAT", "name": "Globalstar (satelity)", "asset_class": "stock", "region": "us"},
    {"symbol": "LMT", "name": "Lockheed Martin (NASA/SpaceX)", "asset_class": "stock", "region": "us"},
    {"symbol": "BA", "name": "Boeing (kosmonautyka)", "asset_class": "stock", "region": "us"},
    {"symbol": "ALB", "name": "Albemarle (lit Tesla)", "asset_class": "stock", "region": "us"},
    {"symbol": "SQM", "name": "SQM (lit Tesla)", "asset_class": "stock", "region": "us"},
    {"symbol": "MP", "name": "MP Materials (magnesy Tesla)", "asset_class": "stock", "region": "us"},
    {"symbol": "ON", "name": "ON Semiconductor (chips Tesla)", "asset_class": "stock", "region": "us"},
    {"symbol": "STM", "name": "STMicroelectronics (Tesla)", "asset_class": "stock", "region": "us"},
    {"symbol": "6752.T", "name": "Panasonic (baterie Tesla)", "asset_class": "stock", "region": "asia"},
    {"symbol": "373220.KS", "name": "LG Energy Solution (Tesla)", "asset_class": "stock", "region": "asia"},
    # ── US STOCKS (mega cap) ──
    {"symbol": "JPM", "name": "JPMorgan", "asset_class": "stock", "region": "us"},
    {"symbol": "V", "name": "Visa", "asset_class": "stock", "region": "us"},
    {"symbol": "XOM", "name": "Exxon Mobil", "asset_class": "stock", "region": "us"},
    # ── EUROPE STOCKS ──
    {"symbol": "ASML", "name": "ASML (NL)", "asset_class": "stock", "region": "eu"},
    {"symbol": "SAP", "name": "SAP (DE)", "asset_class": "stock", "region": "eu"},
    {"symbol": "MC.PA", "name": "LVMH (FR)", "asset_class": "stock", "region": "eu"},
    {"symbol": "SHEL", "name": "Shell (UK)", "asset_class": "stock", "region": "eu"},
    {"symbol": "NESN.SW", "name": "Nestlé (CH)", "asset_class": "stock", "region": "eu"},
    # ── ASIA STOCKS ──
    {"symbol": "TSM", "name": "TSMC (Tajwan)", "asset_class": "stock", "region": "asia"},
    {"symbol": "BABA", "name": "Alibaba", "asset_class": "stock", "region": "asia"},
    {"symbol": "SONY", "name": "Sony (Japonia)", "asset_class": "stock", "region": "asia"},
    {"symbol": "TM", "name": "Toyota", "asset_class": "stock", "region": "asia"},
    {"symbol": "005930.KS", "name": "Samsung (Korea)", "asset_class": "stock", "region": "asia"},
    # ── POLAND INDICES ──
    {"symbol": "WIG20.WA", "name": "WIG20", "asset_class": "index", "region": "pl"},
    {"symbol": "WIG.WA", "name": "WIG (WIG All Share)", "asset_class": "index", "region": "pl"},
    {"symbol": "MWIG40.WA", "name": "mWIG40", "asset_class": "index", "region": "pl"},
    {"symbol": "SWIG80.WA", "name": "sWIG80", "asset_class": "index", "region": "pl"},
    # ── POLAND STOCKS (WIG20 + blue chips) ──
    {"symbol": "PKN.WA", "name": "Orlen", "asset_class": "stock", "region": "pl"},
    {"symbol": "PKO.WA", "name": "PKO BP", "asset_class": "stock", "region": "pl"},
    {"symbol": "PZU.WA", "name": "PZU", "asset_class": "stock", "region": "pl"},
    {"symbol": "PEO.WA", "name": "Bank Pekao", "asset_class": "stock", "region": "pl"},
    {"symbol": "KGH.WA", "name": "KGHM", "asset_class": "stock", "region": "pl"},
    {"symbol": "DNP.WA", "name": "Dino Polska", "asset_class": "stock", "region": "pl"},
    {"symbol": "CDR.WA", "name": "CD Projekt", "asset_class": "stock", "region": "pl"},
    {"symbol": "LPP.WA", "name": "LPP", "asset_class": "stock", "region": "pl"},
    {"symbol": "ALE.WA", "name": "Allegro", "asset_class": "stock", "region": "pl"},
    {"symbol": "PGE.WA", "name": "PGE", "asset_class": "stock", "region": "pl"},
    {"symbol": "SAN.WA", "name": "Santander Bank Polska", "asset_class": "stock", "region": "pl"},
    {"symbol": "ALR.WA", "name": "Alior Bank", "asset_class": "stock", "region": "pl"},
    {"symbol": "KRU.WA", "name": "Kruk", "asset_class": "stock", "region": "pl"},
    {"symbol": "MBK.WA", "name": "mBank", "asset_class": "stock", "region": "pl"},
    {"symbol": "CPS.WA", "name": "Cyfrowy Polsat", "asset_class": "stock", "region": "pl"},
    {"symbol": "JSW.WA", "name": "JSW", "asset_class": "stock", "region": "pl"},
    {"symbol": "OPL.WA", "name": "Orange Polska", "asset_class": "stock", "region": "pl"},
    {"symbol": "TPE.WA", "name": "Tauron", "asset_class": "stock", "region": "pl"},
    {"symbol": "XTB.WA", "name": "XTB", "asset_class": "stock", "region": "pl"},
    {"symbol": "11B.WA", "name": "11 bit studios", "asset_class": "stock", "region": "pl"},
    {"symbol": "BDX.WA", "name": "Budimex", "asset_class": "stock", "region": "pl"},
    # ── BONDS (ETF proxies) ──
    {"symbol": "TLT", "name": "US Treasury 20+Y", "asset_class": "bond", "region": "us"},
    {"symbol": "IEF", "name": "US Treasury 7-10Y", "asset_class": "bond", "region": "us"},
    {"symbol": "SHY", "name": "US Treasury 1-3Y", "asset_class": "bond", "region": "us"},
    {"symbol": "LQD", "name": "US Investment Grade", "asset_class": "bond", "region": "us"},
    {"symbol": "HYG", "name": "US High Yield", "asset_class": "bond", "region": "us"},
    {"symbol": "BNDX", "name": "Global Bonds ex-US", "asset_class": "bond", "region": "global"},
    {"symbol": "EMB", "name": "Emerging Markets Bonds", "asset_class": "bond", "region": "em"},
    {"symbol": "TIP", "name": "US TIPS (inflacja)", "asset_class": "bond", "region": "us"},
    {"symbol": "VGIT", "name": "US Treasury Mid", "asset_class": "bond", "region": "us"},
    # ── SECTOR / UTILITY / COMMODITY ETFs (calendar seasonality coverage) ──
    {"symbol": "XLU", "name": "Utilities Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLE", "name": "Energy Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLF", "name": "Financial Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLB", "name": "Materials Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLI", "name": "Industrial Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLP", "name": "Consumer Staples Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLV", "name": "Health Care Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLY", "name": "Consumer Discretionary Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "XLRE", "name": "Real Estate Select Sector", "asset_class": "etf", "region": "us"},
    {"symbol": "GLD", "name": "SPDR Gold Shares", "asset_class": "etf", "region": "global"},
    {"symbol": "SLV", "name": "iShares Silver Trust", "asset_class": "etf", "region": "global"},
    {"symbol": "USO", "name": "United States Oil Fund", "asset_class": "etf", "region": "global"},
    {"symbol": "UNG", "name": "United States Natural Gas", "asset_class": "etf", "region": "global"},
    {"symbol": "DBA", "name": "Invesco DB Agriculture", "asset_class": "etf", "region": "global"},
    # ── COMMODITIES ──
    {"symbol": "GC=F", "name": "Złoto", "asset_class": "commodity", "region": "global"},
    {"symbol": "SI=F", "name": "Srebro", "asset_class": "commodity", "region": "global"},
    {"symbol": "PL=F", "name": "Platyna", "asset_class": "commodity", "region": "global"},
    {"symbol": "PA=F", "name": "Pallad", "asset_class": "commodity", "region": "global"},
    {"symbol": "CL=F", "name": "Ropa WTI", "asset_class": "commodity", "region": "global"},
    {"symbol": "BZ=F", "name": "Ropa Brent", "asset_class": "commodity", "region": "global"},
    {"symbol": "NG=F", "name": "Gaz ziemny", "asset_class": "commodity", "region": "global"},
    {"symbol": "HG=F", "name": "Miedź", "asset_class": "commodity", "region": "global"},
    {"symbol": "ZC=F", "name": "Kukurydza", "asset_class": "commodity", "region": "global"},
    {"symbol": "ZW=F", "name": "Pszenica", "asset_class": "commodity", "region": "global"},
    {"symbol": "SB=F", "name": "Cukier", "asset_class": "commodity", "region": "global"},
    {"symbol": "KC=F", "name": "Kawa", "asset_class": "commodity", "region": "global"},
    # ── FOREX ──
    {"symbol": "EURUSD=X", "name": "EUR/USD", "asset_class": "forex", "region": "global"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "asset_class": "forex", "region": "global"},
    {"symbol": "USDJPY=X", "name": "USD/JPY", "asset_class": "forex", "region": "global"},
    {"symbol": "USDCHF=X", "name": "USD/CHF", "asset_class": "forex", "region": "global"},
    {"symbol": "AUDUSD=X", "name": "AUD/USD", "asset_class": "forex", "region": "global"},
    {"symbol": "USDCAD=X", "name": "USD/CAD", "asset_class": "forex", "region": "global"},
    {"symbol": "NZDUSD=X", "name": "NZD/USD", "asset_class": "forex", "region": "global"},
    {"symbol": "EURJPY=X", "name": "EUR/JPY", "asset_class": "forex", "region": "global"},
    {"symbol": "EURGBP=X", "name": "EUR/GBP", "asset_class": "forex", "region": "global"},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "asset_class": "forex", "region": "global"},
]

MONITORED_ASSETS = _dedupe_assets(
    _BASE_ASSETS + REGIONAL_UNIVERSE + TOKENIZED_UNIVERSE + CRYPTO_ETF_UNIVERSE
)
DEFAULT_ASSETS = MONITORED_ASSETS

US_INDEX_SYMBOLS = {
    "^GSPC",
    "^DJI",
    "^IXIC",
    "^RUT",
    "^NDX",
    "^VIX",
    "^NYA",
    "^W5000",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
}

CATALOG_BY_SYMBOL = {a["symbol"].upper(): a for a in MONITORED_ASSETS}


def lookup_asset(symbol: str) -> dict | None:
    return CATALOG_BY_SYMBOL.get(symbol.strip().upper())


def resolve_yahoo_symbol(symbol: str) -> str:
    """Map app symbols to Yahoo tickers when they collide (e.g. MEW-USD → MEW30126-USD)."""
    meta = lookup_asset(symbol)
    if meta and meta.get("yahoo_symbol"):
        return str(meta["yahoo_symbol"])
    return symbol


def is_price_proxy(symbol: str) -> bool:
    meta = lookup_asset(symbol)
    yahoo = str(meta.get("yahoo_symbol") or "").strip().upper() if meta else ""
    return bool(yahoo and yahoo != symbol.strip().upper())


def display_symbol_label(symbol: str) -> str:
    """UI label — never pretend a private name is a listed equity ticker."""
    meta = lookup_asset(symbol)
    if not meta:
        return symbol
    name = str(meta.get("name") or symbol)
    yahoo = str(meta.get("yahoo_symbol") or "").strip()
    if yahoo and yahoo.upper() != symbol.strip().upper():
        return f"{symbol} · live {yahoo} (proxy)"
    return name if name != symbol else symbol


REGIONS = {
    "global": "Globalny",
    "us": "USA",
    "eu": "Europa",
    "asia": "Azja-Pacyfik",
    "em": "Rynki wschodzące",
    "pl": "Polska",
}

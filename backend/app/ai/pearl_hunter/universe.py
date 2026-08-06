"""Discovery universes for pearl hunters (outside MONITORED_ASSETS)."""

from __future__ import annotations

from app.data.assets import MONITORED_ASSETS

_MONITORED_SYMBOLS = {a["symbol"] for a in MONITORED_ASSETS}

# Mid/small-cap & sector names typically outside our core Mag7 / majors watchlist
EQUITY_DISCOVERY: list[dict] = [
    {"symbol": "SMCI", "name": "Super Micro Computer", "asset_class": "stock", "region": "us"},
    {"symbol": "ARM", "name": "Arm Holdings", "asset_class": "stock", "region": "us"},
    {"symbol": "PLTR", "name": "Palantir", "asset_class": "stock", "region": "us"},
    {"symbol": "SNOW", "name": "Snowflake", "asset_class": "stock", "region": "us"},
    {"symbol": "CRWD", "name": "CrowdStrike", "asset_class": "stock", "region": "us"},
    {"symbol": "NET", "name": "Cloudflare", "asset_class": "stock", "region": "us"},
    {"symbol": "DDOG", "name": "Datadog", "asset_class": "stock", "region": "us"},
    {"symbol": "MDB", "name": "MongoDB", "asset_class": "stock", "region": "us"},
    {"symbol": "SHOP", "name": "Shopify", "asset_class": "stock", "region": "us"},
    {"symbol": "SQ", "name": "Block Inc", "asset_class": "stock", "region": "us"},
    {"symbol": "COIN", "name": "Coinbase", "asset_class": "stock", "region": "us"},
    {"symbol": "HOOD", "name": "Robinhood", "asset_class": "stock", "region": "us"},
    {"symbol": "SOFI", "name": "SoFi", "asset_class": "stock", "region": "us"},
    {"symbol": "UPST", "name": "Upstart", "asset_class": "stock", "region": "us"},
    {"symbol": "AFRM", "name": "Affirm", "asset_class": "stock", "region": "us"},
    {"symbol": "RIVN", "name": "Rivian", "asset_class": "stock", "region": "us"},
    {"symbol": "LCID", "name": "Lucid", "asset_class": "stock", "region": "us"},
    {"symbol": "NIO", "name": "NIO", "asset_class": "stock", "region": "asia"},
    {"symbol": "XPEV", "name": "XPeng", "asset_class": "stock", "region": "asia"},
    {"symbol": "LI", "name": "Li Auto", "asset_class": "stock", "region": "asia"},
    {"symbol": "JD", "name": "JD.com", "asset_class": "stock", "region": "asia"},
    {"symbol": "PDD", "name": "PDD Holdings", "asset_class": "stock", "region": "asia"},
    {"symbol": "SE", "name": "Sea Limited", "asset_class": "stock", "region": "asia"},
    {"symbol": "GRAB", "name": "Grab", "asset_class": "stock", "region": "asia"},
    {"symbol": "NU", "name": "Nu Holdings", "asset_class": "stock", "region": "em"},
    {"symbol": "MELI", "name": "MercadoLibre", "asset_class": "stock", "region": "em"},
    {"symbol": "GLOB", "name": "Globant", "asset_class": "stock", "region": "em"},
    {"symbol": "ENPH", "name": "Enphase", "asset_class": "stock", "region": "us"},
    {"symbol": "SEDG", "name": "SolarEdge", "asset_class": "stock", "region": "us"},
    {"symbol": "FSLR", "name": "First Solar", "asset_class": "stock", "region": "us"},
    {"symbol": "BE", "name": "Bloom Energy", "asset_class": "stock", "region": "us"},
    {"symbol": "OKLO", "name": "Oklo", "asset_class": "stock", "region": "us"},
    {"symbol": "SMR", "name": "NuScale Power", "asset_class": "stock", "region": "us"},
    {"symbol": "CCJ", "name": "Cameco", "asset_class": "stock", "region": "us"},
    {"symbol": "UEC", "name": "Uranium Energy", "asset_class": "stock", "region": "us"},
    {"symbol": "MP", "name": "MP Materials", "asset_class": "stock", "region": "us"},
    {"symbol": "ALB", "name": "Albemarle", "asset_class": "stock", "region": "us"},
    {"symbol": "SQM", "name": "SQM", "asset_class": "stock", "region": "em"},
    {"symbol": "LAC", "name": "Lithium Americas", "asset_class": "stock", "region": "us"},
    {"symbol": "IONQ", "name": "IonQ", "asset_class": "stock", "region": "us"},
    {"symbol": "RGTI", "name": "Rigetti", "asset_class": "stock", "region": "us"},
    {"symbol": "QBTS", "name": "D-Wave", "asset_class": "stock", "region": "us"},
    {"symbol": "PATH", "name": "UiPath", "asset_class": "stock", "region": "us"},
    {"symbol": "AI", "name": "C3.ai", "asset_class": "stock", "region": "us"},
    {"symbol": "BBAI", "name": "BigBear.ai", "asset_class": "stock", "region": "us"},
    {"symbol": "SOUN", "name": "SoundHound AI", "asset_class": "stock", "region": "us"},
    {"symbol": "HIMS", "name": "Hims & Hers", "asset_class": "stock", "region": "us"},
    {"symbol": "CELH", "name": "Celsius", "asset_class": "stock", "region": "us"},
    {"symbol": "DUOL", "name": "Duolingo", "asset_class": "stock", "region": "us"},
    {"symbol": "TTD", "name": "The Trade Desk", "asset_class": "stock", "region": "us"},
    {"symbol": "ROKU", "name": "Roku", "asset_class": "stock", "region": "us"},
    {"symbol": "SPOT", "name": "Spotify", "asset_class": "stock", "region": "eu"},
    {"symbol": "UBER", "name": "Uber", "asset_class": "stock", "region": "us"},
    {"symbol": "ABNB", "name": "Airbnb", "asset_class": "stock", "region": "us"},
    {"symbol": "DASH", "name": "DoorDash", "asset_class": "stock", "region": "us"},
    {"symbol": "ZM", "name": "Zoom", "asset_class": "stock", "region": "us"},
    {"symbol": "DOCU", "name": "DocuSign", "asset_class": "stock", "region": "us"},
    {"symbol": "U", "name": "Unity", "asset_class": "stock", "region": "us"},
    {"symbol": "RBLX", "name": "Roblox", "asset_class": "stock", "region": "us"},
    {"symbol": "TTWO", "name": "Take-Two", "asset_class": "stock", "region": "us"},
    {"symbol": "EA", "name": "Electronic Arts", "asset_class": "stock", "region": "us"},
    {"symbol": "DKNG", "name": "DraftKings", "asset_class": "stock", "region": "us"},
    {"symbol": "PENN", "name": "PENN Entertainment", "asset_class": "stock", "region": "us"},
    {"symbol": "MARA", "name": "Marathon Digital", "asset_class": "stock", "region": "us"},
    {"symbol": "RIOT", "name": "Riot Platforms", "asset_class": "stock", "region": "us"},
    {"symbol": "CLSK", "name": "CleanSpark", "asset_class": "stock", "region": "us"},
    {"symbol": "HUT", "name": "Hut 8", "asset_class": "stock", "region": "us"},
    {"symbol": "IREN", "name": "Iris Energy", "asset_class": "stock", "region": "us"},
    {"symbol": "CIFR", "name": "Cipher Mining", "asset_class": "stock", "region": "us"},
    {"symbol": "APLD", "name": "Applied Digital", "asset_class": "stock", "region": "us"},
    {"symbol": "VRT", "name": "Vertiv", "asset_class": "stock", "region": "us"},
    {"symbol": "DELL", "name": "Dell Technologies", "asset_class": "stock", "region": "us"},
    {"symbol": "HPE", "name": "Hewlett Packard Ent.", "asset_class": "stock", "region": "us"},
    {"symbol": "ANET", "name": "Arista Networks", "asset_class": "stock", "region": "us"},
    {"symbol": "MRVL", "name": "Marvell", "asset_class": "stock", "region": "us"},
    {"symbol": "MU", "name": "Micron", "asset_class": "stock", "region": "us"},
    {"symbol": "AMAT", "name": "Applied Materials", "asset_class": "stock", "region": "us"},
    {"symbol": "LRCX", "name": "Lam Research", "asset_class": "stock", "region": "us"},
    {"symbol": "KLAC", "name": "KLA Corp", "asset_class": "stock", "region": "us"},
    {"symbol": "ASML", "name": "ASML", "asset_class": "stock", "region": "eu"},
    {"symbol": "TSM", "name": "TSMC", "asset_class": "stock", "region": "asia"},
]


def equity_candidates(limit: int = 40) -> list[dict]:
    out = [a for a in EQUITY_DISCOVERY if a["symbol"] not in _MONITORED_SYMBOLS]
    return out[:limit]


def is_monitored(symbol: str) -> bool:
    return symbol in _MONITORED_SYMBOLS

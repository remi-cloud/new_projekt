"""Top stocks, ETFs and bond ETFs per global market region (Yahoo Finance symbols)."""

# Each region: up to 10 stocks, 10 equity ETFs, 10 bond ETFs (deduped at merge time).

US_TOP_STOCKS = [
    {"symbol": "BRK-B", "name": "Berkshire Hathaway", "asset_class": "stock", "region": "us"},
    {"symbol": "LLY", "name": "Eli Lilly", "asset_class": "stock", "region": "us"},
    {"symbol": "AVGO", "name": "Broadcom", "asset_class": "stock", "region": "us"},
    {"symbol": "WMT", "name": "Walmart", "asset_class": "stock", "region": "us"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "asset_class": "stock", "region": "us"},
    {"symbol": "UNH", "name": "UnitedHealth", "asset_class": "stock", "region": "us"},
    {"symbol": "MA", "name": "Mastercard", "asset_class": "stock", "region": "us"},
    {"symbol": "PG", "name": "Procter & Gamble", "asset_class": "stock", "region": "us"},
    {"symbol": "HD", "name": "Home Depot", "asset_class": "stock", "region": "us"},
    {"symbol": "COST", "name": "Costco", "asset_class": "stock", "region": "us"},
]

US_TOP_ETFS = [
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "asset_class": "etf", "region": "us"},
    {"symbol": "QQQ", "name": "Invesco QQQ (NASDAQ 100)", "asset_class": "etf", "region": "us"},
    {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "asset_class": "etf", "region": "us"},
    {"symbol": "IVV", "name": "iShares Core S&P 500", "asset_class": "etf", "region": "us"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market", "asset_class": "etf", "region": "us"},
    {"symbol": "IWM", "name": "iShares Russell 2000", "asset_class": "etf", "region": "us"},
    {"symbol": "DIA", "name": "SPDR Dow Jones ETF", "asset_class": "etf", "region": "us"},
    {"symbol": "XLK", "name": "Technology Select Sector SPDR", "asset_class": "etf", "region": "us"},
    {"symbol": "XLF", "name": "Financial Select Sector SPDR", "asset_class": "etf", "region": "us"},
    {"symbol": "SCHD", "name": "Schwab US Dividend Equity", "asset_class": "etf", "region": "us"},
]

US_TOP_BONDS = [
    {"symbol": "BIL", "name": "SPDR 1-3M T-Bill", "asset_class": "bond", "region": "us"},
    {"symbol": "AGG", "name": "iShares Core US Aggregate Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "MUB", "name": "iShares National Muni Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "VCIT", "name": "Vanguard Interm Corp Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "VCSH", "name": "Vanguard Short-Term Corp Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "GOVT", "name": "iShares US Treasury Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "SCHP", "name": "Schwab US TIPS ETF", "asset_class": "bond", "region": "us"},
    {"symbol": "JNK", "name": "SPDR High Yield Bond", "asset_class": "bond", "region": "us"},
    {"symbol": "BKLN", "name": "Invesco Senior Loan ETF", "asset_class": "bond", "region": "us"},
    {"symbol": "BND", "name": "Vanguard Total Bond Market", "asset_class": "bond", "region": "us"},
]

EU_TOP_STOCKS = [
    {"symbol": "OR.PA", "name": "L'Oréal (FR)", "asset_class": "stock", "region": "eu"},
    {"symbol": "TTE.PA", "name": "TotalEnergies (FR)", "asset_class": "stock", "region": "eu"},
    {"symbol": "SIE.DE", "name": "Siemens (DE)", "asset_class": "stock", "region": "eu"},
    {"symbol": "ALV.DE", "name": "Allianz (DE)", "asset_class": "stock", "region": "eu"},
    {"symbol": "HSBA.L", "name": "HSBC (UK)", "asset_class": "stock", "region": "eu"},
    {"symbol": "AZN.L", "name": "AstraZeneca (UK)", "asset_class": "stock", "region": "eu"},
    {"symbol": "RHHBY", "name": "Roche (CH ADR)", "asset_class": "stock", "region": "eu"},
    {"symbol": "NOVN.SW", "name": "Novartis (CH)", "asset_class": "stock", "region": "eu"},
    {"symbol": "SAN.MC", "name": "Santander (ES)", "asset_class": "stock", "region": "eu"},
    {"symbol": "IBE.MC", "name": "Iberdrola (ES)", "asset_class": "stock", "region": "eu"},
]

EU_TOP_ETFS = [
    {"symbol": "VGK", "name": "Vanguard FTSE Europe ETF", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWG", "name": "iShares MSCI Germany", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWU", "name": "iShares MSCI UK", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWQ", "name": "iShares MSCI France", "asset_class": "etf", "region": "eu"},
    {"symbol": "FEZ", "name": "SPDR Euro Stoxx 50", "asset_class": "etf", "region": "eu"},
    {"symbol": "EZU", "name": "iShares MSCI Eurozone", "asset_class": "etf", "region": "eu"},
    {"symbol": "IEUR", "name": "iShares Core MSCI Europe", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWL", "name": "iShares MSCI Switzerland", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWP", "name": "iShares MSCI Spain", "asset_class": "etf", "region": "eu"},
    {"symbol": "EWN", "name": "iShares MSCI Netherlands", "asset_class": "etf", "region": "eu"},
]

EU_TOP_BONDS = [
    {"symbol": "IGOV", "name": "iShares Intl Treasury Bond", "asset_class": "bond", "region": "eu"},
    {"symbol": "BWX", "name": "SPDR Intl Treasury Bond", "asset_class": "bond", "region": "eu"},
    {"symbol": "IGEB", "name": "iShares Investment Grade Bond", "asset_class": "bond", "region": "eu"},
    {"symbol": "VWOB", "name": "Vanguard EM Govt Bond USD", "asset_class": "bond", "region": "eu"},
    {"symbol": "IGIB", "name": "iShares 5-10Y IG Corporate", "asset_class": "bond", "region": "eu"},
    {"symbol": "IGSB", "name": "iShares 1-5Y IG Corporate", "asset_class": "bond", "region": "eu"},
    {"symbol": "VCIT", "name": "Vanguard Interm Corp Bond (EU IG proxy)", "asset_class": "bond", "region": "eu"},
    {"symbol": "FLOT", "name": "iShares Floating Rate Bond", "asset_class": "bond", "region": "eu"},
    {"symbol": "SPSB", "name": "SPDR Portfolio Short Term Corp", "asset_class": "bond", "region": "eu"},
    {"symbol": "SPLB", "name": "SPDR Portfolio Long Term Corp", "asset_class": "bond", "region": "eu"},
]

ASIA_TOP_STOCKS = [
    {"symbol": "9984.T", "name": "SoftBank Group (JP)", "asset_class": "stock", "region": "asia"},
    {"symbol": "7203.T", "name": "Toyota Motor (JP)", "asset_class": "stock", "region": "asia"},
    {"symbol": "0700.HK", "name": "Tencent (HK)", "asset_class": "stock", "region": "asia"},
    {"symbol": "9988.HK", "name": "Alibaba (HK)", "asset_class": "stock", "region": "asia"},
    {"symbol": "000660.KS", "name": "SK Hynix (KR)", "asset_class": "stock", "region": "asia"},
    {"symbol": "2330.TW", "name": "TSMC (TW)", "asset_class": "stock", "region": "asia"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries (IN)", "asset_class": "stock", "region": "asia"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank (IN)", "asset_class": "stock", "region": "asia"},
    {"symbol": "BHP.AX", "name": "BHP Group (AU)", "asset_class": "stock", "region": "asia"},
    {"symbol": "CBA.AX", "name": "Commonwealth Bank (AU)", "asset_class": "stock", "region": "asia"},
]

ASIA_TOP_ETFS = [
    {"symbol": "EWJ", "name": "iShares MSCI Japan", "asset_class": "etf", "region": "asia"},
    {"symbol": "EWT", "name": "iShares MSCI Taiwan", "asset_class": "etf", "region": "asia"},
    {"symbol": "EWH", "name": "iShares MSCI Hong Kong", "asset_class": "etf", "region": "asia"},
    {"symbol": "EWY", "name": "iShares MSCI South Korea", "asset_class": "etf", "region": "asia"},
    {"symbol": "INDA", "name": "iShares MSCI India", "asset_class": "etf", "region": "asia"},
    {"symbol": "FXI", "name": "iShares China Large-Cap", "asset_class": "etf", "region": "asia"},
    {"symbol": "MCHI", "name": "iShares MSCI China", "asset_class": "etf", "region": "asia"},
    {"symbol": "EWS", "name": "iShares MSCI Singapore", "asset_class": "etf", "region": "asia"},
    {"symbol": "EWA", "name": "iShares MSCI Australia", "asset_class": "etf", "region": "asia"},
    {"symbol": "EPP", "name": "iShares MSCI Pacific ex-Japan", "asset_class": "etf", "region": "asia"},
]

ASIA_TOP_BONDS = [
    {"symbol": "IBND", "name": "SPDR Intl Corporate Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "EMLC", "name": "VanEck EM Local Currency Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "PCY", "name": "Invesco EM Sovereign Debt", "asset_class": "bond", "region": "asia"},
    {"symbol": "EMHY", "name": "iShares EM High Yield Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "LEMB", "name": "iShares EM Local Currency Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "EBND", "name": "SPDR Bloomberg EM Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "JPMB", "name": "JPMorgan USD EM Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "VCSH", "name": "Vanguard Short-Term Corp (Asia IG proxy)", "asset_class": "bond", "region": "asia"},
    {"symbol": "SHV", "name": "iShares Short Treasury Bond", "asset_class": "bond", "region": "asia"},
    {"symbol": "SUB", "name": "iShares Short-Term National Muni", "asset_class": "bond", "region": "asia"},
]

EM_TOP_STOCKS = [
    {"symbol": "PBR", "name": "Petrobras (BR)", "asset_class": "stock", "region": "em"},
    {"symbol": "VALE", "name": "Vale (BR)", "asset_class": "stock", "region": "em"},
    {"symbol": "ITUB", "name": "Itaú Unibanco (BR)", "asset_class": "stock", "region": "em"},
    {"symbol": "MELI", "name": "MercadoLibre (LA)", "asset_class": "stock", "region": "em"},
    {"symbol": "NU", "name": "Nu Holdings (BR)", "asset_class": "stock", "region": "em"},
    {"symbol": "BBD", "name": "Bradesco (BR)", "asset_class": "stock", "region": "em"},
    {"symbol": "IBN", "name": "ICICI Bank (IN)", "asset_class": "stock", "region": "em"},
    {"symbol": "AMX", "name": "América Móvil (MX)", "asset_class": "stock", "region": "em"},
    {"symbol": "INFY", "name": "Infosys (IN)", "asset_class": "stock", "region": "em"},
    {"symbol": "WIT", "name": "Wipro (IN)", "asset_class": "stock", "region": "em"},
]

EM_TOP_ETFS = [
    {"symbol": "VWO", "name": "Vanguard FTSE EM ETF", "asset_class": "etf", "region": "em"},
    {"symbol": "EEM", "name": "iShares MSCI EM ETF", "asset_class": "etf", "region": "em"},
    {"symbol": "IEMG", "name": "iShares Core MSCI EM", "asset_class": "etf", "region": "em"},
    {"symbol": "EWZ", "name": "iShares MSCI Brazil", "asset_class": "etf", "region": "em"},
    {"symbol": "EWW", "name": "iShares MSCI Mexico", "asset_class": "etf", "region": "em"},
    {"symbol": "ECH", "name": "iShares MSCI Chile", "asset_class": "etf", "region": "em"},
    {"symbol": "EPHE", "name": "iShares MSCI Philippines", "asset_class": "etf", "region": "em"},
    {"symbol": "EZA", "name": "iShares MSCI South Africa", "asset_class": "etf", "region": "em"},
    {"symbol": "TUR", "name": "iShares MSCI Turkey", "asset_class": "etf", "region": "em"},
    {"symbol": "VNM", "name": "VanEck Vietnam ETF", "asset_class": "etf", "region": "em"},
]

EM_TOP_BONDS = [
    {"symbol": "GEMD", "name": "Goldman EM Debt USD", "asset_class": "bond", "region": "em"},
    {"symbol": "EMCB", "name": "WisdomTree EM Corp Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "HYEM", "name": "VanEck EM High Yield Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "EMLC", "name": "VanEck EM Local Currency Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "PCY", "name": "Invesco EM Sovereign Debt", "asset_class": "bond", "region": "em"},
    {"symbol": "EMHY", "name": "iShares EM High Yield Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "JPMB", "name": "JPMorgan USD EM Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "LEMB", "name": "iShares EM Local Currency Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "EBND", "name": "SPDR Bloomberg EM Bond", "asset_class": "bond", "region": "em"},
    {"symbol": "VWOB", "name": "Vanguard EM Govt Bond USD", "asset_class": "bond", "region": "em"},
]

PL_TOP_ETFS = [
    {"symbol": "EPOL", "name": "iShares MSCI Poland ETF", "asset_class": "etf", "region": "pl"},
    {"symbol": "ETFBW20TR.WA", "name": "Beta ETF WIG20TR (PL)", "asset_class": "etf", "region": "pl"},
    {"symbol": "ETFSP500.WA", "name": "Beta ETF S&P 500 (PL)", "asset_class": "etf", "region": "pl"},
    {"symbol": "ETFDAX.WA", "name": "Beta ETF DAX (PL)", "asset_class": "etf", "region": "pl"},
    {"symbol": "WIG20TR.WA", "name": "WIG20TR Portfel (PL)", "asset_class": "etf", "region": "pl"},
    {"symbol": "WIG20LEV.WA", "name": "WIG20 Leverage (PL)", "asset_class": "etf", "region": "pl"},
]

PL_TOP_BONDS = [
    {"symbol": "ETFBNDXPL.WA", "name": "Beta ETF obligacji PL", "asset_class": "bond", "region": "pl"},
    {"symbol": "OBL.WA", "name": "Obligacje fundusz (PL)", "asset_class": "bond", "region": "pl"},
]

REGIONAL_UNIVERSE = (
    US_TOP_STOCKS
    + US_TOP_ETFS
    + US_TOP_BONDS
    + EU_TOP_STOCKS
    + EU_TOP_ETFS
    + EU_TOP_BONDS
    + ASIA_TOP_STOCKS
    + ASIA_TOP_ETFS
    + ASIA_TOP_BONDS
    + EM_TOP_STOCKS
    + EM_TOP_ETFS
    + EM_TOP_BONDS
    + PL_TOP_ETFS
    + PL_TOP_BONDS
)

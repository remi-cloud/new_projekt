"""Investing.com pair IDs for Polish market instruments (sourced from investpy resources)."""

# symbol -> investing.com pair ID
POLISH_INVESTING_IDS: dict[str, int] = {
    # Indices
    "WIG20.WA": 14602,
    "WIG.WA": 37662,
    "MWIG40.WA": 37656,
    "SWIG80.WA": 37660,
    "WIG20TR.WA": 996591,
    "WIG20LEV.WA": 49602,
    # WIG20 blue chips
    "PKO.WA": 8737,
    "PKN.WA": 8785,
    "PZU.WA": 13805,
    "PEO.WA": 8759,
    "KGH.WA": 8777,
    "DNP.WA": 1008705,
    "CDR.WA": 37756,
    "LPP.WA": 37875,
    "ALE.WA": 37970,
    "PGE.WA": 13804,
    "SAN.WA": 8733,
    "ALR.WA": 37712,
    "KRU.WA": 37865,
    "MBK.WA": 8743,
    "CPS.WA": 8813,
    "JSW.WA": 37846,
    "OPL.WA": 8747,
    "TPE.WA": 37978,
    "XTB.WA": 977696,
    "11B.WA": 50697,
    "BDX.WA": 37737,
    # ETFs
    "EPOL": 38133,
    "ETFBW20TR.WA": 1123818,
    "ETFSP500.WA": 962262,
    "ETFDAX.WA": 962261,
}

# Search queries for symbols missing a hard-coded ID (resolved at runtime, cached on disk)
POLISH_INVESTING_SEARCH: dict[str, str] = {
    "ETFBNDXPL.WA": "Beta ETF obligacji polskich",
    "OBL.WA": "OBL obligacje",
}

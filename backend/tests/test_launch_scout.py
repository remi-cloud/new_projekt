"""Launch Scout — scorer + normalize (no network)."""

from app.launch_scout.client_dexscreener import normalize_pair, normalize_profile_stub
from app.launch_scout.client_pumpfun import normalize_pump_coin
from app.launch_scout.scorer import finalize_candidate, mc_tier, score_candidate


def test_mc_tiers():
    assert mc_tier(200) == "seed"
    assert mc_tier(1_500) == "seed"
    assert mc_tier(50_000) == "fresh"
    assert mc_tier(200_000) == "early"
    assert mc_tier(800_000) == "watch"
    assert mc_tier(1_500_000) is None
    assert mc_tier(None) is None


def test_score_prefers_low_mc_and_tags():
    low = score_candidate(market_cap=20_000, age_h=2, liq_usd=5_000, tags=["pump", "fomo_bag"])
    high = score_candidate(market_cap=900_000, age_h=100, liq_usd=5_000, tags=[])
    assert low > high


def test_normalize_pair_pump_tag():
    pair = {
        "chainId": "solana",
        "dexId": "pumpswap",
        "pairAddress": "Pair111",
        "pairCreatedAt": 1_700_000_000_000,
        "marketCap": 38484,
        "liquidity": {"usd": 13000},
        "baseToken": {"address": "Mintpump", "symbol": "NESTLE", "name": "Nestlé"},
        "url": "https://dexscreener.com/solana/x",
        "priceUsd": "0.0001",
    }
    n = normalize_pair(pair)
    assert n["symbol"] == "NESTLE"
    assert "pump" in n["tags"]
    assert n["market_cap"] == 38484


def test_normalize_pump_coin():
    row = {
        "mint": "abc123pump",
        "symbol": "TIK",
        "name": "TikTok",
        "usd_market_cap": 12_345,
        "created_timestamp": 1_700_000_000,
        "complete": False,
    }
    n = normalize_pump_coin(row)
    assert n is not None
    assert n["source"] == "pump"
    assert n["chain"] == "solana"
    assert "planned_visibility" in n["tags"]


def test_finalize_candidate_filters_liq_and_mc():
    thresholds = {
        "max_mc": 1_000_000,
        "seed_mc": 2_000,
        "fresh_mc": 100_000,
        "early_mc": 500_000,
        "min_liq_usd": 1_000,
        "require_migrated": False,
        "require_dex_paid": False,
    }
    ok = finalize_candidate(
        {
            "candidate_id": "solana:m1",
            "mint": "m1",
            "symbol": "AAA",
            "chain": "solana",
            "market_cap": 40_000,
            "liq_usd": 5_000,
            "pair_created_ms": 1_700_000_000_000,
            "source": "dex",
            "tags": ["profile"],
        },
        thresholds,
    )
    assert ok is not None
    assert ok["tier"] == "fresh"

    no_liq = finalize_candidate(
        {
            "candidate_id": "solana:m2",
            "mint": "m2",
            "symbol": "BBB",
            "chain": "solana",
            "market_cap": 40_000,
            "liq_usd": 50,
            "source": "dex",
            "tags": [],
        },
        thresholds,
    )
    assert no_liq is None

    pump_ok = finalize_candidate(
        {
            "candidate_id": "solana:m3",
            "mint": "m3",
            "symbol": "CCC",
            "chain": "solana",
            "market_cap": 8_000,
            "liq_usd": None,
            "source": "pump",
            "tags": ["pump"],
        },
        thresholds,
    )
    assert pump_ok is not None
    assert pump_ok["tier"] == "fresh"

    seed_ok = finalize_candidate(
        {
            "candidate_id": "solana:m4",
            "mint": "m4",
            "symbol": "SEED",
            "chain": "solana",
            "market_cap": 200,
            "liq_usd": None,
            "source": "dex",
            "tags": [],
        },
        thresholds,
    )
    assert seed_ok is not None
    assert seed_ok["tier"] == "seed"


def test_finalize_require_migrated_and_dex_paid():
    thresholds = {
        "max_mc": 5_000_000,
        "seed_mc": 2_000,
        "fresh_mc": 100_000,
        "early_mc": 500_000,
        "min_liq_usd": 1_000,
        "require_migrated": True,
        "require_dex_paid": True,
    }
    bonding = finalize_candidate(
        {
            "mint": "0xabc",
            "symbol": "Cate",
            "chain": "bsc",
            "market_cap": 5,
            "liq_usd": None,
            "source": "4meme",
            "dex_id": "4meme",
            "pair_address": "0xabc:4meme",
            "tags": ["4meme", "bonding"],
        },
        thresholds,
    )
    assert bonding is None

    paid = finalize_candidate(
        {
            "mint": "MintCate1111111111111111111111111111111",
            "symbol": "Cate",
            "chain": "solana",
            "market_cap": 250_000,
            "liq_usd": 12_000,
            "source": "dex",
            "dex_id": "raydium",
            "pair_address": "PairCate111",
            "tags": ["dex_paid", "profile", "value_watch"],
        },
        thresholds,
    )
    assert paid is not None
    assert "migrated" in paid["tags"]


def test_sanitize_terminal_4meme_junk():
    from app.coordinator.link_guard import audit_terminal_urls
    from app.launch_scout.terminal_url import axiom_meme_url, ensure_candidate_urls, sanitize_address, terminal_url

    assert sanitize_address("0xAbC:4meme") == "0xAbC"
    sol = axiom_meme_url("Mint1111111111111111111111111111111111111111", "solana")
    assert "chain=sol" in sol
    url = terminal_url(
        mint="0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF",
        pair_address="0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF:4meme",
        chain="bsc",
        source="4meme",
    )
    assert ":4meme" not in url
    assert "axiom.trade/meme/" in url
    assert "chain=bnb" in url
    c = ensure_candidate_urls(
        {
            "mint": "0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF",
            "pair_address": "0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF:4meme",
            "chain": "bsc",
            "source": "4meme",
            "tags": ["4meme", "bonding"],
            "symbol": "X",
        }
    )
    assert c["pair_address"] == ""
    assert "four.meme" in c["url"]

    audit = audit_terminal_urls(
        [
            {
                "chain": "solana",
                "url": terminal_url(mint="DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump", chain="solana"),
            }
        ]
    )
    assert audit["ok"] is True
    assert audit["missing_chain_axiom"] == 0


def test_profile_stub():
    s = normalize_profile_stub(
        {"chainId": "robinhood", "tokenAddress": "0xabc", "url": "https://dexscreener.com/x"},
        tag="boost",
    )
    assert s["chain"] == "robinhood"
    assert "planned_visibility" in s["tags"]


def test_whisper_keywords_and_correlate():
    from app.launch_scout.whispers import correlate_whisper_tags, extract_whisper_keywords

    kws = extract_whisper_keywords("Elon just posted about $DOGE and pepe memes again")
    assert "doge" in kws
    assert "pepe" in kws
    tags = correlate_whisper_tags(
        {"symbol": "DOGE", "name": "Dogecoin"},
        [{"author": "elon", "keywords": kws, "source": "rss"}],
    )
    assert "elon_whisper" in tags


def test_score_whisper_and_gecko_bonus():
    base = score_candidate(market_cap=20_000, age_h=2, liq_usd=5_000, tags=["pump"])
    boosted = score_candidate(
        market_cap=20_000, age_h=2, liq_usd=5_000, tags=["pump", "elon_whisper", "gecko"]
    )
    assert boosted > base


def test_gecko_normalize_minimal():
    from app.launch_scout.client_geckoterminal import normalize_gecko_pool

    row = {
        "_network": "solana",
        "attributes": {
            "name": "PEPE / SOL",
            "address": "PoolAddr111",
            "fdv_usd": "45000",
            "reserve_in_usd": "12000",
            "pool_created_at": "2026-01-01T00:00:00Z",
            "dex_id": "raydium",
        },
        "relationships": {
            "base_token": {"data": {"id": "solana_MintAddressPepe111"}}
        },
    }
    n = normalize_gecko_pool(row)
    assert n is not None
    assert n["source"] == "gecko"
    assert "gecko" in n["tags"]
    assert n["market_cap"] == 45000


def test_binance_radar_keywords():
    from app.launch_scout.client_binance_radar import extract_keywords

    k = extract_keywords("Binance Alpha lists $PNUT memecoin today")
    assert "pnut" in k
    assert "listing" in k or "alpha" in k


def test_seed_and_pump_trader_score_bonus():
    base = score_candidate(market_cap=500, age_h=1, liq_usd=0, tags=["pump"])
    tagged = score_candidate(market_cap=500, age_h=1, liq_usd=0, tags=["pump", "pump_trader"])
    late = score_candidate(market_cap=900_000, age_h=1, liq_usd=50_000, tags=[])
    assert tagged > base
    assert base > late


def test_normalize_4meme_and_bnb_tags():
    from app.launch_scout.client_4meme import normalize_4meme_token
    from app.launch_scout.client_bnb import normalize_bnb_pair

    bonding_row = {
        "tokenAddress": "0xabcabcabcabcabcabcabcabcabcabcabcabcabca",
        "shortName": "CTD",
        "name": "Claim The Dog",
        "cap": "200",
        "price": "0.0001",
        "img": "/market/x.png",
        "status": "PUBLISH",
        "createDate": "1700000000000",
        "dexType": 0,
    }
    assert normalize_4meme_token(bonding_row) is None

    row = {
        "tokenAddress": "0xabcabcabcabcabcabcabcabcabcabcabcabcabca",
        "shortName": "CTD",
        "name": "Claim The Dog",
        "cap": "200",
        "price": "0.0001",
        "img": "/market/x.png",
        "status": "TRADE",
        "createDate": "1700000000000",
        "dexType": 1,
    }
    n = normalize_4meme_token(row)
    assert n is not None
    assert n["chain"] == "bsc"
    assert n["source"] == "4meme"
    assert "4meme" in n["tags"]
    assert "migrated" in n["tags"]
    assert n["image_url"].startswith("https://static.four.meme/")
    assert n["market_cap"] == 200.0

    pair = {
        "chainId": "bsc",
        "dexId": "flapsh",
        "pairAddress": "0xpair",
        "marketCap": 500,
        "liquidity": {"usd": 0},
        "baseToken": {"address": "0xtoken", "symbol": "FLAPX", "name": "Flap X"},
        "info": {"imageUrl": "https://cdn.example/icon.png"},
        "url": "https://dexscreener.com/bsc/x",
        "priceUsd": "0.01",
    }
    f = normalize_bnb_pair(pair, kind="flap")
    assert f["source"] == "flap"
    assert "flap" in f["tags"]
    assert f["image_url"] == "https://cdn.example/icon.png"

    thresholds = {
        "max_mc": 1_000_000,
        "seed_mc": 2_000,
        "fresh_mc": 100_000,
        "early_mc": 500_000,
        "min_liq_usd": 1_000,
        "require_migrated": False,
        "require_dex_paid": False,
    }
    done = finalize_candidate(
        {
            "candidate_id": "bsc:0xtoken",
            "mint": "0xtoken",
            "symbol": "FLAPX",
            "chain": "bsc",
            "market_cap": 500,
            "liq_usd": None,
            "source": "flap",
            "tags": ["flap", "bonding"],
        },
        thresholds,
    )
    assert done is not None
    assert done["tier"] == "seed"


def test_coin_image_resolver():
    from app.paper.coin_image import resolve_coin_image_url

    btc = resolve_coin_image_url("BTC-USD", "crypto")
    assert btc and "btc.png" in btc
    assert resolve_coin_image_url("AAPL", "stock") is None


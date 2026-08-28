from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Full analysis scan (52w stats + signals)
    scan_interval_minutes: int = 5
    # Lightweight price refresh (batch quotes) — co minutę
    price_poll_interval_seconds: int = 60

    database_path: str = "data/trader.db"
    portfolio_database_path: str = "data/baza_portfela/portfolio.db"
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    btc_bear_phase_days: int = 364
    btc_bull_phase_days: int = 1064

    presidential_terms: list[dict] = [
        {"start": "2009-01-20", "end": "2013-01-20", "president": "Obama I"},
        {"start": "2013-01-20", "end": "2017-01-20", "president": "Obama II"},
        {"start": "2017-01-20", "end": "2021-01-20", "president": "Trump I"},
        {"start": "2021-01-20", "end": "2025-01-20", "president": "Biden"},
        {"start": "2025-01-20", "end": "2029-01-20", "president": "Trump II"},
    ]

    # Notifications
    notifications_enabled: bool = True
    alert_min_confidence: float = 60.0
    alert_cooldown_minutes: int = 30

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:alerts@cyclical-trader.local"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    alert_phone_number: str = ""

    # Macro news — live wire only (no curated desk essays in feed)
    news_fresh_hours: int = 2
    news_display_max_hours: int = 1
    news_article_max_age_days: int = 1
    news_poll_interval_seconds: int = 60
    news_refresh_interval_seconds: int = 60
    news_alert_cooldown_minutes: int = 30
    news_images_enabled: bool = True
    news_images_use_dalle: bool = True
    news_images_max_per_refresh: int = 25
    news_max_per_source: int = 3
    news_musk_max_per_source: int = 6
    news_usa_max_per_source: int = 5
    news_crypto_max_per_source: int = 4
    news_feed_limit: int = 72
    news_musk_feed_slots: int = 12
    news_usa_feed_slots: int = 10
    news_crypto_feed_slots: int = 8
    news_ideology_boost: bool = False
    news_pool_limit: int = 360
    news_calendar_ai_enabled: bool = True
    pexels_api_key: str = ""

    # AI Finance Agent
    # provider: auto (OpenAI if key set, else free LLM7) | openai | llm7 | ollama
    ai_enabled: bool = True
    ai_provider: str = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_image_model: str = "dall-e-3"
    openai_image_size: str = "1792x1024"
    openai_image_quality: str = "standard"
    openai_base_url: str = "https://api.openai.com/v1"
    # Free keyless OpenAI-compatible gateway (no signup / no key)
    free_llm_base_url: str = "https://api.llm7.io/v1"
    free_llm_model: str = "codestral-latest"
    free_llm_fallback_models: str = "meta-Llama-3.1-8B-Instruct-Turbo,minimax-m2.7"
    # Local Ollama (optional): brew install ollama && ollama pull llama3.2
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "llama3.2"
    ai_temperature: float = 0.35
    ai_timeout_seconds: int = 90
    ai_max_history_messages: int = 20
    ai_self_critique_enabled: bool = True
    ai_self_learn_enabled: bool = True
    # Best practical loop: frequent distill + learn after news + inject more lessons
    ai_self_learn_interval_minutes: int = 15
    ai_self_learn_max_lessons: int = 5
    ai_self_learn_on_news_refresh: bool = True
    ai_learning_inject_limit: int = 8
    ai_learn_from_news_chat: bool = True

    # Pearl hunters (global opportunities outside core universe)
    pearl_hunter_enabled: bool = True
    pearl_equity_interval_minutes: int = 20
    pearl_crypto_interval_minutes: int = 15
    pearl_equity_candidates: int = 36
    pearl_min_score: float = 55.0
    pearl_max_store_per_run: int = 15

    # Auto-save progress to backups/progress every N seconds
    auto_backup_enabled: bool = True
    auto_backup_interval_seconds: int = 20
    auto_backup_rotate_every: int = 15
    auto_backup_keep: int = 2

    # Frontend / API hint: optional UI auto-refresh interval (seconds); 0 = off
    ui_auto_refresh_seconds: int = 20

    # Broker execution agent
    execution_enabled: bool = False
    execution_dry_run: bool = True
    execution_mirror_paper: bool = False
    execution_require_approval: bool = True
    execution_min_confidence: float = 70.0
    execution_amount_pln: float = 10_000.0
    execution_max_daily: int = 5
    execution_cooldown_hours: int = 24
    execution_tick_minutes: int = 10
    execution_broker_crypto: str = "kraken"
    execution_broker_equity: str = "ibkr"
    execution_broker_equity_fallback: str = "etoro"

    # Broker API credentials (empty = stub / dry-run only)
    ibkr_gateway_url: str = ""
    ibkr_account: str = ""
    etoro_api_key: str = ""
    kraken_api_key: str = ""
    kraken_api_secret: str = ""
    binance_api_key: str = ""
    binance_api_secret: str = ""
    nexo_api_key: str = ""
    nexo_api_secret: str = ""

    # Paper portfolio — never auto-restore demo/test positions from backup or legacy DB
    portfolio_restore_backup: bool = False
    portfolio_migrate_legacy: bool = False

    # Social desk — news → X / LinkedIn (dry-run by default)
    social_enabled: bool = True
    social_dry_run: bool = True
    social_auto_post: bool = False
    social_cooldown_minutes: int = 60
    social_max_per_cycle: int = 2
    public_base_url: str = ""
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_author_urn: str = ""

    # Telegram Predator relay (FREE via BotFather — forward Predator posts to your channel)
    telegram_predator_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_predator_chat_id: str = ""  # optional filter; empty = all chats bot can see
    telegram_predator_notify: bool = True
    telegram_predator_interval_seconds: int = 60

    # FOMO Ghost — Cope Capital (fomo.family top portfolios → bag activity)
    fomo_enabled: bool = True
    cope_api_key: str = ""  # CYCLICAL_COPE_API_KEY (also accepts COPE_API_KEY via client fallback)
    fomo_interval_seconds: int = 60
    fomo_top_n: int = 30
    fomo_leaderboard_timeframe: str = "7d"
    # FOMO Telegram listener (same BotFather token as Predator; forward Family channels)
    fomo_telegram_enabled: bool = True
    fomo_telegram_chat_ids: str = ""  # comma-separated chat ids; empty = heuristic FOMO text only

    # Axiom desk — Pulse + all positions (FOMO Family bags + optional wallets)
    axiom_enabled: bool = True
    axiom_interval_seconds: int = 90
    axiom_trending_period: str = "1h"
    axiom_include_closed: bool = True
    axiom_access_token: str = ""  # browser cookie auth-access-token (optional)
    axiom_refresh_token: str = ""  # browser cookie auth-refresh-token (optional)
    axiom_wallets: str = ""  # comma-separated Solana wallets → all SPL positions via RPC
    # Firm Solana wallet for Kar Digital desk (merged into Axiom positions as owner_kind=kar_digital)
    kar_digital_wallet: str = ""

    # Launch Scout / Meme Universe — Seed (~$200) + multi-DEX + trader tracking
    launch_scout_enabled: bool = True
    launch_scout_interval_seconds: int = 60
    launch_scout_max_mc: float = 5_000_000  # allow valuable migrated memes (was 1M — skipped cate/cash etc.)
    launch_scout_seed_mc: float = 2_000
    launch_scout_fresh_mc: float = 100_000
    launch_scout_early_mc: float = 500_000
    launch_scout_min_liq_usd: float = 1_000
    # Only post-migration DEX pairs with DexScreener paid visibility (boost/profile)
    launch_scout_require_migrated: bool = True
    launch_scout_require_dex_paid: bool = True
    launch_scout_value_tickers: str = "memestock,cate,cash,cat,xst,calas,pepe,bonk,wif"
    launch_scout_chains: str = (
        "solana,base,ethereum,bsc,arbitrum,polygon,avalanche,optimism,blast,tron,sui,bitcoin,robinhood"
    )
    wallet_scout_top_n: int = 15  # RPC holdings for top Pump wallets (Wallet Scout P0)
    dex_arena_enabled: bool = True
    dex_arena_top_n: int = 8
    dex_arena_lanes: str = "pumpfun,raydium,pancakeswap,flap,4meme,other"
    session_clock_enabled: bool = True
    session_clock_lookback_days: int = 14
    meme_whispers_enabled: bool = True
    meme_whispers_x_enabled: bool = True
    solana_tracker_api_key: str = ""  # optional CYCLICAL_SOLANA_TRACKER_API_KEY for Pump PnL board

    coordinator_interval_seconds: int = 300
    binance_ai_bot_url: str = ""
    binance_ai_bot_key: str = ""
    binance_ai_bot_enabled: bool = True
    binance_ai_bot_interval_seconds: int = 120
    binance_ai_bot_dry_run: bool = True
    binance_ai_bot_mirror_paper: bool = True
    binance_drift_alert_pct: float = 15.0

    class Config:
        env_prefix = "CYCLICAL_"


settings = Settings()

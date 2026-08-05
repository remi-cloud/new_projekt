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

    # Macro news — only breaking / very fresh ("nowinki")
    news_fresh_hours: int = 4
    news_display_max_hours: int = 2
    news_article_max_age_days: int = 2
    news_poll_interval_seconds: int = 120
    news_refresh_interval_seconds: int = 120
    news_alert_cooldown_minutes: int = 30
    news_images_enabled: bool = True
    news_images_use_dalle: bool = True
    news_images_max_per_refresh: int = 25
    news_max_per_source: int = 3
    news_musk_max_per_source: int = 6
    news_usa_max_per_source: int = 5
    news_feed_limit: int = 60
    news_musk_feed_slots: int = 12
    news_usa_feed_slots: int = 10
    news_ideology_boost: bool = True
    news_pool_limit: int = 300
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

    class Config:
        env_prefix = "CYCLICAL_"


settings = Settings()

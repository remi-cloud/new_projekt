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

    # Macro news
    news_fresh_hours: int = 12
    news_display_max_hours: int = 6
    news_poll_interval_seconds: int = 120
    news_refresh_interval_seconds: int = 120
    news_alert_cooldown_minutes: int = 30
    news_images_enabled: bool = True
    news_images_use_dalle: bool = True
    news_images_max_per_refresh: int = 25
    news_max_per_source: int = 4
    news_musk_max_per_source: int = 8
    news_feed_limit: int = 100
    news_musk_feed_slots: int = 15
    news_pool_limit: int = 600
    pexels_api_key: str = ""

    # AI Finance Agent
    ai_enabled: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_image_model: str = "dall-e-3"
    openai_image_size: str = "1792x1024"
    openai_image_quality: str = "standard"
    openai_base_url: str = "https://api.openai.com/v1"
    ai_temperature: float = 0.35
    ai_timeout_seconds: int = 90
    ai_max_history_messages: int = 20
    ai_self_critique_enabled: bool = True

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

    class Config:
        env_prefix = "CYCLICAL_"


settings = Settings()

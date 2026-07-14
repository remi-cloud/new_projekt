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

    class Config:
        env_prefix = "CYCLICAL_"


settings = Settings()

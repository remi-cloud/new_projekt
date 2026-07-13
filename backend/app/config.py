from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    scan_interval_minutes: int = 15
    database_path: str = "data/trader.db"
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    # Bitcoin cycle parameters (days from last ATH)
    btc_bear_phase_days: int = 364
    btc_bull_phase_days: int = 1064

    # Presidential cycle: inauguration day (Jan 20 after election year)
    # Used to compute year 1-4 of each term
    presidential_terms: list[dict] = [
        {"start": "2009-01-20", "end": "2013-01-20", "president": "Obama I"},
        {"start": "2013-01-20", "end": "2017-01-20", "president": "Obama II"},
        {"start": "2017-01-20", "end": "2021-01-20", "president": "Trump I"},
        {"start": "2021-01-20", "end": "2025-01-20", "president": "Biden"},
        {"start": "2025-01-20", "end": "2029-01-20", "president": "Trump II"},
    ]

    class Config:
        env_prefix = "CYCLICAL_"


settings = Settings()

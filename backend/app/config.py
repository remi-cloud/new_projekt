from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="CYCLICAL_")

    scan_interval_minutes: int = 15
    database_path: str = "data/trader.db"
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    # Model Alpha phase windows (days from reference)
    alpha_phase_a_days: int = 364
    alpha_phase_b_days: int = 1064

    # Optional alert defaults (can also be set in the UI / SQLite)
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    webhook_url: str = ""
    alerts_enabled: bool = False

    # Model Beta: successive 4-year scoring periods
    beta_periods: list[dict] = [
        {"start": "2009-01-20", "end": "2013-01-20"},
        {"start": "2013-01-20", "end": "2017-01-20"},
        {"start": "2017-01-20", "end": "2021-01-20"},
        {"start": "2021-01-20", "end": "2025-01-20"},
        {"start": "2025-01-20", "end": "2029-01-20"},
    ]

settings = Settings()

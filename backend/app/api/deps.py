"""Shared API helpers."""

from app.data.assets import MONITORED_ASSETS

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}

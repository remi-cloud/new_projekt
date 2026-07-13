"""Stable filesystem paths for SQLite persistence."""

from __future__ import annotations

from pathlib import Path

from app.config import settings

# backend/ — always the same regardless of process cwd
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def database_path() -> Path:
    """Absolute path to trader.db so restarts never create a fresh empty DB."""
    raw = Path(settings.database_path)
    if raw.is_absolute():
        return raw
    return (BACKEND_ROOT / raw).resolve()


def ensure_data_dir() -> Path:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

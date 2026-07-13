"""Stable filesystem paths for SQLite persistence."""

from __future__ import annotations

from pathlib import Path

from app.config import settings

# backend/ — always the same regardless of process cwd
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


def database_path() -> Path:
    """Absolute path to trader.db (alerts, opportunities)."""
    return _resolve(settings.database_path)


def portfolio_dir() -> Path:
    """Folder for paper-trading portfolio database and snapshots."""
    return _resolve(settings.portfolio_database_path).parent


def portfolio_database_path() -> Path:
    """Absolute path to portfolio.db — paper account, positions, trades."""
    return _resolve(settings.portfolio_database_path)


def portfolio_snapshot_path() -> Path:
    """JSON snapshot written by the portfolio agent."""
    return portfolio_dir() / "portfolio_snapshot.json"


def ensure_data_dir() -> Path:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_portfolio_dir() -> Path:
    folder = portfolio_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return folder

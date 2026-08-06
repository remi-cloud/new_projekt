"""Pytest bootstrap — isolate SQLite from the live baza_portfela portfolio."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# MUST run before any `app.*` import so Settings() picks up test paths.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="cyclical_pytest_"))
_PF_DIR = _TEST_ROOT / "baza_portfela"
_PF_DIR.mkdir(parents=True, exist_ok=True)

os.environ["CYCLICAL_DATABASE_PATH"] = str(_TEST_ROOT / "trader.db")
os.environ["CYCLICAL_PORTFOLIO_DATABASE_PATH"] = str(_PF_DIR / "portfolio.db")
os.environ["CYCLICAL_PORTFOLIO_RESTORE_BACKUP"] = "false"
os.environ["CYCLICAL_PORTFOLIO_MIGRATE_LEGACY"] = "false"
os.environ.setdefault("CYCLICAL_PEARL_HUNTER_ENABLED", "false")
os.environ.setdefault("CYCLICAL_AUTO_BACKUP_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

# Rebuild settings if a previous import cached defaults (defensive).
from app import config as config_mod

config_mod.settings = config_mod.Settings()

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def test_data_root() -> Path:
    return _TEST_ROOT

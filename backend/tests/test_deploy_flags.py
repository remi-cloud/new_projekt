"""Deploy config must use the settings prefix the app actually reads."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_binance_dry_run_flag_is_prefixed():
    compose = _text("docker-compose.yml")
    render = _text("render.yaml")
    dead = re.compile(r"(?<!CYCLICAL_)BINANCE_AI_BOT_DRY_RUN")
    assert dead.search(compose) is None
    assert dead.search(render) is None
    assert "CYCLICAL_BINANCE_AI_BOT_DRY_RUN" in compose
    assert re.search(
        r"CYCLICAL_BINANCE_AI_BOT_DRY_RUN:\s*\"\$\{CYCLICAL_BINANCE_AI_BOT_DRY_RUN:-true\}\"",
        compose,
    )
    assert re.search(
        r"-\s+key:\s+CYCLICAL_BINANCE_AI_BOT_DRY_RUN\s+value:\s+\"true\"",
        render,
    )

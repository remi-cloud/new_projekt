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


def test_auto_post_stays_on_unless_the_domain_gate_says_otherwise():
    docker = _text("Dockerfile")
    render = _text("render.yaml")
    assert "CYCLICAL_SOCIAL_AUTO_POST=false" not in docker
    assert re.search(r"key:\s+CYCLICAL_SOCIAL_AUTO_POST\s+value:\s+\"true\"", render)
    refresh = _text("backend/app/api/news.py").split("async def macro_news_refresh", 1)[1]
    refresh = refresh.split("async def news_outbound", 1)[0]
    assert "queue_social_from_news_items" not in refresh
    assert "queue_social_from_news_items" in _text("backend/app/scheduler/jobs.py")

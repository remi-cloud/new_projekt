"""Auto-publish rules: whitelist, score threshold, 2 posts per hour, source line."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.schemas import MacroNewsItem
from app.news.social_composer import compose_x
from app.news.x_auto import (
    assert_post_has_source,
    evaluate_auto,
    is_whitelisted,
    score_item,
)


def _now() -> datetime:
    return datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)


def _decide(**kwargs):
    base = dict(
        source="Reuters",
        url="https://www.reuters.com/markets/fed-holds",
        title="Fed holds rates as inflation stays sticky",
        summary="The Federal Reserve left interest rates unchanged.",
        impact="high",
        category="fed",
        published_at=_now() - timedelta(minutes=20),
        now=_now(),
        confirming_sources=1,
        posted_last_hour=0,
        recent_topics=set(),
        min_score=70,
        max_per_hour=2,
    )
    base.update(kwargs)
    return evaluate_auto(**base)


def test_whitelist_allows_named_outlets_and_blocks_the_rest():
    assert not is_whitelisted("Reuters", "https://news.google.com/rss/articles/x")
    assert is_whitelisted("Reuters", "https://www.reuters.com/markets/fed-holds")
    assert is_whitelisted("FT · Markets", "https://www.ft.com/content/abc")
    assert not is_whitelisted("BBC Business", None)
    assert is_whitelisted("BBC Business", "https://www.bbc.co.uk/news/business-1")
    assert is_whitelisted("Federal Reserve", "https://www.federalreserve.gov/newsevents.htm")
    assert is_whitelisted("Al Jazeera", "https://www.aljazeera.com/news/story")
    assert is_whitelisted("Kyodo", "https://english.kyodonews.net/news/story")
    assert is_whitelisted("WHO", "https://www.who.int/news/item/1")
    assert not is_whitelisted("Fox News · Politics", "https://www.foxnews.com/politics/x")
    assert not is_whitelisted("ZeroHedge", "https://www.zerohedge.com/markets/x")
    assert is_whitelisted("Desk", "https://www.reuters.com/world/story")
    assert not is_whitelisted("Electrek", "https://electrek.co/2026/11/17/story")
    assert not is_whitelisted("ZeroHedge", "https://news.google.com/rss/articles/zh")
    assert not is_whitelisted("CoinDesk", "https://www.coindesk.com/markets/x")


def test_threshold_blocks_a_cold_item_and_passes_a_fresh_high_impact_one():
    cold = score_item(
        title="Markets drift",
        summary="A quiet session.",
        impact="low",
        category="global",
        published_at=_now() - timedelta(hours=8),
        now=_now(),
        confirming_sources=1,
    )
    hot = score_item(
        title="Fed holds rates",
        summary="Federal Reserve interest rate decision.",
        impact="high",
        category="fed",
        published_at=_now() - timedelta(minutes=15),
        now=_now(),
        confirming_sources=2,
    )
    assert cold < 70
    assert hot >= 70
    assert _decide().action == "publish"
    rejected = _decide(impact="low", category="global", title="Markets drift", summary="Quiet.")
    assert rejected.action == "reject"
    assert "progu" in rejected.reason


def test_two_per_hour_and_duplicate_topic_reject():
    blocked = _decide(posted_last_hour=2)
    assert blocked.action == "reject"
    assert "godzinę" in blocked.reason
    duplicate = _decide(recent_topics={_decide().topic})
    assert duplicate.action == "reject"
    assert duplicate.reason == "duplikat tematu"


def test_global_hot_topic_adds_weight_without_matching_warning():
    cold_kwargs = dict(
        impact="low",
        category="global",
        published_at=_now() - timedelta(hours=8),
        now=_now(),
        confirming_sources=1,
    )
    war = score_item(
        title="Missile strike widens the war",
        summary="Sanctions follow the election.",
        **cold_kwargs,
    )
    warning = score_item(
        title="Weather warning issued",
        summary="A quiet advisory.",
        **cold_kwargs,
    )
    assert war - warning == 20


def test_unconfirmed_single_source_is_rejected():
    decision = _decide(title="Fed holds rates, sources say, unconfirmed")
    assert decision.action == "reject"
    assert "niepotwierdzone" in decision.reason


@pytest.mark.asyncio
async def test_auto_unwraps_google_news_to_publisher_host():
    from unittest.mock import patch

    from app.models.schemas import MacroNewsItem
    from app.news.social_db import init_social_db, list_decisions
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    item = MacroNewsItem(
        id="unwrap-reuters-1",
        title="Fed holds rates as inflation stays sticky",
        summary="The Federal Reserve left interest rates unchanged.",
        url="https://news.google.com/rss/articles/CBMiTestUnwrap",
        source="Reuters",
        category="fed",
        impact="high",
        published_at=_now(),
    )

    async def _unwrap(url, title=""):
        return "https://www.reuters.com/world/fed-holds"

    with (
        patch.object(sd, "ensure_clickable_url", new=_unwrap),
        patch.object(sd, "x_configured", return_value=False),
    ):
        await sd.run_auto_x([item])
    rows = await list_decisions(10)
    mine = [row for row in rows if row["news_id"] == "unwrap-reuters-1"]
    assert mine
    assert mine[0]["action"] == "odrzucono"
    assert "tokenów" in mine[0]["reason"]


def test_outside_whitelist_never_publishes():
    decision = _decide(source="Electrek", url="https://electrek.co/story")
    assert decision.action == "reject"
    assert decision.reason == "poza białą listą źródeł"


def test_compose_x_includes_source_name_and_article_url():
    item = MacroNewsItem(
        id="n1",
        title="Fed holds rates",
        summary="Decision in Oslo at 14:00 CET rattled Norway.",
        url="https://www.reuters.com/markets/fed-holds",
        source="Reuters",
        category="fed",
        impact="high",
        published_at=_now(),
    )
    body = compose_x(item).body
    assert "Źródło: Reuters" in body
    assert "https://www.reuters.com/markets/fed-holds" in body
    assert "— @robi44610 | Kar Digital" in body
    assert len(body) <= 500
    lowered = body.lower()
    assert "oslo" not in lowered
    assert "norway" not in lowered
    assert "cet" not in lowered
    assert_post_has_source(body, "Reuters", item.url)


@pytest.mark.asyncio
async def test_hourly_limit_is_counted_from_the_database():
    from app.news.social_db import count_posted_since, init_social_db, insert_post

    await init_social_db()
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=1)).isoformat()
    for index in range(2):
        await insert_post(
            platform="x",
            news_id=f"hour-{now.timestamp()}-{index}",
            url=f"https://www.reuters.com/hour-{index}-{now.timestamp()}",
            title="Fed holds rates",
            body="Źródło: Reuters\nhttps://www.reuters.com/hour",
            media_path=None,
            status="posted",
            posted_at=now.isoformat(),
            source_name="Reuters",
        )
    posted = await count_posted_since("x", since)
    decision = _decide(posted_last_hour=posted)
    assert posted >= 2
    assert decision.action == "reject"
    assert "godzinę" in decision.reason


def test_publish_blocked_without_source_line():
    with pytest.raises(RuntimeError, match="źródła"):
        assert_post_has_source("Fed holds rates", "Reuters", "https://www.reuters.com/a")
    with pytest.raises(RuntimeError, match="linku"):
        assert_post_has_source(
            "Źródło: Reuters\n— @robi44610 | Kar Digital",
            "Reuters",
            "",
        )
    with pytest.raises(RuntimeError, match="robi44610"):
        assert_post_has_source(
            "Źródło: Reuters\nhttps://www.reuters.com/a",
            "Reuters",
            "https://www.reuters.com/a",
        )

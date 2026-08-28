from datetime import datetime, timezone

from app.models.schemas import MacroNewsItem
from app.news.ideology_lens import alignment_score, curated_desk_briefings, sort_by_alignment
from app.news.macro_news import _dedupe_by_title, _title_fingerprint


def _item(title: str, category: str = "macro", **kwargs) -> MacroNewsItem:
    return MacroNewsItem(
        id=title[:16],
        title=title,
        summary=kwargs.get("summary"),
        source=kwargs.get("source", "Test"),
        category=category,  # type: ignore[arg-type]
        impact=kwargs.get("impact", "medium"),
        published_at=kwargs.get("published_at", datetime.now(timezone.utc)),
        is_curated=kwargs.get("is_curated", False),
        age_minutes=0,
    )


def test_supportive_trump_beats_scandal():
    good = _item("Trump energy dominance and deregulation push", "usa")
    bad = _item("Trump indicted again in new scandal", "usa")
    assert alignment_score(good) > alignment_score(bad)


def test_stagflation_and_musk_boost():
    stag = _item("Stagflation risk as sticky inflation meets slow growth", "macro")
    musk = _item("Elon Musk Robotaxi and DOGE spending cuts", "musk")
    plain = _item("European PMI mixed in quiet session", "global")
    ranked = sort_by_alignment([plain, stag, musk])
    assert ranked[0] in (stag, musk)
    assert plain in ranked[-1:]


def test_curated_desk_briefings_still_exist_but_not_for_feed():
    """Briefings helper remains for tests / optional narracja — live feed must not inject them."""
    briefs = curated_desk_briefings()
    assert len(briefs) == 3
    assert all(b.is_curated for b in briefs)
    assert all(b.id.startswith("desk-ideology-") for b in briefs)
    assert {b.category for b in briefs} == {"usa", "musk", "macro"}


def test_title_fingerprint_dedupe():
    a = _item("10% of Cathie Wood’s Portfolio Is Invested in Elon Musk-Led Companies")
    b = _item("10% of Cathie Wood's Portfolio Is Invested in Elon Musk-Led Companies!")
    assert _title_fingerprint(a.title) == _title_fingerprint(b.title)
    older = a.model_copy(update={"published_at": datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc)})
    newer = b.model_copy(update={"published_at": datetime(2026, 8, 27, 7, 0, tzinfo=timezone.utc)})
    out = _dedupe_by_title([older, newer])
    assert len(out) == 1
    assert out[0].published_at == newer.published_at

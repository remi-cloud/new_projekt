"""Desk lens: prefer Trump / Musk aligned market narratives + stagflation frame.

Used for RSS ranking and curated briefings — not fabricated publisher articles.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.models.schemas import MacroNewsItem

# Supportive / ideology-aligned market framing (boost)
_SUPPORT_PATTERNS: tuple[str, ...] = (
    r"america first",
    r"deregulat",
    r"energy dominance",
    r"\bdrill(ing)?\b",
    r"border security",
    r"\bdoge\b",
    r"government efficiency",
    r"department of government efficiency",
    r"free speech",
    r"\brobotaxi\b",
    r"\boptimus\b",
    r"\bstarship\b",
    r"\bstarlink\b",
    r"full self.?driving",
    r"tariff.*(deal|negotiat|leverage|reciproc)",
    r"reciprocal tariff",
    r"peace through strength",
    r"reshoring",
    r"onshoring",
    r"manufacturing renaissance",
    r"secure the border",
    r"tax cut",
    r"lower taxes",
    r"fiscal discipline",
    r"spending cut",
    r"deficit cut",
    r"gold standard",  # rare but aligned fringe macro talk
    r"sound money",
    r"stagflation.*(fed|energy|spend|tariff)",
    r"(fed|powell).*(too (late|easy|loose)|behind)",
    r"musk.*(trump|white house|doge)",
    r"trump.*(musk|economy|growth|win|deal)",
)

# Hostile / scandal framing — soft demote in ranking only
_DEMOTE_PATTERNS: tuple[str, ...] = (
    r"\bindict",
    r"\bimpeach",
    r"\bfelony\b",
    r"\bconvicted\b",
    r"\bfascis",
    r"\bdictator\b",
    r"\bnazi\b",
    r"hitler",
    r"burn america",
    r"coming back to burn",
    r"doge.*(disaster|fail|chaos|burn|backfire)",
    r"(disaster|catastrophe|ruin|backfire).*(trump|musk|doge)",
    r"(trump|musk|doge).*(disaster|catastrophe|ruin|backfire)",
    r"musk.*(harass|racist|nazi|apartheid)",
    r"tesla.*(plunge|crash|recall|fire|deaths?)\b",
    r"trump.*(indict|convict|impeach|felon|scandal)",
    r"elon.*(crash|plunge|meltdown|lawsuit)",
)

_STAGFLATION_PATTERNS: tuple[str, ...] = (
    r"stagflation",
    r"stagflacj",
    r"cost.?of.?living",
    r"sticky inflation",
    r"slow.?growth.*(inflat|cpi)",
    r"inflat.*(slow.?growth|recession|stagn)",
    r"energy.?driven.?inflat",
)

_compiled_support = [re.compile(p, re.I) for p in _SUPPORT_PATTERNS]
_compiled_demote = [re.compile(p, re.I) for p in _DEMOTE_PATTERNS]
_compiled_stagflation = [re.compile(p, re.I) for p in _STAGFLATION_PATTERNS]


def _blob(item: MacroNewsItem) -> str:
    return f"{item.title} {item.summary or ''}".lower()


def alignment_score(item: MacroNewsItem) -> float:
    """Higher = more desk-preferred for Trump/Musk / stagflation lens."""
    text = _blob(item)
    score = 0.0

    if item.category in ("musk", "usa"):
        score += 2.0
    if item.is_curated:
        score += 3.0
    if item.impact == "high":
        score += 0.5

    for pat in _compiled_support:
        if pat.search(text):
            score += 1.5
    for pat in _compiled_stagflation:
        if pat.search(text):
            score += 2.0
    for pat in _compiled_demote:
        if pat.search(text):
            score -= 3.0

    # Prefer fresher items slightly when scores tie later
    age = item.age_minutes if item.age_minutes is not None else 0
    score -= min(age, 360) / 360.0
    return score


def is_stagflation_item(item: MacroNewsItem) -> bool:
    return any(p.search(_blob(item)) for p in _compiled_stagflation)


def sort_by_alignment(items: list[MacroNewsItem]) -> list[MacroNewsItem]:
    return sorted(
        items,
        key=lambda n: (alignment_score(n), n.published_at),
        reverse=True,
    )


def curated_desk_briefings(now: datetime | None = None) -> list[MacroNewsItem]:
    """Short desk notes: Trump/Musk growth + stagflation supply-side frame."""
    from urllib.parse import quote_plus

    ref = now or datetime.now(timezone.utc)
    briefs: list[tuple[str, str, str, str, str]] = [
        (
            "usa",
            "Desk · Trump · wzrost",
            "Desk: Trump — cła jako dźwignia, energia i deregulacja vs stagflacja",
            "Narracja desk: stagflacja (słaby wzrost + lepka inflacja) łagodzi się "
            "przez dominację energetyczną, cięcia regulacji i dyscyplinę fiskalną — "
            "nie przez luźną politykę Fed. Śledź cła, DOGE i komunikaty Białego Domu.",
            "Trump tariffs energy deregulation stagflation",
        ),
        (
            "musk",
            "Desk · Musk · podaż",
            "Desk: Musk — Tesla / SpaceX / xAI jako podażowa odpowiedź na stagflację",
            "Narracja desk: produktywność (Robotaxi, Optimus, Starlink, xAI) to "
            "strona podażowa przeciwko stagflacji. DOGE + cięcia wydatków = mniej "
            "presji fiskalnej; Elon × administracja USA = sygnał pro-growth dla rynku.",
            "Elon Musk Tesla SpaceX DOGE Robotaxi",
        ),
        (
            "macro",
            "Desk · Stagflacja",
            "Desk: Stagflacja — Fed spóźniony, energia i wydatki trzymają CPI w górze",
            "Ramka zgodna z linią Trump/Musk: stagflacja to efekt drogiego pieniądza "
            "po erze luzowania + kosztownej energii i rozdętych wydatków. "
            "Obserwuj CPI/PPI, ropę, rentowności i retorykę cięć vs stopy.",
            "stagflation Fed CPI energy spending Trump",
        ),
    ]

    items: list[MacroNewsItem] = []
    for i, (category, source, title, summary, query) in enumerate(briefs):
        items.append(
            MacroNewsItem(
                id=f"desk-ideology-{category}-{ref.strftime('%Y%m%d')}-{i}",
                title=title,
                summary=summary,
                url=(
                    "https://news.google.com/search?q="
                    f"{quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
                ),
                source=source,
                category=category,  # type: ignore[arg-type]
                impact="high",
                published_at=ref,
                is_curated=True,
                age_minutes=0,
            )
        )
    return items

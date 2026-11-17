"""Rules for automatic X posts. Pure checks — no network, no secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.news.x_publish_whitelist import OFFICIAL_LABELS, SOURCE_LABELS, URL_HOSTS

# X Premium allows much more. Keep posts short enough to read.
X_MAX_CHARS = 500

_UNCONFIRMED = re.compile(
    r"\b(unconfirmed|unnamed|anonymous|sources say|reportedly|"
    r"niepotwierdz\w*|anonimow\w*|niesprawdzon\w*)\b",
    re.IGNORECASE,
)
_FORBIDDEN_PLACE = re.compile(
    r"\b(oslo|norway|norwegia|norwegii|cet|cest|europe/oslo)\b",
    re.IGNORECASE,
)
_TOPIC_STOP = frozenset(
    {
        "the", "and", "for", "with", "from", "that", "this", "after", "before",
        "over", "into", "says", "said", "will", "have", "has", "its", "are",
        "was", "were", "ale", "oraz", "dla", "przy", "przez",
    }
)
_WEIGHT_WORDS = (
    "fomc", "federal reserve", "interest rate", "rate cut", "rate hike",
    "cpi", "inflation", "recession", "default", "sanction", "opec",
    "ecb", "gdp", "payroll", "ceasefire", "tariff",
)


@dataclass(frozen=True)
class AutoDecision:
    action: str  # publish | reject
    reason: str
    score: int
    topic: str


def strip_forbidden_place(text: str | None) -> str:
    """Drop Oslo / Norway / CET. Posts do not carry that clock or place."""
    if not text:
        return ""
    cleaned = _FORBIDDEN_PLACE.sub("", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip(" ,;-")


def topic_key(title: str) -> str:
    words = re.findall(r"[a-z0-9]{3,}", strip_forbidden_place(title).lower())
    tokens = [word for word in words if word not in _TOPIC_STOP][:6]
    return " ".join(sorted(tokens))


def _host(url: str | None) -> str:
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_whitelisted(source: str | None, url: str | None) -> bool:
    label = (source or "").lower().strip()
    if label in {"pap", "afp", "ap", "bbc", "ft", "reuters"}:
        return True
    if any(token in label for token in SOURCE_LABELS):
        return True
    if any(token in label for token in OFFICIAL_LABELS):
        return True
    host = _host(url)
    if not host or host.endswith("news.google.com") or host == "news.google.com":
        return False
    return any(host == allowed or host.endswith("." + allowed) for allowed in URL_HOSTS)


def is_unconfirmed(title: str, summary: str | None) -> bool:
    blob = f"{title} {summary or ''}"
    return _UNCONFIRMED.search(blob) is not None


def score_item(
    *,
    title: str,
    summary: str | None,
    impact: str,
    category: str,
    published_at: datetime,
    now: datetime,
    confirming_sources: int,
) -> int:
    """0–100. Freshness, independent confirmations, topic weight."""
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age_min = max(0, (now - published_at).total_seconds() / 60)
    if age_min <= 60:
        fresh = 40
    elif age_min <= 180:
        fresh = 25
    elif age_min <= 360:
        fresh = 10
    else:
        fresh = 0
    confirms = min(3, max(0, confirming_sources)) * 15
    blob = f"{title} {summary or ''}".lower()
    weight = 20 if any(word in blob for word in _WEIGHT_WORDS) else 0
    if (impact or "").lower() == "high":
        weight += 25
    if category in {"fed", "macro"}:
        weight += 10
    return min(100, fresh + confirms + weight)


def evaluate_auto(
    *,
    source: str | None,
    url: str | None,
    title: str,
    summary: str | None,
    impact: str,
    category: str,
    published_at: datetime,
    now: datetime,
    confirming_sources: int,
    posted_last_hour: int,
    recent_topics: set[str],
    min_score: int,
    max_per_hour: int,
) -> AutoDecision:
    topic = topic_key(title)
    if not is_whitelisted(source, url):
        return AutoDecision("reject", "poza białą listą źródeł", 0, topic)
    if is_unconfirmed(title, summary):
        return AutoDecision(
            "reject",
            "niepotwierdzone lub anonimowe źródło bez oznaczenia",
            0,
            topic,
        )
    if not url or not url.startswith("http"):
        return AutoDecision("reject", "brak linku do oryginalnego artykułu", 0, topic)
    if topic and topic in recent_topics:
        return AutoDecision("reject", "duplikat tematu", 0, topic)
    if posted_last_hour >= max_per_hour:
        return AutoDecision("reject", f"limit {max_per_hour} postów na godzinę", 0, topic)
    score = score_item(
        title=title,
        summary=summary,
        impact=impact,
        category=category,
        published_at=published_at,
        now=now,
        confirming_sources=confirming_sources,
    )
    if score < min_score:
        return AutoDecision("reject", f"poniżej progu {min_score} (wynik {score})", score, topic)
    return AutoDecision("publish", f"próg spełniony (wynik {score})", score, topic)


def assert_post_has_source(body: str, source_name: str | None, source_url: str | None) -> None:
    """Refuse to publish when the body lacks the outlet name or the article URL."""
    name = (source_name or "").strip()
    url = (source_url or "").strip()
    text = body or ""
    lowered = text.lower()
    if not name:
        raise RuntimeError("Brak nazwy źródła")
    if not url.startswith("http"):
        raise RuntimeError("Brak linku do oryginalnego artykułu")
    if "źródło:" not in lowered and "source:" not in lowered:
        raise RuntimeError("Treść nie zawiera oznaczenia źródła")
    if name.lower() not in lowered:
        raise RuntimeError("Treść nie zawiera nazwy źródła")
    if url not in text:
        raise RuntimeError("Treść nie zawiera linku do artykułu")


def x_status_url(external_id: str | None) -> str | None:
    if not external_id:
        return None
    return f"https://x.com/i/status/{external_id}"

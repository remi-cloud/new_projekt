"""Compose X / LinkedIn post copy from macro news items."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings
from app.models.schemas import MacroNewsItem


DISCLAIMER_PL = "Edukacja rynkowa · nie porada inwestycyjna · KAR Digital"
DISCLAIMER_EN = "Market education · not investment advice · KAR Digital"


@dataclass(frozen=True)
class ComposedPost:
    platform: str
    body: str
    title: str


def _clean(text: str | None, limit: int) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= limit:
        return t
    return t[: max(0, limit - 1)].rstrip() + "…"


def _footer_link(item: MacroNewsItem) -> str:
    base = (settings.public_base_url or "").rstrip("/")
    if base:
        return f"{base}/news"
    if item.url:
        return item.url
    return ""


def compose_x(item: MacroNewsItem, locale: str = "pl") -> ComposedPost:
    disc = DISCLAIMER_PL if locale.startswith("pl") else DISCLAIMER_EN
    title = _clean(item.title, 120)
    summary = _clean(item.summary, 100)
    link = _footer_link(item)
    parts = [f"📰 {title}"]
    if summary and summary.lower() not in title.lower():
        parts.append(summary)
    parts.append(f"#{item.category.upper()} · {disc}")
    if link:
        parts.append(link)
    body = "\n".join(parts)
    if len(body) > 280:
        # Trim summary first
        budget = 280 - len(f"📰 {title}\n#{item.category.upper()} · {disc}\n{link}") - 2
        summary = _clean(item.summary, max(40, budget))
        parts = [f"📰 {title}"]
        if summary:
            parts.append(summary)
        parts.append(f"#{item.category.upper()} · {disc}")
        if link:
            parts.append(link)
        body = "\n".join(parts)[:280]
    return ComposedPost(platform="x", body=body, title=title)


def compose_linkedin(item: MacroNewsItem, locale: str = "pl") -> ComposedPost:
    disc = DISCLAIMER_PL if locale.startswith("pl") else DISCLAIMER_EN
    title = _clean(item.title, 200)
    summary = _clean(item.summary, 500)
    link = _footer_link(item)
    source = item.source or "desk"
    reason = f"Impact: {item.impact} · {item.category}"
    lines = [
        title,
        "",
        summary or reason,
        "",
        f"Źródło: {source}" if locale.startswith("pl") else f"Source: {source}",
        disc,
    ]
    if link:
        lines.extend(["", link])
    body = "\n".join(lines).strip()
    if len(body) > 1300:
        body = body[:1299] + "…"
    return ComposedPost(platform="linkedin", body=body, title=title)


def compose_for_platforms(item: MacroNewsItem, locale: str = "pl") -> list[ComposedPost]:
    return [compose_x(item, locale), compose_linkedin(item, locale)]

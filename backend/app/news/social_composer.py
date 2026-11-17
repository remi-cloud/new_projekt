"""Compose X / LinkedIn post copy from macro news items."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import MacroNewsItem
from app.news.public_urls import public_site_base
from app.news.x_auto import X_AUTHOR_FOOTER, X_MAX_CHARS, strip_forbidden_place


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
    base = public_site_base()
    if base:
        return f"{base}/news"
    if item.url:
        return item.url
    return ""


def _source_block(item: MacroNewsItem) -> tuple[str, str]:
    name = strip_forbidden_place(item.source or "").strip()
    url = (item.url or "").strip()
    return name, url


def compose_x(item: MacroNewsItem, locale: str = "pl") -> ComposedPost:
    disc = DISCLAIMER_PL if locale.startswith("pl") else DISCLAIMER_EN
    name, url = _source_block(item)
    title = _clean(strip_forbidden_place(item.title), 180)
    summary = _clean(strip_forbidden_place(item.summary), 160)
    tag = f"#{item.category.upper()} · {disc}"
    source_lines = [line for line in (f"Źródło: {name}" if name else "", url) if line]
    tail = "\n".join([*source_lines, tag, X_AUTHOR_FOOTER])

    def pack(head: str, blurb: str) -> str:
        chunks = [f"📰 {head}"]
        if blurb and blurb.lower() not in head.lower():
            chunks.append(blurb)
        chunks.append(tail)
        return "\n".join(chunks)

    body = pack(title, summary)
    if len(body) > X_MAX_CHARS:
        body = pack(title, "")
    if len(body) > X_MAX_CHARS:
        budget = X_MAX_CHARS - len(f"📰 \n{tail}") - 1
        body = pack(_clean(title, max(40, budget)), "")
    if len(body) > X_MAX_CHARS:
        room = X_MAX_CHARS - len(X_AUTHOR_FOOTER) - 1
        body = body[:room].rstrip() + "\n" + X_AUTHOR_FOOTER
    return ComposedPost(platform="x", body=body, title=title)


def compose_linkedin(item: MacroNewsItem, locale: str = "pl") -> ComposedPost:
    disc = DISCLAIMER_PL if locale.startswith("pl") else DISCLAIMER_EN
    name, url = _source_block(item)
    title = _clean(strip_forbidden_place(item.title), 200)
    summary = _clean(strip_forbidden_place(item.summary), 500)
    link = _footer_link(item)
    source = name or "desk"
    reason = f"Impact: {item.impact} · {item.category}"
    lines = [
        title,
        "",
        summary or reason,
        "",
        f"Źródło: {source}",
    ]
    if url:
        lines.append(url)
    elif link:
        lines.append(link)
    lines.append(disc)
    lines.append(X_AUTHOR_FOOTER)
    body = "\n".join(lines).strip()
    if len(body) > 1300:
        room = 1300 - len(X_AUTHOR_FOOTER) - 1
        body = body[:room].rstrip() + "\n" + X_AUTHOR_FOOTER
    return ComposedPost(platform="linkedin", body=body, title=title)


def compose_for_platforms(item: MacroNewsItem, locale: str = "pl") -> list[ComposedPost]:
    return [compose_x(item, locale), compose_linkedin(item, locale)]

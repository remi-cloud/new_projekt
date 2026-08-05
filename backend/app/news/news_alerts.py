"""Push / ntfy alerts for fresh high-impact macro news."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.schemas import MacroNewsItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsAlertEvent:
    news_id: str
    title: str
    source: str
    category: str
    impact: str
    url: str | None
    published_at: datetime
    reason: str


class NewsAlertEngine:
    def __init__(self) -> None:
        self._seen_ids: set[str] = set()
        self._last_sent: dict[str, datetime] = {}
        self._bootstrapped = False

    def reset(self, items: list[MacroNewsItem]) -> None:
        self._seen_ids = {i.id for i in items}
        self._bootstrapped = True

    def diff(self, items: list[MacroNewsItem]) -> list[NewsAlertEvent]:
        now = datetime.now(timezone.utc)
        cooldown = timedelta(minutes=settings.news_alert_cooldown_minutes)
        fresh_window = timedelta(hours=settings.news_fresh_hours)
        events: list[NewsAlertEvent] = []

        if not self._bootstrapped:
            self.reset(items)
            return []

        for item in items:
            if item.is_curated:
                continue
            if item.id in self._seen_ids:
                continue

            age = now - item.published_at
            if age > fresh_window:
                self._seen_ids.add(item.id)
                continue

            should_alert = False
            reason = ""

            title_l = (item.title or "").lower()
            stagflation_hit = "stagflation" in title_l or "stagflacj" in title_l or "cost of living" in title_l

            if item.impact == "high" and age <= fresh_window:
                should_alert = True
                reason = "Nowy news wysokiego wpływu"
            elif item.category == "usa" and age <= timedelta(hours=3):
                should_alert = True
                reason = "Świeży news USA / Trump"
            elif item.category == "musk" and age <= timedelta(hours=3):
                should_alert = True
                reason = "Świeży news Musk / Tesla / SpaceX"
            elif stagflation_hit and age <= timedelta(hours=6):
                should_alert = True
                reason = "Stagflacja / koszt życia"
            elif item.category == "fed" and age <= timedelta(hours=6):
                should_alert = True
                reason = "Świeży news Fed"

            if not should_alert:
                self._seen_ids.add(item.id)
                continue

            bucket = item.category
            last = self._last_sent.get(bucket)
            if last and now - last < cooldown:
                self._seen_ids.add(item.id)
                continue

            events.append(
                NewsAlertEvent(
                    news_id=item.id,
                    title=item.title,
                    source=item.source,
                    category=item.category,
                    impact=item.impact,
                    url=item.url,
                    published_at=item.published_at,
                    reason=reason,
                )
            )
            self._last_sent[bucket] = now
            self._seen_ids.add(item.id)

        if len(self._seen_ids) > 5000:
            self._seen_ids = set(list(self._seen_ids)[-2000:])

        return events


news_alert_engine = NewsAlertEngine()

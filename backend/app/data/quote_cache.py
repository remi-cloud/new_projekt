"""Shared quote cache with TTL — single source of truth for Markets + Dashboard."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.data.assets import DEFAULT_ASSETS, enrich_asset
from app.data.market_data import build_markets_quotes, fetch_quotes
from app.models.schemas import AssetQuote

logger = logging.getLogger(__name__)

# Quotes older than this are refetched on the next markets/dashboard hit.
# Keep short so the Markets page stays near-live while open.
QUOTE_TTL_SECONDS = 45


class QuoteCache:
    def __init__(self) -> None:
        self._quotes: dict[str, AssetQuote] = {}
        self._lock = asyncio.Lock()
        self.last_refresh_at: datetime | None = None

    @property
    def quotes(self) -> list[AssetQuote]:
        return list(self._quotes.values())

    def _is_fresh(self, q: AssetQuote, now: datetime) -> bool:
        if not q.live or q.price <= 0:
            return False
        updated = q.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = (now - updated).total_seconds()
        return age <= QUOTE_TTL_SECONDS

    async def get_catalog_quotes(
        self,
        *,
        extra_assets: list[dict] | None = None,
        force: bool = False,
    ) -> list[AssetQuote]:
        """
        Always return the full DEFAULT_ASSETS catalog (+ optional extras),
        with fresh quotes. Never hide markets behind watchlist toggles.
        """
        now = datetime.now(timezone.utc)
        by_sym: dict[str, dict] = {}
        for a in DEFAULT_ASSETS:
            by_sym[a["symbol"].upper()] = enrich_asset(a)
        for a in extra_assets or []:
            sym = str(a.get("symbol", "")).upper()
            if sym and sym not in by_sym:
                by_sym[sym] = enrich_asset(a)
        assets = list(by_sym.values())

        async with self._lock:
            stale_or_missing: list[dict] = []
            cached_ok: dict[str, AssetQuote] = {}
            for asset in assets:
                sym = asset["symbol"].upper()
                hit = self._quotes.get(sym)
                if force or hit is None or not self._is_fresh(hit, now):
                    stale_or_missing.append(asset)
                else:
                    cached_ok[sym] = hit

            if stale_or_missing:
                logger.info(
                    "QuoteCache refresh %d / %d symbols (force=%s)",
                    len(stale_or_missing),
                    len(assets),
                    force,
                )
                fresh = await fetch_quotes(stale_or_missing)
                for q in fresh:
                    self._quotes[q.symbol.upper()] = q
                    cached_ok[q.symbol.upper()] = q
                # Fill any still-missing via build (stubs)
                still = [a for a in stale_or_missing if a["symbol"].upper() not in cached_ok]
                if still:
                    filled = await build_markets_quotes(
                        still, cached=list(cached_ok.values()), fetch_missing=False
                    )
                    for q in filled:
                        self._quotes[q.symbol.upper()] = q
                        cached_ok[q.symbol.upper()] = q
                self.last_refresh_at = now

            # Ensure every catalog asset is present (stub if needed)
            out: list[AssetQuote] = []
            for asset in assets:
                sym = asset["symbol"].upper()
                q = cached_ok.get(sym) or self._quotes.get(sym)
                if q is None:
                    from app.data.market_data import stub_quote

                    q = stub_quote(asset, now)
                    q = q.model_copy(update={"quote_source": "stub"})
                    self._quotes[sym] = q
                elif not q.region:
                    q = q.model_copy(
                        update={
                            "region": asset.get("region", q.region),
                            "region_label": asset.get("region_label", q.region_label),
                        }
                    )
                    self._quotes[sym] = q
                out.append(q)
            return out

    def seed_from_scanner(self, quotes: list[AssetQuote]) -> None:
        """Push orchestrator scan quotes into cache without wiping fresher entries."""
        now = datetime.now(timezone.utc)
        for q in quotes:
            sym = q.symbol.upper()
            prev = self._quotes.get(sym)
            if prev is None or not self._is_fresh(prev, now) or q.price > 0:
                self._quotes[sym] = q
        if quotes:
            self.last_refresh_at = now


quote_cache = QuoteCache()

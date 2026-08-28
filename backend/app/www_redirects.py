"""WWW path aliases — keep in sync with frontend/src/routes.ts ALIAS_REDIRECTS."""

from __future__ import annotations

# First path segment (no leading slash) → canonical Polish/shared route.
WWW_REDIRECTS: dict[str, str] = {
    "business": "/biznes",
    "partners": "/partnerzy",
    "calculator": "/kalkulator",
    "roi": "/kalkulator",
    "markets": "/rynki",
    "alerts": "/powiadomienia",
    "about": "/o-nas",
    "portfolio": "/portfel",
    "cycles": "/cykle",
    "opportunities": "/okazje",
    "super": "/superokazje",
    "tools": "/narzedzia",
    "ai": "/agent",
    "panel": "/dashboard",
    "home": "/",
    "start": "/",
    "telegram": "/biznes",
    "discord": "/biznes",
    "channels": "/biznes",
    "kanaly": "/biznes",
}

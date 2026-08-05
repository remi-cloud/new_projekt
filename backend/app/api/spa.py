"""Serve built frontend SPA from backend/static when present."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

# English / legacy URL aliases (hard refresh & direct links)
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
    "ai": "/agent",
    "panel": "/dashboard",
    "home": "/",
    "start": "/",
    "telegram": "/biznes",
    "discord": "/biznes",
    "channels": "/biznes",
    "kanaly": "/biznes",
}


def mount_static(app: FastAPI) -> None:
    if not STATIC_DIR.exists():
        logger.info("No static frontend at %s — API-only mode", STATIC_DIR)
        return

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.api_route("/", methods=["GET", "HEAD"])
    async def serve_index():
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
        )

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        head = full_path.split("/", 1)[0].lower()
        if head in WWW_REDIRECTS:
            return RedirectResponse(url=WWW_REDIRECTS[head], status_code=307)

        static_root = STATIC_DIR.resolve()
        candidate = (STATIC_DIR / full_path).resolve()
        try:
            candidate.relative_to(static_root)
        except ValueError:
            raise HTTPException(status_code=404) from None

        if candidate.is_file():
            headers = {}
            if full_path.startswith("assets/"):
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                headers["Pragma"] = "no-cache"
            return FileResponse(candidate, headers=headers)
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
        )

    logger.info("WWW frontend enabled from %s", STATIC_DIR)

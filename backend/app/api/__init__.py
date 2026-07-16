"""HTTP API routers — registered from app.main."""

from fastapi import FastAPI

from app.api import (
    ai,
    backup,
    cycles,
    dashboard,
    growth,
    health,
    live,
    markets,
    news,
    notifications,
    paper,
    pearl,
    roi,
    spa,
)


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(dashboard.router)
    app.include_router(markets.router)
    app.include_router(roi.router)
    app.include_router(growth.router)
    app.include_router(backup.router)
    app.include_router(cycles.router)
    app.include_router(news.router)
    app.include_router(ai.router)
    app.include_router(pearl.router)
    app.include_router(notifications.router)
    app.include_router(paper.router)
    app.include_router(live.router)
    spa.mount_static(app)

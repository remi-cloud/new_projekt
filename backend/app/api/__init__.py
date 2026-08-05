"""HTTP API routers — registered from app.main."""

from fastapi import FastAPI

from app.api import (
    ai,
    backup,
    cycles,
    dashboard,
    execution,
    growth,
    health,
    live,
    markets,
    news,
    notifications,
    paper,
    pearl,
    predator,
    roi,
    singularity,
    social,
    spa,
    super_opportunities,
    telemetry,
)


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(dashboard.router)
    app.include_router(markets.router)
    app.include_router(roi.router)
    app.include_router(growth.router)
    app.include_router(backup.router)
    app.include_router(cycles.router)
    app.include_router(telemetry.router)
    app.include_router(news.router)
    app.include_router(social.router)
    app.include_router(ai.router)
    app.include_router(pearl.router)
    app.include_router(execution.router)
    app.include_router(notifications.router)
    app.include_router(paper.router)
    app.include_router(live.router)
    app.include_router(super_opportunities.router)
    app.include_router(singularity.router)
    app.include_router(predator.router)
    spa.mount_static(app)

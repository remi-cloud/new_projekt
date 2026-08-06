"""Portfolio agent — loads DB from baza_portfela/, updates live values, writes snapshot."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone

import aiosqlite

from app.db.paths import (
    database_path,
    portfolio_database_path,
    portfolio_dir,
    portfolio_repo_backup_path,
    portfolio_snapshot_path,
)
from app.db.sqlite import db_session, portfolio_db_session
from app.paper import paper_db

logger = logging.getLogger(__name__)

_LEGACY_PAPER_TABLES = ("paper_account", "paper_positions", "paper_trades")


async def _table_count(db: aiosqlite.Connection, table: str) -> int:
    try:
        row = await (await db.execute(f"SELECT COUNT(*) FROM {table}")).fetchone()
        return int(row[0]) if row else 0
    except aiosqlite.OperationalError:
        return 0


async def _legacy_has_portfolio_data() -> bool:
    legacy = database_path()
    if not legacy.exists():
        return False
    async with db_session() as db:
        positions = await _table_count(db, "paper_positions")
        trades = await _table_count(db, "paper_trades")
        return positions > 0 or trades > 0


async def _new_portfolio_is_empty() -> bool:
    if not portfolio_database_path().exists():
        return True
    async with portfolio_db_session() as db:
        positions = await _table_count(db, "paper_positions")
        trades = await _table_count(db, "paper_trades")
        return positions == 0 and trades == 0


async def migrate_legacy_portfolio_if_needed() -> bool:
    """Copy paper tables from trader.db → baza_portfela/portfolio.db on first run."""
    from app.config import settings

    if not settings.portfolio_migrate_legacy:
        return False
    if not await _new_portfolio_is_empty():
        return False
    if not await _legacy_has_portfolio_data():
        return False

    legacy = database_path()
    target = portfolio_database_path()
    ensure = portfolio_dir()
    ensure.mkdir(parents=True, exist_ok=True)

    logger.info("Migrating paper portfolio from %s → %s", legacy, target)

    async with db_session() as src:
        async with portfolio_db_session() as dst:
            for table in _LEGACY_PAPER_TABLES:
                await dst.execute(f"DROP TABLE IF EXISTS {table}")
            await dst.commit()

            await dst.execute("ATTACH DATABASE ? AS legacy", (str(legacy),))
            for table in _LEGACY_PAPER_TABLES:
                try:
                    await dst.execute(
                        f"CREATE TABLE {table} AS SELECT * FROM legacy.{table}"
                    )
                except aiosqlite.OperationalError as exc:
                    logger.warning("Skip legacy table %s: %s", table, exc)
            await dst.execute("DETACH DATABASE legacy")
            await dst.commit()

    logger.info("Portfolio migration complete → %s", target)
    return True


def _write_snapshot_file(payload: dict) -> None:
    folder = portfolio_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = portfolio_snapshot_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


async def refresh_snapshot() -> dict:
    """Rebuild mark-to-market view and persist JSON next to portfolio.db."""
    from app.paper.portfolio_service import build_portfolio

    portfolio = await build_portfolio()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "portfolio_agent",
        "db_path": str(portfolio_database_path()),
        "folder": str(portfolio_dir()),
        "portfolio": portfolio,
    }
    _write_snapshot_file(payload)
    return payload


async def restore_repo_backup_if_needed() -> bool:
    """Copy committed backups/portfolio_latest.sqlite when local DB is empty."""
    from app.config import settings

    if not settings.portfolio_restore_backup:
        return False
    backup = portfolio_repo_backup_path()
    if not backup.exists():
        return False
    if not await _new_portfolio_is_empty():
        return False

    target = portfolio_database_path()
    ensure = portfolio_dir()
    ensure.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    logger.info("Portfolio agent: restored from repo backup → %s", target)
    return True


async def sync_on_startup() -> dict:
    """Run when the app starts: ensure folder, migrate legacy DB, ledger reconcile, snapshot."""
    folder = portfolio_dir()
    folder.mkdir(parents=True, exist_ok=True)
    logger.info("Portfolio agent: folder %s", folder)

    await paper_db.init_paper_db()
    restored = await restore_repo_backup_if_needed()
    migrated = await migrate_legacy_portfolio_if_needed()
    if migrated:
        logger.info("Portfolio agent: restored data from legacy trader.db")
    elif restored:
        logger.info("Portfolio agent: restored data from backups/portfolio_latest.sqlite")

    try:
        from app.paper.ledger_agent import reconcile_on_startup

        ledger_status = await reconcile_on_startup()
        logger.info(
            "Ledger agent: trades ledger=%s db=%s rebuilt=%s ok=%s → %s",
            ledger_status.get("ledger_trades"),
            ledger_status.get("db_trades"),
            ledger_status.get("rebuilt"),
            ledger_status.get("ok"),
            ledger_status.get("ledger_dir"),
        )
    except Exception as exc:
        logger.warning("Ledger reconcile on startup failed: %s", exc)

    positions = await paper_db.get_positions()
    account = await paper_db.get_account()
    logger.info(
        "Portfolio agent: loaded %d positions, cash %.0f PLN from %s",
        len(positions),
        float(account["cash_pln"]),
        portfolio_database_path(),
    )

    snapshot = await refresh_snapshot()
    logger.info(
        "Portfolio agent: snapshot updated → %s (equity %.0f PLN)",
        portfolio_snapshot_path(),
        snapshot["portfolio"]["total_equity_pln"],
    )

    # Seed finance-agent memory from persisted paper desk (previous session → this process).
    try:
        from app.paper.portfolio_memory import seed_agent_portfolio_memory

        await seed_agent_portfolio_memory(snapshot.get("portfolio"))
    except Exception as exc:
        logger.warning("Portfolio → agent memory seed failed: %s", exc)

    return snapshot


async def sync_after_trade(trade: dict | None = None) -> None:
    """Append trade to disk ledger, then refresh JSON snapshot + agent memory."""
    if trade is not None:
        try:
            from app.paper.ledger_agent import append_trade

            await append_trade(trade)
        except Exception as exc:
            logger.warning("Ledger append after trade failed: %s", exc)
    try:
        snapshot = await refresh_snapshot()
        from app.paper.portfolio_memory import seed_agent_portfolio_memory

        await seed_agent_portfolio_memory(snapshot.get("portfolio"))
    except Exception as exc:
        logger.warning("Portfolio snapshot update failed: %s", exc)
    # Real portfolio vs SPX tick after every fill
    try:
        from app.scanners.opportunity_scanner import scanner
        from app.telemetry.agent_vs_spx import record_telemetry_tick

        spx = None
        for a in scanner.market_assessments or []:
            if getattr(a, "symbol", None) in ("^GSPC", "SPY"):
                spx = getattr(a, "price", None)
                break
        await record_telemetry_tick(
            scanner.market_assessments or [],
            spx_price=float(spx) if spx else None,
            scan_id="after_trade",
        )
    except Exception as exc:
        logger.debug("Portfolio vs SPX tick after trade skipped: %s", exc)


def backup_portfolio_db() -> str | None:
    """Optional file copy of portfolio.db into the same folder."""
    src = portfolio_database_path()
    if not src.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = portfolio_dir() / f"portfolio_backup_{stamp}.db"
    shutil.copy2(src, dest)
    return str(dest)

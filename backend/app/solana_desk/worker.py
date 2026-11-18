"""Background paper loop. One leader at a time, state kept in SQLite."""

from __future__ import annotations

import asyncio
import logging
import os

from app.solana_desk.db import init_solana_desk_db
from app.solana_desk.real_gate import install_secret_filter
from app.solana_desk.service import run_tick

log = logging.getLogger("app.solana_desk.worker")
install_secret_filter()

_task: asyncio.Task | None = None


def autostart_enabled() -> bool:
    raw = os.environ.get("SOLANA_DESK_AUTOSTART", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def interval_seconds() -> float:
    try:
        value = float(os.environ.get("SOLANA_DESK_INTERVAL_SECONDS", "25"))
    except ValueError:
        value = 25.0
    return max(10.0, min(value, 300.0))


async def run_forever() -> None:
    await init_solana_desk_db()
    log.info("Solana Desk: pętla papierowa działa co %.0f s.", interval_seconds())
    while True:
        try:
            await run_tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Solana Desk: obieg przerwany.")
        await asyncio.sleep(interval_seconds())


async def start_embedded() -> None:
    global _task
    if not autostart_enabled():
        log.info("Solana Desk: pętla w tym procesie jest wyłączona.")
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="solana-desk")


async def stop_embedded() -> None:
    global _task
    task = _task
    _task = None
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()

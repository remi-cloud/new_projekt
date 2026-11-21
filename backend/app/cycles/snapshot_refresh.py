"""Daily live recompute of the seasonality / cycle-book tables from real Yahoo history.

The ``*_data.py`` modules used to be offline snapshots (generated once, then frozen).
Here the very same generator scripts (``backend/scripts/compute_*.py``) run inside
the app on a schedule; their output is loaded and the data modules' dicts are
updated in place, so every consumer serves the fresh numbers. ``generated_at`` in
the API responses becomes the time of the last *successful* real computation.
On failure nothing changes and the previous real timestamp stays visible.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

from app.db.paths import ensure_data_dir

logger = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parents[2]
SCRIPTS = BACKEND / "scripts"

# name → (generator script, data module, consumer modules that copy GENERATED_AT)
SNAPSHOTS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "calendar": (
        "compute_calendar_seasonality.py",
        "app.cycles.calendar_seasonality_data",
        ("app.cycles.calendar_seasonality",),
    ),
    "intramonth": (
        "compute_intramonth_seasonality.py",
        "app.cycles.intramonth_seasonality_data",
        (),
    ),
    "global_book": (
        "compute_global_cycle_book.py",
        "app.cycles.global_cycle_book_data",
        ("app.cycles.global_cycle_book",),
    ),
}

_STATE: dict[str, dict] = {}


def snapshot_state() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name, (_script, data_mod, _c) in SNAPSHOTS.items():
        st = dict(_STATE.get(name) or {})
        if "updated_at" not in st:
            try:
                st["updated_at"] = getattr(importlib.import_module(data_mod), "GENERATED_AT", None)
            except Exception:  # pragma: no cover
                st["updated_at"] = None
            st.setdefault("live", False)
        st["source"] = "Yahoo Finance (miesięczne/dzienne zamknięcia)"
        out[name] = st
    return out


def _load_script(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_live_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_generated(data_module: ModuleType, namespace: dict, consumers: tuple[str, ...] = ()) -> int:
    """Copy UPPER_CASE names into ``data_module``; dicts/lists are updated in place."""
    changed = 0
    for key, value in namespace.items():
        if not key.isupper():
            continue
        cur = getattr(data_module, key, None)
        if isinstance(cur, dict) and isinstance(value, dict):
            cur.clear()
            cur.update(value)
        elif isinstance(cur, list) and isinstance(value, list):
            cur[:] = value
        else:
            setattr(data_module, key, value)
        changed += 1
    gen = namespace.get("GENERATED_AT")
    for name in consumers:
        try:
            consumer = importlib.import_module(name)
            if gen is not None and hasattr(consumer, "GENERATED_AT"):
                setattr(consumer, "GENERATED_AT", gen)
        except Exception as exc:  # pragma: no cover
            logger.debug("consumer %s not updated: %s", name, exc)
    return changed


def _run_generator(script: str, out_path: Path) -> dict:
    mod = _load_script(SCRIPTS / script)
    mod.OUT = out_path  # never rewrite the source tree at runtime
    mod.main()
    ns: dict = {}
    exec(compile(out_path.read_text(encoding="utf-8"), str(out_path), "exec"), ns)  # noqa: S102
    return ns


async def refresh_snapshot(name: str) -> bool:
    script, data_mod, consumers = SNAPSHOTS[name]
    started = datetime.now(timezone.utc)
    out_dir = ensure_data_dir().parent / "live_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.py"
    try:
        ns = await asyncio.to_thread(_run_generator, script, out_path)
        if not any(k.isupper() for k in ns):
            raise ValueError("generator produced no tables")
        apply_generated(importlib.import_module(data_mod), ns, consumers)
    except Exception as exc:
        prev = _STATE.get(name) or {}
        _STATE[name] = {**prev, "last_error": str(exc)[:200], "last_attempt_at": started.isoformat()}
        logger.warning("Snapshot %s refresh failed (keeping last real values): %s", name, exc)
        return False
    _STATE[name] = {
        "updated_at": ns.get("GENERATED_AT") or started.isoformat(),
        "live": True,
        "last_error": None,
        "last_attempt_at": started.isoformat(),
    }
    logger.info("Snapshot %s refreshed from real data", name)
    return True


async def refresh_all_snapshots() -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name in SNAPSHOTS:
        results[name] = await refresh_snapshot(name)
    return results

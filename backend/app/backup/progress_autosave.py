"""Auto-save project progress into backups/progress/ (and rotating snapshots)."""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.db.paths import database_path, portfolio_database_path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRESS_DIR = REPO_ROOT / "backups" / "progress"
SESSIONS_DIR = REPO_ROOT / "backups" / "sessions_auto"

def _sqlite_backup(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    try:
        target = sqlite3.connect(tmp)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    tmp.replace(dest)


def backup_enabled() -> bool:
    return bool(getattr(settings, "auto_backup_enabled", True))


def progress_status() -> dict[str, Any]:
    latest = PROGRESS_DIR / "latest.json"
    payload: dict[str, Any] = {
        "enabled": backup_enabled(),
        "interval_seconds": int(getattr(settings, "auto_backup_interval_seconds", 20)),
        "progress_dir": "backups/progress",
        "latest": None,
    }
    if latest.is_file():
        try:
            payload["latest"] = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload["latest"] = {"raw": latest.read_text(encoding="utf-8")[:500]}
    return payload


def save_progress(*, reason: str = "scheduled") -> dict[str, Any]:
    """Copy critical work folders into backups/progress/current (+ rotate stamp)."""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    current = PROGRESS_DIR / "current"
    current.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []
    db_sources = [
        (database_path(), "trader.db"),
        (portfolio_database_path(), "portfolio.db"),
    ]
    for src, name in db_sources:
        if not src.is_file():
            missing.append(name)
            continue
        try:
            _sqlite_backup(src, current / name)
            copied.append(name)
        except sqlite3.Error as exc:
            logger.warning("Autosave failed for %s: %s", name, type(exc).__name__)
            missing.append(name)
    static = REPO_ROOT / "backend" / "static"
    if static.is_dir():
        dest = current / "static_www"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(static, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            copied.append("static_www")
        except OSError:
            missing.append("static_www")
    example = REPO_ROOT / ".env.example"
    if example.is_file():
        try:
            shutil.copy2(example, current / "env.example")
            copied.append("env.example")
        except OSError:
            missing.append("env.example")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rotate_every = max(1, int(getattr(settings, "auto_backup_rotate_every", 15)))
    meta_path = PROGRESS_DIR / "counter.txt"
    count = 0
    if meta_path.is_file():
        try:
            count = int(meta_path.read_text().strip() or "0")
        except ValueError:
            count = 0
    count += 1
    meta_path.write_text(str(count), encoding="utf-8")

    rotated = False
    if count % rotate_every == 0:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        snap = SESSIONS_DIR / f"progress_{stamp}"
        try:
            shutil.copytree(current, snap)
            rotated = True
            _prune_old_sessions(keep=int(getattr(settings, "auto_backup_keep", 12)))
        except OSError as exc:
            logger.warning("Rotate snapshot failed: %s", exc)

    manifest = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "copied": copied,
        "missing": missing,
        "rotated": rotated,
        "counter": count,
        "progress_path": "backups/progress/current",
    }
    (PROGRESS_DIR / "latest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Progress autosaved (%s): %d items → %s",
        reason,
        len(copied),
        current,
    )
    return manifest


def _prune_old_sessions(*, keep: int) -> None:
    if not SESSIONS_DIR.is_dir():
        return
    sessions = sorted(
        [p for p in SESSIONS_DIR.iterdir() if p.is_dir() and p.name.startswith("progress_")],
        key=lambda p: p.name,
    )
    while len(sessions) > keep:
        old = sessions.pop(0)
        shutil.rmtree(old, ignore_errors=True)

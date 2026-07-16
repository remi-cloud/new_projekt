"""Auto-save project progress into backups/progress/ (and rotating snapshots)."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRESS_DIR = REPO_ROOT / "backups" / "progress"
SESSIONS_DIR = REPO_ROOT / "backups" / "sessions_auto"

_BACKUP_ITEMS: list[tuple[str, str]] = [
    ("backend/data/baza_portfela", "baza_portfela"),
    ("backend/data/trader.db", "trader.db"),
    ("backend/static", "static_www"),
    (".env.example", "env.example"),
]


def _resolve(rel: str) -> Path:
    p = REPO_ROOT / rel
    if p.exists():
        return p
    alt = Path.cwd() / rel.replace("backend/", "", 1)
    if alt.exists():
        return alt
    return p


def backup_enabled() -> bool:
    return bool(getattr(settings, "auto_backup_enabled", True))


def progress_status() -> dict[str, Any]:
    latest = PROGRESS_DIR / "latest.json"
    payload: dict[str, Any] = {
        "enabled": backup_enabled(),
        "interval_seconds": int(getattr(settings, "auto_backup_interval_seconds", 20)),
        "progress_dir": str(PROGRESS_DIR),
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
    for rel, name in _BACKUP_ITEMS:
        src = _resolve(rel)
        dest = current / name
        if not src.exists():
            missing.append(rel)
            continue
        try:
            if src.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(
                    src,
                    dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
                )
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            copied.append(name)
        except OSError as exc:
            logger.warning("Autosave failed for %s: %s", rel, exc)
            missing.append(f"{rel}:{exc}")

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
        "progress_path": str(current),
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

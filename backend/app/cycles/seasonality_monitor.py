"""Seasonality drift monitor — softens overlay when matrices drift too far."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.cycles.bitcoin_seasonality_data import (
    BTC_CALENDAR_MONTHLY_RETURNS,
    SPX_COMPARISON,
)
from app.cycles.presidential_seasonality_data import US_UNIVERSE_MONTHLY_RETURNS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LATEST = DATA_DIR / "seasonality_monitor_latest.json"
PREV = DATA_DIR / "seasonality_monitor_prev.json"

MAX_CELL_DELTA_PP = 2.0
MEAN_ABS_DELTA_PP = 0.5
SOFTENED_SCALE = 0.5
NORMAL_SCALE = 1.0

_state: dict[str, Any] = {
    "overlay_scale": NORMAL_SCALE,
    "drift_alert": False,
    "last_run": None,
    "pres_max_delta": 0.0,
    "pres_mean_abs_delta": 0.0,
    "btc_max_delta": 0.0,
    "btc_mean_abs_delta": 0.0,
    "btc_verdict": SPX_COMPARISON.get("verdict"),
    "btc_regime": SPX_COMPARISON.get("regime"),
    "flags": [],
}


def get_overlay_scale() -> float:
    return float(_state.get("overlay_scale") or NORMAL_SCALE)


def get_health() -> dict[str, Any]:
    return dict(_state)


def _snapshot_now() -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "presidential": {
            str(y): {str(m): float(US_UNIVERSE_MONTHLY_RETURNS[y][m]) for m in range(1, 13)}
            for y in range(1, 5)
        },
        "btc_calendar": {str(m): float(BTC_CALENDAR_MONTHLY_RETURNS[m]) for m in range(1, 13)},
        "btc_verdict": SPX_COMPARISON.get("verdict"),
        "btc_regime": SPX_COMPARISON.get("regime"),
    }


def _cell_deltas(
    a: dict[str, dict[str, float]], b: dict[str, dict[str, float]]
) -> tuple[float, float]:
    deltas: list[float] = []
    for y, row in a.items():
        brow = b.get(y) or {}
        for m, v in row.items():
            if m in brow:
                deltas.append(abs(float(v) - float(brow[m])))
    if not deltas:
        return 0.0, 0.0
    return max(deltas), sum(deltas) / len(deltas)


def _cal_deltas(a: dict[str, float], b: dict[str, float]) -> tuple[float, float]:
    deltas = [abs(float(a[m]) - float(b[m])) for m in a if m in b]
    if not deltas:
        return 0.0, 0.0
    return max(deltas), sum(deltas) / len(deltas)


def run_seasonality_monitor(*, persist: bool = True) -> dict[str, Any]:
    """Compare current baked matrices to previous snapshot; update overlay_scale."""
    global _state
    snap = _snapshot_now()
    flags: list[str] = []
    pres_max = pres_mean = btc_max = btc_mean = 0.0
    overlay = NORMAL_SCALE
    drift = False

    if PREV.exists() or LATEST.exists():
        prev_path = PREV if PREV.exists() else LATEST
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            pres_max, pres_mean = _cell_deltas(
                snap["presidential"], prev.get("presidential") or {}
            )
            btc_max, btc_mean = _cal_deltas(
                snap["btc_calendar"], prev.get("btc_calendar") or {}
            )
            if (
                prev.get("btc_verdict") != snap.get("btc_verdict")
                or prev.get("btc_regime") != snap.get("btc_regime")
            ):
                flags.append("btc_verdict_or_regime_changed")
            if pres_max > MAX_CELL_DELTA_PP or pres_mean > MEAN_ABS_DELTA_PP:
                flags.append("presidential_drift")
                drift = True
            if btc_max > MAX_CELL_DELTA_PP or btc_mean > MEAN_ABS_DELTA_PP:
                flags.append("btc_calendar_drift")
                drift = True
            if drift:
                overlay = SOFTENED_SCALE
                flags.append(f"overlay_scale={SOFTENED_SCALE}")
        except Exception as exc:
            logger.warning("Seasonality monitor prev read failed: %s", exc)
            flags.append("prev_unreadable")

    _state = {
        "overlay_scale": overlay,
        "drift_alert": drift,
        "last_run": snap["ts"],
        "pres_max_delta": round(pres_max, 3),
        "pres_mean_abs_delta": round(pres_mean, 3),
        "btc_max_delta": round(btc_max, 3),
        "btc_mean_abs_delta": round(btc_mean, 3),
        "btc_verdict": snap.get("btc_verdict"),
        "btc_regime": snap.get("btc_regime"),
        "flags": flags,
        "thresholds": {
            "max_cell_delta_pp": MAX_CELL_DELTA_PP,
            "mean_abs_delta_pp": MEAN_ABS_DELTA_PP,
        },
    }

    if persist:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if LATEST.exists():
            LATEST.replace(PREV)
        LATEST.write_text(json.dumps({**snap, "health": _state}, indent=2) + "\n", encoding="utf-8")

    logger.info(
        "Seasonality monitor: drift=%s scale=%.2f flags=%s",
        drift,
        overlay,
        flags,
    )
    return get_health()

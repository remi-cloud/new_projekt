#!/usr/bin/env bash
# Quarterly (or on-demand) refresh of BTC seasonality matrices + vs-SPX verdict.
# Usage: ./scripts/recompute-btc-seasonality.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
PREV="data/btc_seasonality_debug.json"
SNAP="data/btc_seasonality_debug.prev.json"
if [[ -f "$PREV" ]]; then
  cp "$PREV" "$SNAP"
fi
PYTHONPATH=. .venv/bin/python scripts/compute_bitcoin_monthly.py
if [[ -f "$SNAP" ]]; then
  python3 - <<'PY'
import json
from pathlib import Path

prev = json.loads(Path("data/btc_seasonality_debug.prev.json").read_text())
cur = json.loads(Path("data/btc_seasonality_debug.json").read_text())
keys = ("verdict", "regime", "corr_full", "best_six_delta_pct", "month_sign_agreement")
print("Drift check (prev → cur):")
for k in keys:
    print(f"  {k}: {prev.get(k)} → {cur.get(k)}")
if prev.get("verdict") != cur.get("verdict") or prev.get("regime") != cur.get("regime"):
    print("NOTE: verdict/regime changed — review docs/BTC-SEASONALITY.md and AI knowledge.")
else:
    print("OK: verdict/regime stable.")
PY
fi
echo "Done. See docs/BTC-SEASONALITY.md"

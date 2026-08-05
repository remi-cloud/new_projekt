#!/usr/bin/env bash
# Idempotent dependency install for Cursor Cloud / local debut.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Prefer python3.12/3.11 if present (3.14 sometimes breaks wheels)
PY=python3
if command -v python3.12 >/dev/null 2>&1; then PY=python3.12
elif command -v python3.11 >/dev/null 2>&1; then PY=python3.11
fi

echo "→ Backend Python deps ($($PY --version 2>&1))"
cd "$ROOT/backend"
if [[ ! -d .venv/bin ]]; then
  rm -rf .venv
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "→ Frontend Node deps"
cd "$ROOT/frontend"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "✓ install complete"

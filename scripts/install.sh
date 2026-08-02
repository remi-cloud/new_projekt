#!/usr/bin/env bash
# Idempotent dependency install for Cursor Cloud / local debut.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Backend Python deps"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
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

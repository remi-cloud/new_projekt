#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Frontend: vitest + tsc"
cd frontend
npm run test
npx tsc --noEmit
cd "$ROOT"

echo "==> Backend: pytest"
cd backend
if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi
$PY -m pytest tests/ -q --tb=line

echo "==> Build static"
cd "$ROOT"
./scripts/build-www.sh

echo "==> All tests passed"

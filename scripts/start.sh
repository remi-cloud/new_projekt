#!/usr/bin/env bash
# Uniwersalny start — na Macu przekierowuje do mac-start.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$(uname -s)" = "Darwin" ]; then
  exec "$ROOT/scripts/mac-start.sh" "$@"
fi

# Linux / CI
cd "$ROOT"
PORT="${PORT:-8080}"

if [ ! -d "backend/static" ] || [ -z "$(ls -A backend/static 2>/dev/null)" ]; then
  echo "Budowanie frontendu…"
  ./scripts/build-www.sh
fi

cd backend
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

mkdir -p data/baza_portfela
if [ ! -f data/baza_portfela/portfolio.db ] && [ -f "$ROOT/backups/portfolio_latest.sqlite" ]; then
  cp "$ROOT/backups/portfolio_latest.sqlite" data/baza_portfela/portfolio.db
  echo "Przywrócono portfel z backupu."
fi

echo "Aplikacja: http://localhost:${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Budowanie frontendu WWW..."
cd "$ROOT/frontend"
npm install --silent
npm run build

echo "==> Kopiowanie do backend/static..."
rm -rf "$ROOT/backend/static"
mkdir -p "$ROOT/backend/static"
cp -r dist/* "$ROOT/backend/static/"

echo "==> Gotowe! Uruchom backend:"
echo "    cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8080"
echo "    Otwórz: http://localhost:8080"

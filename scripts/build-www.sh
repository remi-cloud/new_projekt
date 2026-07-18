#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Building frontend…"
cd "$ROOT/frontend"
npm install
npm run build

echo "→ Copying dist → backend/static…"
rm -rf "$ROOT/backend/static"
mkdir -p "$ROOT/backend/static"
cp -R "$ROOT/frontend/dist/." "$ROOT/backend/static/"

echo "✓ WWW ready. Start with:"
echo "  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8080"
echo "  Open http://localhost:8080 (or phone via tunnel / LAN IP)"

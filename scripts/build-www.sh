#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Building frontend…"
cd "$ROOT/frontend"
npm install
npm run build

echo "→ Copying dist → backend/static (keep prior hashed assets)…"
# Never wipe previous /assets/*.js hashes: cached HTML still points at them → 404 → blank #root.
mkdir -p "$ROOT/backend/static/assets"
# Sync non-asset files with delete so removed public files disappear.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude 'assets/' "$ROOT/frontend/dist/" "$ROOT/backend/static/"
  # Merge new hashed assets; do NOT --delete orphans.
  rsync -a "$ROOT/frontend/dist/assets/" "$ROOT/backend/static/assets/"
else
  # Fallback without rsync: copy over, keep existing asset orphans.
  find "$ROOT/frontend/dist" -mindepth 1 -maxdepth 1 ! -name assets -exec cp -R {} "$ROOT/backend/static/" \;
  cp -R "$ROOT/frontend/dist/assets/." "$ROOT/backend/static/assets/"
fi

echo "✓ WWW ready. Start with:"
echo "  ./scripts/dev-up.sh"
echo "  ./scripts/mac-start.sh"
echo "  ./scripts/start-public.sh   # telefon / publiczny link"
echo "  Open http://localhost:8080"

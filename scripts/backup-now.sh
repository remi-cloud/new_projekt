#!/usr/bin/env bash
# Pełny snapshot projektu → backups/session_YYYYMMDD_HHMMSS/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$ROOT/backups/session_$STAMP"
mkdir -p "$DEST"

echo "==> Snapshot → $DEST"

# Kod i konfiguracja (bez secrets .env jeśli wolisz — kopiujemy .env.example zawsze;
# .env lokalny też, żeby nic nie zgubić w drodze do domu)
rsync -a \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'backend/.venv/' \
  --exclude '**/.venv/' \
  --exclude '**/__pycache__/' \
  --exclude '**/.pytest_cache/' \
  --exclude 'frontend/dist/' \
  --exclude 'backups/session_*/' \
  --exclude '.DS_Store' \
  "$ROOT/" "$DEST/"

# Manifest
{
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "hostname=$(hostname 2>/dev/null || echo unknown)"
  echo "path=$DEST"
  echo "note=Full work snapshot before leave / safety copy"
} > "$DEST/BACKUP_MANIFEST.txt"

# Aktualny wskaźnik „latest”
ln -sfn "session_$STAMP" "$ROOT/backups/latest_session" 2>/dev/null || true
echo "$DEST" > "$ROOT/backups/LATEST_SESSION.txt"

echo "==> Gotowe: $DEST"
du -sh "$DEST" 2>/dev/null || true

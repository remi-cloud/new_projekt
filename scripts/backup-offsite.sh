#!/usr/bin/env bash
# Copy SQLite desks off this machine. Does not read .env secrets.
# Usage:
#   CYCLICAL_BACKUP_DEST=user@backup.example:/var/backups/kar-digital ./scripts/backup-offsite.sh
#   CYCLICAL_BACKUP_DEST=/mnt/offsite/kar-digital ./scripts/backup-offsite.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CYCLICAL_BACKUP_DEST:-}"
if [[ -z "$DEST" ]]; then
  echo "Ustaw CYCLICAL_BACKUP_DEST na katalog albo user@host:/ścieżka" >&2
  exit 2
fi

DB="${CYCLICAL_DATABASE_PATH:-$ROOT/backend/data/trader.db}"
PORTFOLIO="${CYCLICAL_PORTFOLIO_DATABASE_PATH:-$ROOT/backend/data/baza_portfela/portfolio.db}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/$STAMP"
copy_one() {
  local src="$1"
  local name="$2"
  if [[ -f "$src" ]]; then
    cp "$src" "$STAGE/$STAMP/$name"
  else
    echo "Pominięto brakujący plik: $src" >&2
  fi
}
copy_one "$DB" "trader.db"
copy_one "$PORTFOLIO" "portfolio.db"
if [[ -d "$(dirname "$PORTFOLIO")/ledger" ]]; then
  cp -a "$(dirname "$PORTFOLIO")/ledger" "$STAGE/$STAMP/ledger"
fi
printf '%s\n' "$STAMP" >"$STAGE/$STAMP/STAMP.txt"

if command -v rsync >/dev/null 2>&1; then
  if [[ "$DEST" == *:* ]]; then
    rsync -a "$STAGE/$STAMP" "$DEST/"
  else
    mkdir -p "$DEST"
    rsync -a "$STAGE/$STAMP" "$DEST/"
  fi
elif [[ "$DEST" == *:* ]]; then
  scp -r "$STAGE/$STAMP" "$DEST/"
else
  mkdir -p "$DEST"
  cp -a "$STAGE/$STAMP" "$DEST/"
fi
echo "Kopia baz: $DEST/$STAMP"

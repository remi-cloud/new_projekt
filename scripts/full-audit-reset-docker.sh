#!/usr/bin/env bash
# Cykliczny Trader · Kar Digital — pełny audyt + reset Docker WWW
# Mac: dwuklik lub: bash ~/Desktop/Cykliczny-Trader-FULL-AUDIT.command
set -euo pipefail

ROOT="${CYCLICAL_ROOT:-$HOME/Desktop/Cykliczny Trader Kar Digital}"
PORT="${PORT:-8080}"
BASE="http://127.0.0.1:${PORT}"
export PATH="/Applications/Docker.app/Contents/Resources/bin:${HOME}/.docker/bin:/usr/local/bin:${PATH}"

ok() { echo "✓ $*"; }
info() { echo "→ $*"; }
fail() { echo "✗ $*" >&2; exit 1; }

cd "$ROOT" || fail "Brak katalogu projektu: $ROOT"

info "1/6 Stop lokalnego WWW + Docker compose"
./scripts/www-down.sh || true
docker compose down || true

info "2/6 mac-doctor"
./scripts/mac-doctor.sh

info "3/6 test-all (vitest + pytest)"
./scripts/test-all.sh

info "4/6 docker-up (rebuild + start kontenera)"
./scripts/docker-up.sh

info "5/6 audit smoke"
if ! ./scripts/audit.sh "$BASE"; then
  info "Audit fail — audit-fix"
  ./scripts/audit-fix.sh "$BASE"
fi

info "6/6 Status kontenera"
docker compose ps || true
curl -sf "$BASE/api/health" | python3 -m json.tool 2>/dev/null || curl -sf "$BASE/api/health" || true

ok "WWW: $BASE"
open "$BASE" 2>/dev/null || true
echo ""
echo "========================================"
echo "  Otwórz: $BASE"
echo "========================================"

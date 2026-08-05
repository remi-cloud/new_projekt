#!/usr/bin/env bash
# If health/audit fails → bring WWW up and re-audit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-http://127.0.0.1:8080}"
PORT="${PORT:-8080}"

echo "=== audit-fix ($BASE) ==="
if ! curl -sf --max-time 5 "$BASE/api/health" >/dev/null 2>&1; then
  echo "→ Health down — ./scripts/www-up.sh"
  "$ROOT/scripts/www-up.sh"
fi

if "$ROOT/scripts/audit.sh" "$BASE"; then
  exit 0
fi

echo "→ Audit failed — rebuild + www-up + retry"
"$ROOT/scripts/build-www.sh"
"$ROOT/scripts/www-up.sh"
"$ROOT/scripts/audit.sh" "$BASE"

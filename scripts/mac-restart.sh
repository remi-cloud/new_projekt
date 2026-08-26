#!/usr/bin/env bash
# Restart Cyclical Trader (stop + start)
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
"$ROOT/scripts/www-down.sh"
exec "$ROOT/scripts/www-up.sh"

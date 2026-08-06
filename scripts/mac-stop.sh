#!/usr/bin/env bash
# Zatrzymaj Cyclical Trader na Macu (uvicorn na porcie 8080 / $PORT)
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PORT="${PORT-8080}"
exec "$ROOT/scripts/www-down.sh"

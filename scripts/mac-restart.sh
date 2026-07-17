#!/usr/bin/env bash
# Restart Cyclical Trader (stop + start)
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
"$ROOT/scripts/mac-stop.sh"
exec "$ROOT/scripts/mac-start.sh"

#!/usr/bin/env bash
# Public smoke audit — backend API + frontend static + live markets.
set -euo pipefail
BASE="${1:-http://127.0.0.1:8080}"
fail=0

check() {
  local path="$1" expect="$2"
  local code body
  body=$(mktemp)
  code=$(curl -sS -o "$body" -w '%{http_code}' --max-time 60 "$BASE$path" || echo 000)
  if [[ "$code" != "$expect" ]]; then
    echo "FAIL $path -> HTTP $code (want $expect)"
    fail=1
  else
    echo "OK   $path -> $code"
  fi
  rm -f "$body"
}

echo "=== Audit $BASE ==="
check /api/health 200
check /live 200
check /rynki 200
check /api/markets?region=all 200
check /api/market-status 200
check /api/broadcast 200

LIVE=$(curl -sf --max-time 90 "$BASE/api/markets?region=all" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("live_count",0),d.get("count",0))')
read -r LIVE_N COUNT <<<"$LIVE"
echo "markets live=$LIVE_N count=$COUNT"
if [[ "${LIVE_N:-0}" -lt 1 || "${COUNT:-0}" -lt 1 ]]; then
  echo "FAIL markets empty"
  fail=1
else
  echo "OK   markets non-empty"
fi

SRC=$(curl -sf --max-time 30 "$BASE/live" | rg -o 'TRADINGVIEW [0-9]+|YAHOO [0-9]+' | head -5 || true)
echo "live sources: $SRC"
if ! echo "$SRC" | rg -q 'TRADINGVIEW|YAHOO'; then
  echo "FAIL /live missing source line"
  fail=1
else
  echo "OK   /live shows sources"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "=== AUDIT FAILED ==="
  exit 1
fi
echo "=== AUDIT PASSED ==="

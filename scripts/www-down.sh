#!/usr/bin/env bash
# Stop Cyclical Trader WWW (pidfile + port).
# Usage: ./scripts/www-down.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
PIDFILE="$ROOT/backend/.run/uvicorn.pid"

echo "→ Zatrzymuję WWW na :$PORT …"

if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
fi

# Also clear anything still listening (uvicorn without pidfile)
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$PIDS" ]]; then
    # shellcheck disable=SC2086
    kill $PIDS 2>/dev/null || true
    sleep 1
    LEFT="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
    # shellcheck disable=SC2086
    [[ -n "$LEFT" ]] && kill -9 $LEFT 2>/dev/null || true
  fi
fi

# Best-effort: leftover uvicorn from this project
pkill -f "$ROOT/backend/.venv/bin/uvicorn app.main:app" 2>/dev/null || true

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ Port $PORT nadal zajęty"
  exit 1
fi
echo "✓ Port $PORT wolny"

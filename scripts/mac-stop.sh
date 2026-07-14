#!/usr/bin/env bash
# Zatrzymaj Cyclical Trader na Macu (uvicorn na porcie 8080 / $PORT)
set -euo pipefail
PORT="${PORT:-8080}"

echo "Szukam procesu na porcie $PORT…"
if ! command -v lsof >/dev/null 2>&1; then
  echo "Brak lsof — użyj Ctrl+C w oknie Terminala z serwerem."
  exit 1
fi

PIDS="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -z "$PIDS" ]; then
  echo "Nic nie nasłuchuje na :$PORT — już zatrzymane."
  exit 0
fi

echo "Zatrzymuję PID: $PIDS"
# shellcheck disable=SC2086
kill $PIDS 2>/dev/null || true
sleep 1
LEFT="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$LEFT" ]; then
  echo "Wymuszam kill -9…"
  # shellcheck disable=SC2086
  kill -9 $LEFT 2>/dev/null || true
fi
echo "OK — port $PORT wolny."

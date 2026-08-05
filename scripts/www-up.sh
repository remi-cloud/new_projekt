#!/usr/bin/env bash
# Start Cyclical Trader WWW detached (survives shell exit / tunnel failures).
# Usage: ./scripts/www-up.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
RUN_DIR="$ROOT/backend/.run"
PIDFILE="$RUN_DIR/uvicorn.pid"
LOG_FILE="${WWW_LOG:-/tmp/kar-uvicorn.log}"
STATIC_INDEX="$ROOT/backend/static/index.html"

ok() { echo "✓ $*"; }
info() { echo "→ $*"; }
fail() { echo "✗ $*" >&2; exit 1; }

mkdir -p "$RUN_DIR" "$ROOT/backend/data/baza_portfela"
export CYCLICAL_DATABASE_PATH="${CYCLICAL_DATABASE_PATH:-$ROOT/backend/data/trader.db}"

# Already healthy?
if curl -sf --max-time 3 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  STATUS=$(curl -sf --max-time 3 "http://127.0.0.1:${PORT}/api/health" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || true)
  if [[ "$STATUS" == "ok" ]]; then
    # Refresh pidfile if listen PID known
    if command -v lsof >/dev/null 2>&1; then
      LPID="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
      [[ -n "$LPID" ]] && echo "$LPID" >"$PIDFILE"
    fi
    ok "WWW już działa: http://127.0.0.1:${PORT}"
    LAN="$(ipconfig getifaddr en0 2>/dev/null || true)"
    [[ -n "$LAN" ]] && info "LAN: http://${LAN}:${PORT}"
    exit 0
  fi
fi

# Build static if missing
if [[ ! -f "$STATIC_INDEX" ]]; then
  info "Brak static — buduję WWW…"
  "$ROOT/scripts/build-www.sh"
fi

# Ensure venv
cd "$ROOT/backend"
PY=python3
if command -v python3.12 >/dev/null 2>&1; then PY=python3.12
elif command -v python3.11 >/dev/null 2>&1; then PY=python3.11
fi
if [[ ! -x .venv/bin/uvicorn ]]; then
  info "Tworzę venv ($PY)…"
  rm -rf .venv
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
fi
UVICORN="$ROOT/backend/.venv/bin/uvicorn"
[[ -x "$UVICORN" ]] || fail "Brak $UVICORN"

# Free port / stale pid
if [[ -f "$PIDFILE" ]]; then
  OLD="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "$OLD" ]] && kill -0 "$OLD" 2>/dev/null; then
    info "Zatrzymuję stary PID $OLD…"
    kill "$OLD" 2>/dev/null || true
    sleep 1
    kill -9 "$OLD" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
fi
if command -v lsof >/dev/null 2>&1; then
  LEFT="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$LEFT" ]]; then
    info "Zwalniam port $PORT (PID $LEFT)…"
    # shellcheck disable=SC2086
    kill $LEFT 2>/dev/null || true
    sleep 1
    LEFT="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
    # shellcheck disable=SC2086
    [[ -n "$LEFT" ]] && kill -9 $LEFT 2>/dev/null || true
  fi
fi

info "Start uvicorn ${HOST}:${PORT} (log: $LOG_FILE)…"
# New session (setsid) — survives Cursor/agent shell teardown & SIGHUP
NEW_PID="$(
  HOST="$HOST" PORT="$PORT" LOG_FILE="$LOG_FILE" UVICORN="$UVICORN" ROOT="$ROOT" \
  "$PY" - <<'PY'
import os, subprocess, sys
uv = os.environ["UVICORN"]
host = os.environ["HOST"]
port = os.environ["PORT"]
log = os.environ["LOG_FILE"]
cwd = os.path.join(os.environ["ROOT"], "backend")
os.makedirs(os.path.dirname(log) or ".", exist_ok=True)
with open(log, "a", encoding="utf-8") as fh:
    fh.write("\n--- www-up start ---\n")
    fh.flush()
    proc = subprocess.Popen(
        [uv, "app.main:app", "--host", host, "--port", port],
        cwd=cwd,
        stdout=fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env={**os.environ, "CYCLICAL_DATABASE_PATH": os.environ.get("CYCLICAL_DATABASE_PATH", "")},
    )
print(proc.pid)
PY
)"
[[ -n "$NEW_PID" ]] || fail "Nie uruchomiono uvicorn"
echo "$NEW_PID" >"$PIDFILE"

for _ in $(seq 1 60); do
  if curl -sf --max-time 2 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

HEALTH="$(curl -sf --max-time 5 "http://127.0.0.1:${PORT}/api/health" || true)"
[[ -n "$HEALTH" ]] || fail "Health check failed — zobacz $LOG_FILE"
STATUS="$(printf '%s' "$HEALTH" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
WWW="$(printf '%s' "$HEALTH" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("www",False))')"
[[ "$STATUS" == "ok" ]] || fail "health.status=$STATUS"
if [[ "$WWW" != "True" && "$WWW" != "true" ]]; then
  info "www=false — buduję frontend…"
  "$ROOT/scripts/build-www.sh"
  # static is served from disk; no restart needed if already mounted
fi

CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${PORT}/" || echo 000)"
[[ "$CODE" == "200" ]] || fail "/ -> HTTP $CODE"

ok "WWW: http://127.0.0.1:${PORT} (pid $(cat "$PIDFILE"))"
LAN="$(ipconfig getifaddr en0 2>/dev/null || true)"
[[ -n "$LAN" ]] && ok "LAN: http://${LAN}:${PORT}"

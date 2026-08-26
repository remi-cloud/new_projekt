#!/usr/bin/env bash
# Retries Cope register until a key lands, then injects it into .env + Docker and runs a tick.
# Run in background; exits 0 when FOMO Ghost is live.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
INTERVAL="${FOMO_RETRY_INTERVAL:-45}"
MAX_TRIES="${FOMO_RETRY_MAX:-200}"
LOG="$ROOT/backend/data/fomo-retry.log"
mkdir -p "$ROOT/backend/data"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

apply_key() {
  local KEY="$1"
  local LINE="CYCLICAL_COPE_API_KEY=${KEY}"
  local ENV_FILE="$ROOT/.env"
  if [[ -f "$ENV_FILE" ]] && grep -q '^CYCLICAL_COPE_API_KEY=' "$ENV_FILE"; then
    if sed --version >/dev/null 2>&1; then
      sed -i "s|^CYCLICAL_COPE_API_KEY=.*|${LINE}|" "$ENV_FILE"
    else
      sed -i '' "s|^CYCLICAL_COPE_API_KEY=.*|${LINE}|" "$ENV_FILE"
    fi
  else
    {
      echo ""
      echo "# FOMO Ghost (Cope Capital) — auto by fomo-retry-until-live.sh"
      echo "$LINE"
    } >> "$ENV_FILE"
  fi
  printf '%s\n' "$KEY" > "$ROOT/backend/data/cope_api_key.txt"
  chmod 600 "$ROOT/backend/data/cope_api_key.txt" 2>/dev/null || true

  # Inject into running Docker volume so next tick picks it up without rebuild
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'cyclical-trader-www'; then
    docker exec cyclical-trader-www sh -c "printf '%s\n' '$KEY' > /app/data/cope_api_key.txt && chmod 600 /app/data/cope_api_key.txt" \
      && log "Injected key into Docker /app/data/cope_api_key.txt" \
      || log "Docker inject failed (will rely on .env recreate)"
    # Recreate with env so CYCLICAL_COPE_API_KEY is in process env too
    (cd "$ROOT" && docker compose up -d --force-recreate www) >>"$LOG" 2>&1 || true
  fi
}

log "FOMO retry started (interval=${INTERVAL}s, max=${MAX_TRIES})"

for ((i=1; i<=MAX_TRIES; i++)); do
  # Already live?
  STATUS="$(curl -sS --max-time 8 http://127.0.0.1:8080/api/fomo/status 2>/dev/null || true)"
  if echo "$STATUS" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get("enabled") and not d.get("needs_api_key") else 1)' 2>/dev/null; then
    log "Already live — triggering tick"
    curl -sS -X POST "http://127.0.0.1:8080/api/fomo/run" >/dev/null 2>&1 || true
    exit 0
  fi

  log "Try $i/$MAX_TRIES — register with Cope…"
  RESP="$(curl -sS --max-time 25 -X POST "https://api.cope.capital/v1/register" \
    -H "Content-Type: application/json" \
    -H "User-Agent: CyclicalTrader-FomoGhost/1.0" \
    -d '{"agent_name":"cyclical-trader-fomo-ghost","description":"Cyclical Trader FOMO Ghost top-30"}' 2>&1 || true)"

  KEY="$(python3 - <<'PY' "$RESP"
import json,sys
raw=sys.argv[1]
try:
    data=json.loads(raw)
except Exception:
    print("", end="")
    raise SystemExit(0)
print(str(data.get("api_key") or "").strip())
PY
)" || true

  if [[ -n "${KEY}" && "${KEY}" == cope_* ]]; then
    log "Got key ${KEY:0:14}… — applying"
    apply_key "$KEY"
    sleep 8
    for _ in 1 2 3 4 5 6; do
      STATUS="$(curl -sS --max-time 8 http://127.0.0.1:8080/api/fomo/status 2>/dev/null || true)"
      if echo "$STATUS" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if not d.get("needs_api_key") else 1)' 2>/dev/null; then
        curl -sS -X POST "http://127.0.0.1:8080/api/fomo/run" | tee -a "$LOG" >/dev/null
        log "FOMO Ghost LIVE"
        exit 0
      fi
      sleep 5
    done
    log "Key applied but status still needs_api_key — will keep retrying"
  else
    log "Cope still down: $(echo "$RESP" | tr '\n' ' ' | head -c 120)"
  fi

  # Also poke in-app register (same upstream; helps after code auto-register lands)
  curl -sS --max-time 20 -X POST "http://127.0.0.1:8080/api/fomo/register" \
    -H "Content-Type: application/json" \
    -d '{"agent_name":"cyclical-trader-fomo-ghost"}' >>"$LOG" 2>&1 || true

  sleep "$INTERVAL"
done

log "Gave up after ${MAX_TRIES} tries"
exit 1

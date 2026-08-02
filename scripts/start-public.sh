#!/usr/bin/env bash
# Start Cyclical Trader WWW on :8080 and expose a public internet URL.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

"$ROOT/scripts/build-www.sh"

cd "$ROOT/backend"
if [[ ! -d .venv/bin ]]; then
  rm -rf .venv
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p data
export CYCLICAL_DATABASE_PATH="${CYCLICAL_DATABASE_PATH:-data/trader.db}"

pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 1

echo "→ Starting WWW on http://0.0.0.0:8080 …"
uvicorn app.main:app --host 0.0.0.0 --port 8080 &
APP_PID=$!
cleanup() {
  kill "$APP_PID" 2>/dev/null || true
  [[ -n "${TUNNEL_PID:-}" ]] && kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8080/api/health >/dev/null; then
    break
  fi
  sleep 1
done
curl -sf http://127.0.0.1:8080/api/health >/dev/null
curl -sf http://127.0.0.1:8080/ >/dev/null

LIVE=$(curl -sf "http://127.0.0.1:8080/api/markets?region=all" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("live_count",0))')
if [[ "${LIVE:-0}" -lt 1 ]]; then
  echo "✗ Markets live_count=$LIVE — aborting public tunnel"
  exit 1
fi
echo "✓ Local WWW OK: http://127.0.0.1:8080 (markets live=$LIVE)"

CLOUDFLARED="${CLOUDFLARED:-/tmp/cloudflared}"
if [[ ! -x "$CLOUDFLARED" ]]; then
  echo "→ Downloading cloudflared…"
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
fi

URL_FILE="${ROOT}/PUBLIC_URL.txt"
LOG_FILE="${ROOT}/.tunnel.log"
rm -f "$URL_FILE" "$LOG_FILE"

echo "→ Opening public tunnel (internet)…"
"$CLOUDFLARED" tunnel --url http://127.0.0.1:8080 >"$LOG_FILE" 2>&1 &
TUNNEL_PID=$!

PUBLIC_URL=""
for _ in $(seq 1 60); do
  if [[ -f "$LOG_FILE" ]]; then
    PUBLIC_URL="$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | head -1 || true)"
  fi
  if [[ -n "$PUBLIC_URL" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "✗ Nie udało się uzyskać publicznego URL — log:"
  tail -40 "$LOG_FILE" || true
  exit 1
fi

echo "$PUBLIC_URL" > "$URL_FILE"
cat <<EOF

════════════════════════════════════════════════
  APLIKACJA W SIECI (otwórz na telefonie / PC):

  $PUBLIC_URL

  Superokazje:  $PUBLIC_URL/superokazje
  Rynki:        $PUBLIC_URL/rynki
  Whale API:    $PUBLIC_URL/api/whale-flows
  Live HTML:    $PUBLIC_URL/live

  URL zapisany w: PUBLIC_URL.txt
  Zatrzymanie: Ctrl+C
════════════════════════════════════════════════

EOF

# Keep process alive while tunnel + app run
wait "$TUNNEL_PID"

#!/usr/bin/env bash
# Start Cyclical Trader WWW (API + UI) on :8080 and expose a public phone URL.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Always rebuild SPA so phone never gets stale "brak danych" UI
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

# Stop previous instance on 8080 if any
pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 1

echo "→ Starting WWW app on http://0.0.0.0:8080 …"
uvicorn app.main:app --host 0.0.0.0 --port 8080 &
APP_PID=$!
trap 'kill $APP_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8080/api/health >/dev/null; then
    break
  fi
  sleep 1
done

curl -sf http://127.0.0.1:8080/api/health >/dev/null
curl -sf http://127.0.0.1:8080/ >/dev/null
# Smoke: markets must return live quotes
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

echo "→ Public tunnel (open this on your phone):"
exec "$CLOUDFLARED" tunnel --url http://127.0.0.1:8080

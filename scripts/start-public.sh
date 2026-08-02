#!/usr/bin/env bash
# Start Cyclical Trader WWW on :8080 and expose a public internet URL.
# Works on macOS (Apple Silicon / Intel) and Linux.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$ROOT/scripts/build-www.sh" ]]; then
  cat <<'EOF'
✗ Brak folderu scripts/ — jesteś na starej gałęzi (prawdopodobnie main).

Zrób TAK (skopiuj całość):

  cd ~
  rm -rf new_projekt
  git clone -b cursor/market-scanner-product-018e https://github.com/remi-cloud/new_projekt.git
  cd new_projekt
  chmod +x scripts/*.sh
  ./scripts/start-public.sh

EOF
  exit 1
fi

"$ROOT/scripts/build-www.sh"

cd "$ROOT/backend"
# Prefer python3.12/3.11 if present (3.14 sometimes breaks wheels)
PY=python3
if command -v python3.12 >/dev/null 2>&1; then PY=python3.12
elif command -v python3.11 >/dev/null 2>&1; then PY=python3.11
fi
echo "→ Python: $($PY --version 2>&1)"

if [[ ! -d .venv/bin ]]; then
  rm -rf .venv
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q --upgrade pip
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
echo "  (w LAN też: http://$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}'):8080 )"

# ── cloudflared for macOS / Linux ──────────────────────────────────────
CLOUDFLARED_DIR="${ROOT}/.tools"
mkdir -p "$CLOUDFLARED_DIR"
CLOUDFLARED="${CLOUDFLARED:-$CLOUDFLARED_DIR/cloudflared}"

download_cloudflared() {
  local os arch asset url tmp
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "$os-$arch" in
    darwin-arm64|darwin-aarch64)
      asset="cloudflared-darwin-arm64.tgz"
      ;;
    darwin-x86_64|darwin-amd64)
      asset="cloudflared-darwin-amd64.tgz"
      ;;
    linux-x86_64|linux-amd64)
      # bare binary on Linux
      url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
      echo "→ Downloading cloudflared (linux amd64)…"
      curl -fsSL "$url" -o "$CLOUDFLARED"
      chmod +x "$CLOUDFLARED"
      return 0
      ;;
    linux-arm64|linux-aarch64)
      url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
      echo "→ Downloading cloudflared (linux arm64)…"
      curl -fsSL "$url" -o "$CLOUDFLARED"
      chmod +x "$CLOUDFLARED"
      return 0
      ;;
    *)
      echo "✗ Nieznana platforma: $os $arch — zainstaluj cloudflared ręcznie: brew install cloudflared"
      return 1
      ;;
  esac

  # Prefer Homebrew binary on Mac if present
  if command -v cloudflared >/dev/null 2>&1; then
    CLOUDFLARED="$(command -v cloudflared)"
    echo "→ Używam systemowego cloudflared: $CLOUDFLARED"
    return 0
  fi

  url="https://github.com/cloudflare/cloudflared/releases/latest/download/${asset}"
  tmp="$(mktemp -d)"
  echo "→ Downloading cloudflared ($asset)…"
  curl -fsSL "$url" -o "$tmp/cf.tgz"
  tar -xzf "$tmp/cf.tgz" -C "$tmp"
  # tarball contains a single 'cloudflared' binary
  cp "$tmp/cloudflared" "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
  rm -rf "$tmp"
}

if [[ ! -x "$CLOUDFLARED" ]] || ! "$CLOUDFLARED" --version >/dev/null 2>&1; then
  download_cloudflared
fi
# If brew has it, prefer that
if command -v cloudflared >/dev/null 2>&1; then
  CLOUDFLARED="$(command -v cloudflared)"
fi
echo "→ cloudflared: $("$CLOUDFLARED" --version 2>&1 | head -1)"

URL_FILE="${ROOT}/PUBLIC_URL.txt"
LOG_FILE="${ROOT}/.tunnel.log"
rm -f "$URL_FILE" "$LOG_FILE"

echo "→ Opening public tunnel (internet)…"
"$CLOUDFLARED" tunnel --url http://127.0.0.1:8080 >"$LOG_FILE" 2>&1 &
TUNNEL_PID=$!

PUBLIC_URL=""
for _ in $(seq 1 90); do
  if [[ -f "$LOG_FILE" ]]; then
    PUBLIC_URL="$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | head -1 || true)"
  fi
  if [[ -n "$PUBLIC_URL" ]]; then
    break
  fi
  # bail early if process died
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "✗ Nie udało się uzyskać publicznego URL — log:"
  tail -50 "$LOG_FILE" || true
  exit 1
fi

echo "$PUBLIC_URL" > "$URL_FILE"
cat <<EOF

════════════════════════════════════════════════
  APLIKACJA W SIECI (telefon / dowolny internet):

  $PUBLIC_URL

  Superokazje:  $PUBLIC_URL/superokazje
  Rynki:        $PUBLIC_URL/rynki
  Whale API:    $PUBLIC_URL/api/whale-flows
  Live HTML:    $PUBLIC_URL/live

  Lokalnie:     http://127.0.0.1:8080
  URL zapisany: PUBLIC_URL.txt
  Stop:         Ctrl+C
════════════════════════════════════════════════

EOF

wait "$TUNNEL_PID"

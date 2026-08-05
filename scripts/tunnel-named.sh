#!/usr/bin/env bash
# Run a Cloudflare *named* tunnel (stable .ph domain) → local WWW :8080.
# Requires CLOUDFLARE_TUNNEL_TOKEN from Zero Trust dashboard (never commit).
# Docs: docs/DOMAIN-PH.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
LOG_FILE="${ROOT}/.tunnel-named.log"
URL_FILE="${ROOT}/PUBLIC_URL.txt"

ok() { echo "✓ $*"; }
info() { echo "→ $*"; }
fail() { echo "✗ $*" >&2; exit 1; }

# Load only needed keys from .env (gitignored) — avoid sourcing whole file
env_get() {
  local key="$1" file="$ROOT/.env" line val
  [[ -f "$file" ]] || return 0
  line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -1 || true)"
  [[ -n "$line" ]] || return 0
  val="${line#*=}"
  val="${val%\"}"
  val="${val#\"}"
  val="${val%\'}"
  val="${val#\'}"
  printf '%s' "$val"
}

TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-$(env_get CLOUDFLARE_TUNNEL_TOKEN)}"
PUBLIC_BASE="${CYCLICAL_PUBLIC_BASE_URL:-$(env_get CYCLICAL_PUBLIC_BASE_URL)}"

if [[ -z "$TOKEN" ]]; then
  cat <<'EOF' >&2
✗ Brak CLOUDFLARE_TUNNEL_TOKEN.

1. Cloudflare → Zero Trust → Networks → Tunnels → Create
2. Skopiuj token instalacji
3. export CLOUDFLARE_TUNNEL_TOKEN='…'
   albo dopisz do .env (nie commituj)

Szczegóły: docs/DOMAIN-PH.md
EOF
  exit 1
fi

CLOUDFLARED_DIR="${ROOT}/.tools"
mkdir -p "$CLOUDFLARED_DIR"
CLOUDFLARED="${CLOUDFLARED:-$CLOUDFLARED_DIR/cloudflared}"

download_cloudflared() {
  local os arch asset url tmp
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "${os}-${arch}" in
    darwin-arm64|darwin-aarch64) asset="cloudflared-darwin-arm64.tgz" ;;
    darwin-x86_64|darwin-amd64) asset="cloudflared-darwin-amd64.tgz" ;;
    linux-x86_64|linux-amd64)
      url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
      info "Downloading cloudflared (linux amd64)…"
      curl -fsSL "$url" -o "$CLOUDFLARED"
      chmod +x "$CLOUDFLARED"
      return 0
      ;;
    linux-aarch64|linux-arm64)
      url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
      info "Downloading cloudflared (linux arm64)…"
      curl -fsSL "$url" -o "$CLOUDFLARED"
      chmod +x "$CLOUDFLARED"
      return 0
      ;;
    *)
      fail "Nieznana platforma: $os $arch — brew install cloudflared"
      ;;
  esac
  url="https://github.com/cloudflare/cloudflared/releases/latest/download/${asset}"
  tmp="$(mktemp -d)"
  info "Downloading cloudflared ($asset)…"
  curl -fsSL "$url" | tar -xz -C "$tmp"
  cp "$tmp/cloudflared" "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
  rm -rf "$tmp"
}

if command -v cloudflared >/dev/null 2>&1; then
  CLOUDFLARED="$(command -v cloudflared)"
elif [[ ! -x "$CLOUDFLARED" ]] || ! "$CLOUDFLARED" --version >/dev/null 2>&1; then
  download_cloudflared
fi

info "cloudflared: $("$CLOUDFLARED" --version 2>&1 | head -1)"

# Ensure local origin is up
HEALTH="http://127.0.0.1:${PORT}/api/health"
CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH" || echo 000)"
if [[ "$CODE" != "200" ]]; then
  info "WWW na :${PORT} nie odpowiada — uruchamiam docker-up…"
  if [[ -x "$ROOT/scripts/docker-up.sh" ]]; then
    "$ROOT/scripts/docker-up.sh"
  else
    fail "Uruchom najpierw Docker WWW na porcie ${PORT}"
  fi
  for _ in $(seq 1 40); do
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH" || echo 000)"
    [[ "$CODE" == "200" ]] && break
    sleep 2
  done
  [[ "$CODE" == "200" ]] || fail "Origin http://127.0.0.1:${PORT} nadal niedostępny"
fi
ok "Origin healthy: $HEALTH"

# Stop previous named / quick tunnels for this project
pkill -f "$ROOT/.tools/cloudflared tunnel run" 2>/dev/null || true
pkill -f "cloudflared tunnel run --token" 2>/dev/null || true
pkill -f "$ROOT/.tools/cloudflared tunnel --url" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://127.0.0.1:${PORT}" 2>/dev/null || true

rm -f "$LOG_FILE"
info "Starting named tunnel (token from env)…"
"$CLOUDFLARED" tunnel run --token "$TOKEN" >"$LOG_FILE" 2>&1 &
TUNNEL_PID=$!

cleanup() {
  if [[ -n "${TUNNEL_PID:-}" ]] && kill -0 "$TUNNEL_PID" 2>/dev/null; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

sleep 3
if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
  echo "✗ cloudflared zakończył się od razu — log:" >&2
  tail -40 "$LOG_FILE" >&2 || true
  exit 1
fi

if [[ -n "$PUBLIC_BASE" ]]; then
  PUBLIC_BASE="${PUBLIC_BASE%/}"
  echo "$PUBLIC_BASE" >"$URL_FILE"
  info "Sprawdzam ${PUBLIC_BASE}/api/health …"
  PUBLIC_OK=0
  for _ in $(seq 1 30); do
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "${PUBLIC_BASE}/api/health" || echo 000)"
    if [[ "$CODE" == "200" ]]; then
      PUBLIC_OK=1
      break
    fi
    sleep 2
  done
  if [[ "$PUBLIC_OK" == "1" ]]; then
    ok "Public health 200"
  else
    echo "⚠ Tunel działa lokalnie, ale ${PUBLIC_BASE}/api/health ≠ 200 jeszcze."
    echo "  Sprawdź DNS (nameservery Cloudflare) i Public Hostname w Zero Trust."
    echo "  Log: $LOG_FILE"
  fi
  cat <<EOF

════════════════════════════════════════════════
  PRODUKCJA (.ph named tunnel)

  ${PUBLIC_BASE}
  Health:     ${PUBLIC_BASE}/api/health
  News:       ${PUBLIC_BASE}/news
  Agent:      ${PUBLIC_BASE}/agent

  Lokalnie:   http://127.0.0.1:${PORT}
  Log:        ${LOG_FILE}
  URL file:   PUBLIC_URL.txt
  Stop:       Ctrl+C  (Docker WWW zostaje)
════════════════════════════════════════════════

EOF
else
  cat <<EOF

════════════════════════════════════════════════
  Named tunnel uruchomiony (PID ${TUNNEL_PID})

  Ustaw CYCLICAL_PUBLIC_BASE_URL=https://TWOJA_DOMENA.ph
  w .env, żeby skrypt mógł zweryfikować health.

  Lokalnie: http://127.0.0.1:${PORT}
  Log:      ${LOG_FILE}
  Stop:     Ctrl+C
════════════════════════════════════════════════

EOF
fi

wait "$TUNNEL_PID" || true
trap - EXIT INT TERM

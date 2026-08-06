#!/usr/bin/env bash
# Start Cyclical Trader WWW (detached) + optional public Cloudflare *quick* tunnel.
# Hostname is random (*.trycloudflare.com) — demo only, not for social / branding.
# Production .ph domain: docs/DOMAIN-PH.md + ./scripts/tunnel-named.sh
# Local WWW survives tunnel failure / script exit.
# Works on macOS (Apple Silicon / Intel) and Linux.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
STOP_WWW_ON_EXIT="${STOP_WWW_ON_EXIT:-0}"

if [[ ! -f "$ROOT/scripts/build-www.sh" ]]; then
  cat <<'EOF'
✗ Brak folderu scripts/ — jesteś w złym katalogu lub starej kopii.

Zrób TAK (z katalogu tego repo):

  cd "/Users/remigiuszgoraus/Desktop/Cykliczny Trader Kar Digital"
  chmod +x scripts/*.sh
  ./scripts/start-public.sh

EOF
  exit 1
fi

lan_ip() {
  ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true
}

print_local() {
  local lan
  lan="$(lan_ip)"
  cat <<EOF

════════════════════════════════════════════════
  LOKALNE WWW (działa bez tunelu):

  http://127.0.0.1:${PORT}
  Agent:   http://127.0.0.1:${PORT}/agent
EOF
  if [[ -n "$lan" ]]; then
    cat <<EOF
  LAN:     http://${lan}:${PORT}
EOF
  fi
  cat <<'EOF'
════════════════════════════════════════════════
EOF
}

# Build + ensure local WWW is up (detached — not killed by this script's EXIT)
"$ROOT/scripts/build-www.sh"
"$ROOT/scripts/www-up.sh"
print_local

# ── cloudflared ─────────────────────────────────────────────
CLOUDFLARED_DIR="${ROOT}/.tools"
mkdir -p "$CLOUDFLARED_DIR"
CLOUDFLARED="${CLOUDFLARED:-$CLOUDFLARED_DIR/cloudflared}"

download_cloudflared() {
  local os arch asset url tmp
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "$os-$arch" in
    darwin-arm64|darwin-aarch64) asset="cloudflared-darwin-arm64.tgz" ;;
    darwin-x86_64|darwin-amd64) asset="cloudflared-darwin-amd64.tgz" ;;
    linux-x86_64|linux-amd64)
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
      echo "✗ Nieznana platforma: $os $arch — brew install cloudflared"
      return 1
      ;;
  esac

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
  cp "$tmp/cloudflared" "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
  rm -rf "$tmp"
}

if [[ ! -x "$CLOUDFLARED" ]] || ! "$CLOUDFLARED" --version >/dev/null 2>&1; then
  download_cloudflared || {
    echo "✗ cloudflared niedostępny — lokalne WWW zostaje włączone"
    exit 0
  }
fi
if command -v cloudflared >/dev/null 2>&1; then
  CLOUDFLARED="$(command -v cloudflared)"
fi
echo "→ cloudflared: $("$CLOUDFLARED" --version 2>&1 | head -1)"

URL_FILE="${ROOT}/PUBLIC_URL.txt"
LOG_FILE="${ROOT}/.tunnel.log"
# Kill previous quick tunnels from this project only
pkill -f "$ROOT/.tools/cloudflared tunnel --url" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://127.0.0.1:${PORT}" 2>/dev/null || true
rm -f "$URL_FILE" "$LOG_FILE"

echo "→ Opening public tunnel…"
"$CLOUDFLARED" tunnel --url "http://127.0.0.1:${PORT}" >"$LOG_FILE" 2>&1 &
TUNNEL_PID=$!

cleanup_tunnel() {
  if [[ -n "${TUNNEL_PID:-}" ]] && kill -0 "$TUNNEL_PID" 2>/dev/null; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
  if [[ "$STOP_WWW_ON_EXIT" == "1" ]]; then
    "$ROOT/scripts/www-down.sh" || true
  fi
}
# Only tunnel (and optional WWW) — never kill WWW by default
trap cleanup_tunnel EXIT INT TERM

PUBLIC_URL=""
for _ in $(seq 1 90); do
  if [[ -f "$LOG_FILE" ]]; then
    PUBLIC_URL="$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | head -1 || true)"
  fi
  if [[ -n "$PUBLIC_URL" ]]; then
    break
  fi
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "✗ Nie udało się uzyskać publicznego URL — lokalne WWW nadal działa"
  tail -30 "$LOG_FILE" || true
  print_local
  # Keep WWW; drop tunnel wait by exiting 0
  trap - EXIT INT TERM
  cleanup_tunnel
  exit 0
fi

# Verify public URL actually responds (DNS + origin)
PUBLIC_OK=0
for _ in $(seq 1 20); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$PUBLIC_URL/api/health" || echo 000)"
  if [[ "$CODE" == "200" ]]; then
    PUBLIC_OK=1
    break
  fi
  sleep 2
done

if [[ "$PUBLIC_OK" != "1" ]]; then
  echo "✗ Tunel zgłosił $PUBLIC_URL, ale HTTP health ≠ 200 (DNS/Cloudflare)."
  echo "  Lokalne WWW zostaje włączone — użyj LAN lub http://127.0.0.1:${PORT}"
  rm -f "$URL_FILE"
  print_local
  trap - EXIT INT TERM
  cleanup_tunnel
  exit 0
fi

echo "$PUBLIC_URL" >"$URL_FILE"
cat <<EOF

════════════════════════════════════════════════
  APLIKACJA W SIECI (telefon / dowolny internet):

  $PUBLIC_URL

  Dashboard:    $PUBLIC_URL/dashboard
  Rynki:        $PUBLIC_URL/rynki
  Portfel:      $PUBLIC_URL/portfel
  Agent:        $PUBLIC_URL/agent
  Health:       $PUBLIC_URL/api/health

  Lokalnie:     http://127.0.0.1:${PORT}
  LAN:          http://$(lan_ip):${PORT}
  URL zapisany: PUBLIC_URL.txt
  Stop tunelu:  Ctrl+C  (WWW lokalne zostaje)
  Stop WWW:     ./scripts/www-down.sh
════════════════════════════════════════════════

EOF

wait "$TUNNEL_PID" || true
# After tunnel ends, leave WWW running unless STOP_WWW_ON_EXIT=1
trap - EXIT INT TERM
if [[ "$STOP_WWW_ON_EXIT" == "1" ]]; then
  "$ROOT/scripts/www-down.sh" || true
fi

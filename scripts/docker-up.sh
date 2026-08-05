#!/usr/bin/env bash
# Start Docker Desktop engine (if needed) + docker compose WWW on :8080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
export PATH="/Applications/Docker.app/Contents/Resources/bin:${HOME}/.docker/bin:/usr/local/bin:${PATH}"

ok() { echo "✓ $*"; }
info() { echo "→ $*"; }
fail() { echo "✗ $*" >&2; exit 1; }

engine_ready() {
  docker info 2>/dev/null | grep -q "Server Version"
}

if ! command -v docker >/dev/null 2>&1; then
  fail "Brak docker CLI. Zainstaluj Docker Desktop z https://www.docker.com/products/docker-desktop/"
fi

if ! engine_ready; then
  info "Docker engine nie działa — uruchamiam Docker Desktop…"
  if [[ -d /Applications/Docker.app ]]; then
    open -a "/Applications/Docker.app"
  elif [[ -d "${HOME}/Desktop/Docker.app" ]]; then
    open -a "${HOME}/Desktop/Docker.app"
  else
    fail "Nie znaleziono Docker.app"
  fi
  # Prefer CLI start when available
  docker desktop start >/dev/null 2>&1 || true

  for i in $(seq 1 90); do
    if engine_ready; then
      ok "Docker engine gotowy"
      break
    fi
    sleep 2
    if [[ "$i" -eq 90 ]]; then
      fail "Engine nie wstał. W Docker Desktop: whale → Restart (albo Troubleshoot → Restart)."
    fi
  done
else
  ok "Docker engine już działa"
fi

cd "$ROOT"

# Free port if a non-docker process holds it
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if ! docker compose ps --status running 2>/dev/null | grep -q www; then
    info "Zwalniam port :$PORT (inny proces)…"
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t | xargs kill 2>/dev/null || true
    sleep 1
  fi
fi

info "docker compose up --build -d"
docker compose up --build -d

info "Czekam na /api/health…"
for i in $(seq 1 45); do
  if curl -sf --max-time 3 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    ok "WWW: http://127.0.0.1:${PORT}"
    curl -sf "http://127.0.0.1:${PORT}/api/health" | python3 -m json.tool 2>/dev/null || true
    exit 0
  fi
  sleep 2
done

docker compose logs --tail=40 www || true
fail "Kontener wystartował, ale health nie odpowiada — sprawdź: docker compose logs -f www"

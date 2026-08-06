#!/usr/bin/env bash
# Cyclical Trader — start z Terminala na Macu
# Użycie:  ./scripts/mac-start.sh
set -eo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=_mac_python.sh
source "$ROOT/scripts/_mac_python.sh"
ensure_brew_path || true
resolve_mac_python || { echo "Brak Python 3 — brew install python@3.12"; exit 1; }
check_python_version || { echo "Python ≥ 3.11 wymagany (masz $($PYTHON_BIN --version)) — brew install python@3.12"; exit 1; }

PORT="${PORT-8080}"
OPEN_BROWSER="${OPEN_BROWSER-1}"

RED=$'\033[31m'
GRN=$'\033[32m'
YLW=$'\033[33m'
BLU=$'\033[34m'
RST=$'\033[0m'

ok()   { echo "${GRN}✓${RST} $*"; }
warn() { echo "${YLW}!${RST} $*"; }
fail() { echo "${RED}✗${RST} $*"; exit 1; }
info() { echo "${BLU}→${RST} $*"; }

echo ""
echo "=== Cyclical Trader — macOS / Terminal ==="
echo ""

# ── Wymagania ──────────────────────────────────────────────
need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Brakuje: $1 — zainstaluj (Homebrew): $2"
  fi
}

need_cmd node    "brew install node"
need_cmd npm     "brew install node"

ok "Python $($PYTHON_BIN --version | awk '{print $2}')"
ok "Node $(node -v) / npm $(npm -v)"

# ── Port zajęty? ────────────────────────────────────────────
if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    if command -v curl >/dev/null 2>&1 && curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
      ok "Serwer już działa na http://localhost:${PORT}"
      info "Execution agent: http://localhost:${PORT}/execution"
      info "Zatrzymaj: ./scripts/mac-stop.sh"
      if [ "$OPEN_BROWSER" = "1" ] && command -v open >/dev/null 2>&1; then
        open "http://localhost:${PORT}/execution"
      fi
      exit 0
    fi
    warn "Port $PORT już zajęty (inny proces)."
    info "Zatrzymaj:  ./scripts/mac-stop.sh"
    info "Albo port:  PORT=8090 ./scripts/mac-start.sh"
    fail "Nie mogę wystartować na :$PORT"
  fi
fi

# ── Frontend → backend/static ───────────────────────────────
NEED_BUILD=0
if [ ! -f "backend/static/index.html" ]; then
  NEED_BUILD=1
elif [ -n "$(find frontend/src -newer backend/static/index.html 2>/dev/null | head -1)" ]; then
  NEED_BUILD=1
  warn "Źródła frontendu nowsze niż static — przebuduję."
fi

if [ "$NEED_BUILD" = "1" ]; then
  info "Budowanie frontendu (może potrwać 1–2 min)…"
  ./scripts/build-www.sh
  ok "Frontend w backend/static"
else
  ok "Frontend już zbudowany"
fi

# ── Python venv ─────────────────────────────────────────────
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  info "Tworzenie środowiska Python (.venv)…"
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
info "Instalacja zależności…"
pip install -q --upgrade pip
if ! pip install -q -r requirements.txt; then
  warn "pip install nieudany — często pomaga: brew install curl openssl@3"
  warn "Potem: rm -rf .venv && ./scripts/mac-start.sh"
  fail "Nie udało się zainstalować zależności Python"
fi
ok "Backend gotowy"

# ── Portfel (tylko lokalny portfolio.db — bez wklejania backupów z testów) ──
PF_DIR="data/baza_portfela"
PF_DB="$PF_DIR/portfolio.db"
mkdir -p "$PF_DIR"
if [ -f "$PF_DB" ]; then
  ok "Portfel lokalny: $PF_DB"
else
  ok "Nowy portfel — start z kontem 1 000 000 PLN (pozycje tylko z Twoich zleceń)"
fi

# ── Start ───────────────────────────────────────────────────
echo ""
ok "Aplikacja:  http://localhost:${PORT}"
info "API docs:    http://localhost:${PORT}/docs"
info "Zatrzymanie: Ctrl+C  albo  ./scripts/mac-stop.sh"
echo ""

if [ "$OPEN_BROWSER" = "1" ] && command -v open >/dev/null 2>&1; then
  (sleep 1.5 && open "http://localhost:${PORT}") &
fi

# 0.0.0.0 — dostęp z telefonu w LAN (nie tylko localhost)
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

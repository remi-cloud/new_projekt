#!/usr/bin/env bash
# Cyclical Trader — start z Terminala na Macu
# Użycie:  ./scripts/mac-start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-8080}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"

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

need_cmd python3 "brew install python"
need_cmd node    "brew install node"
need_cmd npm     "brew install node"

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(echo "$PY_VER" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VER" | cut -d. -f2)"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  fail "Potrzebny Python ≥ 3.11 (masz $PY_VER).: brew install python@3.12"
fi
ok "Python $PY_VER"
ok "Node $(node -v) / npm $(npm -v)"

# ── Port zajęty? ────────────────────────────────────────────
if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    warn "Port $PORT już zajęty."
    info "Zatrzymaj stary proces:  ./scripts/mac-stop.sh"
    info "Albo inny port:          PORT=8090 ./scripts/mac-start.sh"
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
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
info "Instalacja zależności…"
pip install -q -r requirements.txt
ok "Backend gotowy"

# ── Backup portfela (pierwszy start) ────────────────────────
PF_DIR="data/baza_portfela"
PF_DB="$PF_DIR/portfolio.db"
BACKUP="$ROOT/backups/portfolio_latest.sqlite"
mkdir -p "$PF_DIR"
if [ ! -f "$PF_DB" ] && [ -f "$BACKUP" ]; then
  cp "$BACKUP" "$PF_DB"
  ok "Przywrócono portfel z backups/portfolio_latest.sqlite"
elif [ -f "$PF_DB" ]; then
  ok "Portfel lokalny: $PF_DB"
else
  warn "Brak backupu — start z pustym kontem 1 000 000 PLN"
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

exec uvicorn app.main:app --host 127.0.0.1 --port "$PORT"

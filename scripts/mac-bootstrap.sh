#!/usr/bin/env bash
# Cyclical Trader — pełny setup na Macu (foldery → narzędzia → git → dysk)
# Uruchom w Terminalu:
#   bash scripts/mac-bootstrap.sh
# albo (przed clone) skopiuj komendy z docs/MAC-SETUP.md
set -euo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLU=$'\033[34m'; BLD=$'\033[1m'; RST=$'\033[0m'
ok()   { echo "${GRN}✓${RST} $*"; }
warn() { echo "${YLW}!${RST} $*"; }
fail() { echo "${RED}✗${RST} $*"; exit 1; }
step() { echo ""; echo "${BLD}${BLU}▶ $*${RST}"; }
info() { echo "  $*"; }

# ── Gdzie na dysku ──────────────────────────────────────────
PROJECTS_DIR="${PROJECTS_DIR:-$HOME/Projects}"
REPO_NAME="${REPO_NAME:-new_projekt}"
REPO_URL="${REPO_URL:-https://github.com/remi-cloud/new_projekt.git}"
BRANCH="${BRANCH:-cursor/paper-trading-21d6}"
PROJECT_DIR="${PROJECT_DIR:-$PROJECTS_DIR/$REPO_NAME}"

echo ""
echo "${BLD}=== Cyclical Trader — bootstrap macOS ===${RST}"
echo "  Folder projektu: ${PROJECT_DIR}"
echo "  Branch:          ${BRANCH}"
echo ""

# ── 1. Foldery ──────────────────────────────────────────────
step "1/6  Foldery na dysku"
mkdir -p "$PROJECTS_DIR"
ok "Utworzono / istnieje: $PROJECTS_DIR"

# ── 2. Xcode Command Line Tools (git, clang) ────────────────
step "2/6  Narzędzia systemowe (Xcode CLT)"
if xcode-select -p >/dev/null 2>&1; then
  ok "Xcode Command Line Tools już zainstalowane"
else
  warn "Instalacja Xcode Command Line Tools — pojawi się okno systemowe."
  warn "Kliknij Install, poczekaj, potem uruchom ten skrypt PONOWNIE."
  xcode-select --install 2>/dev/null || true
  fail "Dokończ instalację CLT i uruchom: bash scripts/mac-bootstrap.sh"
fi
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Brak polecenia: $1"
}
need_cmd git
ok "git $(git --version | awk '{print $3}')"

# ── 3. Homebrew ─────────────────────────────────────────────
step "3/6  Homebrew"
if command -v brew >/dev/null 2>&1; then
  ok "Homebrew $(brew --version | head -1)"
else
  info "Instaluję Homebrew (może poprosić o hasło)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Apple Silicon
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    if ! grep -q 'homebrew/bin/brew shellenv' "$HOME/.zprofile" 2>/dev/null; then
      echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
  fi
  # Intel
  if [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  command -v brew >/dev/null 2>&1 || fail "Homebrew zainstalowany, ale nie w PATH — otwórz nowe okno Terminala i uruchom skrypt ponownie."
  ok "Homebrew zainstalowany"
fi

# ── 4. Python + Node ────────────────────────────────────────
step "4/6  Python 3.12 + Node.js"
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
brew list node >/dev/null 2>&1 || brew install node

# Prefer python3.12 if available
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.12)"
elif [ -x /opt/homebrew/opt/python@3.12/bin/python3.12 ]; then
  PYTHON_BIN="/opt/homebrew/opt/python@3.12/bin/python3.12"
elif [ -x /usr/local/opt/python@3.12/bin/python3.12 ]; then
  PYTHON_BIN="/usr/local/opt/python@3.12/bin/python3.12"
else
  PYTHON_BIN="$(command -v python3)"
fi

ok "Python: $($PYTHON_BIN --version)  ($PYTHON_BIN)"
ok "Node:   $(node -v)  / npm $(npm -v)"

# ── 5. Clone / pull na dysk ─────────────────────────────────
step "5/6  Pobieranie projektu na dysk"
if [ -d "$PROJECT_DIR/.git" ]; then
  info "Repo już istnieje — pobieram najnowsze zmiany…"
  git -C "$PROJECT_DIR" fetch origin
  git -C "$PROJECT_DIR" checkout "$BRANCH"
  git -C "$PROJECT_DIR" pull --ff-only origin "$BRANCH" || git -C "$PROJECT_DIR" pull origin "$BRANCH"
  ok "Zaktualizowano: $PROJECT_DIR"
else
  if [ -e "$PROJECT_DIR" ]; then
    fail "Ścieżka istnieje, ale to nie jest git repo: $PROJECT_DIR"
  fi
  info "Klonuję $REPO_URL → $PROJECT_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
  ok "Zapisano na dysku: $PROJECT_DIR"
fi

chmod +x "$PROJECT_DIR"/scripts/*.sh 2>/dev/null || true

# ── 6. Zależności projektu + frontend + portfel ─────────────
step "6/6  Instalacja zależności projektu"
cd "$PROJECT_DIR"

info "Budowanie frontendu → backend/static …"
./scripts/build-www.sh

cd "$PROJECT_DIR/backend"
if [ ! -d ".venv" ]; then
  info "Tworzenie .venv …"
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
ok "Python venv + requirements"

mkdir -p data/baza_portfela
if [ ! -f data/baza_portfela/portfolio.db ] && [ -f "$PROJECT_DIR/backups/portfolio_latest.sqlite" ]; then
  cp "$PROJECT_DIR/backups/portfolio_latest.sqlite" data/baza_portfela/portfolio.db
  ok "Portfel przywrócony z backupu"
fi

# Zapisz helper: ścieżka do projektu
MARKER="$HOME/.cyclical-trader-path"
echo "$PROJECT_DIR" > "$MARKER"
ok "Ścieżka zapisana w $MARKER"

echo ""
echo "${GRN}${BLD}Gotowe — projekt jest na dysku.${RST}"
echo ""
echo "  Folder:  ${PROJECT_DIR}"
echo "  Start:   cd \"$PROJECT_DIR\" && ./scripts/mac-start.sh"
echo "  Stop:    ./scripts/mac-stop.sh"
echo ""
echo "Uruchomić serwer teraz? [t/N]"
read -r ANSWER || ANSWER="n"
case "$ANSWER" in
  t|T|y|Y|tak|Tak)
    exec ./scripts/mac-start.sh
    ;;
  *)
    echo "OK. Jak będziesz gotowy:"
    echo "  cd \"$PROJECT_DIR\" && ./scripts/mac-start.sh"
    ;;
esac

#!/usr/bin/env bash
# Diagnostyka — wklej wynik do czatu jeśli coś nie działa
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Cyclical Trader — mac-doctor ==="
echo "Data: $(date)"
echo "Mac:  $(sw_vers -productVersion 2>/dev/null || uname -srm)"
echo "Projekt: $ROOT"
echo ""

check() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "OK  $1 → $($1 --version 2>&1 | head -1)"
  else
    echo "BRAK $1"
  fi
}

check git
check brew
check node
check npm
check python3
check python3.12
check lsof

echo ""
echo "--- Python ---"
for p in python3.12 python3 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
  if command -v "$p" >/dev/null 2>&1 || [ -x "$p" ]; then
    echo "  $p → $($p --version 2>&1)"
  fi
done

echo ""
echo "--- Pliki projektu ---"
for f in scripts/mac-start.sh scripts/mac-bootstrap.sh scripts/build-www.sh backend/requirements.txt frontend/package.json backups/portfolio_latest.sqlite; do
  if [ -e "$f" ]; then echo "OK  $f"; else echo "BRAK $f"; fi
done

echo ""
echo "--- Frontend static ---"
if [ -f backend/static/index.html ]; then
  echo "OK  backend/static/index.html"
  ls -la backend/static/assets/*.js 2>/dev/null | tail -1 || echo "BRAK JS w static/"
else
  echo "BRAK backend/static — uruchom: ./scripts/build-www.sh"
fi

echo ""
echo "--- Python venv ---"
if [ -d backend/.venv/bin/python ]; then
  backend/.venv/bin/python --version
  backend/.venv/bin/pip show curl_cffi fastapi uvicorn 2>/dev/null | rg '^(Name|Version):' || echo "Brak pakietów w venv"
else
  echo "BRAK backend/.venv — uruchom: ./scripts/mac-bootstrap.sh"
fi

echo ""
echo "--- Port 8080 ---"
if lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ZAJĘTY:"
  lsof -nP -iTCP:8080 -sTCP:LISTEN
else
  echo "Wolny"
fi

echo ""
echo "--- Test importu backendu ---"
if [ -x backend/.venv/bin/python ]; then
  backend/.venv/bin/python -c "
import sys
print('python', sys.version)
try:
    import curl_cffi
    print('curl_cffi OK', curl_cffi.__version__)
except Exception as e:
    print('curl_cffi FAIL:', e)
try:
    from app.main import app
    print('app.main OK')
except Exception as e:
    print('app.main FAIL:', e)
" 2>&1 || true
fi

echo ""
echo "=== Koniec — skopiuj cały output powyżej ==="

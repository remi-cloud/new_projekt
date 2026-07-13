#!/usr/bin/env bash
# Prosty skrypt startowy — uruchamia aplikację WWW na http://localhost:8080
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Cyclical Trader — start ==="

# Frontend
if [ ! -d "backend/static" ] || [ -z "$(ls -A backend/static 2>/dev/null)" ]; then
  echo "Budowanie frontendu (pierwsze uruchomienie)..."
  ./scripts/build-www.sh
fi

# Backend venv
cd backend
if [ ! -d ".venv" ]; then
  echo "Tworzenie środowiska Python..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "Aplikacja dostępna pod: http://localhost:8080"
echo "Naciśnij Ctrl+C aby zatrzymać"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8080

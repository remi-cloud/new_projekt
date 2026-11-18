#!/usr/bin/env bash
# Debut developing environment — one command: build SPA + run WWW on :8080
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

"$ROOT/scripts/install.sh"
"$ROOT/scripts/build-www.sh"

# shellcheck source=load-dotenv.sh
source "$ROOT/scripts/load-dotenv.sh"
load_dotenv "$ROOT/.env"

cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
mkdir -p data/baza_portfela
export CYCLICAL_DATABASE_PATH="${CYCLICAL_DATABASE_PATH:-data/trader.db}"

echo "→ Cyclical Trader WWW → http://127.0.0.1:8080"
exec uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port 8080 --reload

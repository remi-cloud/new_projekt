# Jutro — domena · GitHub · Docker

Snapshot lokalny projektu Cykliczny Trader · Kar Digital.

## Co jest w tym folderze
- Kod backend + frontend (bez `node_modules` / `.venv` — zainstalujesz na świeżo)
- `backend/static` — zbudowane WWW
- `backend/data` — lokalne dane / DB jeśli były
- Skrypty: `scripts/www-up.sh`, `audit.sh`, `start-public.sh`, `build-www.sh`

## Szybki start lokalnie
```bash
cd "/ścieżka/do/tego/folderu"
chmod +x scripts/*.sh
./scripts/mac-bootstrap.sh   # lub: python3.12 -m venv backend/.venv && pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
./scripts/build-www.sh
./scripts/www-up.sh
# http://127.0.0.1:8080
```

## Plan na jutro
1. **Docker lokalnie** — zobacz [`docs/DOCKER.md`](docs/DOCKER.md): `docker compose up --build -d`
2. **GitHub** — push (nie commituj `.env` z sekretami)
3. **VPS / Lightsail** — ten sam `docker compose up -d`
4. **Domena KAR Digital** — reverse proxy → :8080, HTTPS, link z www firmowej
5. **Env produkcyjny** — `CYCLICAL_*` z `.env.example` (AI: LLM7 bez klucza lub OpenAI)

## Ważne ścieżki
- Agent AI: `/agent`
- Narzędzia / Singularity: `/narzedzia`, `/narzedzia/singularity`
- Superokazje: `/superokazje`
- Health: `/api/health`

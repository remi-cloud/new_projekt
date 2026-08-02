# Cyclical Trader — agent notes

## Cursor Cloud specific instructions

- Product is a **single-port WWW** on `:8080` (FastAPI serves React from `backend/static`).
- After code changes that touch `frontend/`, run `./scripts/build-www.sh` before testing the UI.
- Preferred start: `./scripts/dev-up.sh` (install → build SPA → uvicorn).
- Tests: `cd backend && source .venv/bin/activate && pytest -q`
- Public phone access: `./scripts/start-public.sh` (Cloudflare quick tunnel).
- Strategy engines are internal; public UI/API must only expose **Model Alpha / Model Beta** (never bitcoin/presidential cycle naming in JSON field names or copy).
- Superokazje heatmap: green = long liquidations (below price), red = short liquidations (above price); intensity = shade.

## Layout

```
backend/     FastAPI + scanners + SQLite
frontend/    React + Vite
scripts/     install / build-www / dev-up / start-public
.cursor/     Cloud debut environment (environment.json)
```

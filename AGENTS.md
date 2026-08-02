# AGENTS.md

## Cursor Cloud specific instructions

Cyclical Trader is a single product with two services in this repo:

- `backend/` — FastAPI + APScheduler + SQLite market scanner (Python 3.12). External data sources: CoinGecko (crypto/BTC ATH) and Yahoo Finance chart API (traditional markets). Egress is unrestricted in this environment, so both work.
- `frontend/` — React 19 + TypeScript + Vite 6 SPA. In dev it proxies `/api` to the backend on `http://localhost:8000` (see `frontend/vite.config.ts`).

Standard commands live in `README.md` (sections "Lokalnie (dev)" and "Testy") and `package.json`/`render.yaml`. Prefer those; notes below are only the non-obvious caveats.

### Running the services (dev)

- Backend (from `backend/`, venv activated): `uvicorn app.main:app --reload --port 8000`
  - The Python venv is at `backend/.venv` (created by the startup update script). Activate with `. backend/.venv/bin/activate` or call binaries directly, e.g. `backend/.venv/bin/uvicorn ...`.
  - On startup, the app runs `init_db()` then an immediate scan and starts the APScheduler background scanner. SQLite lives at `backend/data/trader.db` (gitignored); `data/` is created automatically.
- Frontend (from `frontend/`): `npm run dev` (Vite on port 5173). Use `npm run dev -- --host` to expose it on the VM's network interface for browser testing.
- Both dev servers must run together for the UI to load data (the frontend has no data of its own; it calls the proxied API).

### Testing / lint / build

- Backend tests: from `backend/` with the venv active, run `pytest -q` (config in `backend/pytest.ini`, `pythonpath=.`). No network needed — tests cover pure cycle/scanner/db logic.
- Frontend has no separate lint script. Type-checking is the lint gate: `npx tsc --noEmit` (also part of `npm run build`, which is `tsc --noEmit && vite build`).
- Single-container prod-style build (API + built SPA on one port 8080) is via `docker compose up --build` or `scripts/build-www.sh`; not needed for day-to-day dev.

### Non-obvious gotchas

- The manual "Skanuj teraz" scan button gives little visible UI feedback; confirm a scan actually ran via `GET /api/health` (`last_scan_at`) or `POST /api/scan` (returns `scanned`, counts, and detected `changes`).
- The watchlist table is sorted (not append-order), so a newly added symbol appears in its sorted position, not at the bottom. Verify additions via the count badge or `GET /api/watchlist`.
- Yahoo Finance can intermittently return HTTP 429 to a single request; the scanner tolerates per-quote failures (logs a warning, skips that asset) so the dashboard still renders from whatever succeeded (crypto quotes come from CoinGecko).

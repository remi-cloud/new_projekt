# Cyclical Trader · Kar Digital — agent notes

## Cursor Cloud / local debut

- Product is a **single-port WWW** on `:8080` (FastAPI serves React from `backend/static`).
- Brand: **Cykliczny Trader · Kar Digital** + `KarDigitalLogo` (Saturn/Earth) — never the scanner “CT” mark.
- After frontend changes: `./scripts/build-www.sh`
- Preferred start: `./scripts/dev-up.sh` or `./scripts/mac-start.sh`
- Public phone URL: `./scripts/start-public.sh` → `PUBLIC_URL.txt`
- Smoke: `./scripts/audit.sh`
- Cycles in UI stay **explicit** (Bitcoin / presidential / regional). Finance Agent tools include Superokazje / whale / Singularity.
- Desk: `/superokazje` (3D liq heatmap), `/narzedzia/singularity`

## Layout

```
backend/     FastAPI + cycles + scanners + agents (Singularity) + paper + AI
frontend/    React + Vite + Kar Digital brand
scripts/     install / build-www / dev-up / start-public / mac-* / audit
```

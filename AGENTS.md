# Cyclical Trader · Kar Digital — agent notes

## Cursor Cloud / local debut

- Product is a **single-port WWW** on `:8080` (FastAPI serves React from `backend/static`).
- Brand: **Cykliczny Trader · Kar Digital** + `KarDigitalLogo` (Saturn/Earth) — never the scanner “CT” mark.
- After frontend changes: `./scripts/build-www.sh`
- **WWW start (agents + prod):** `./scripts/www-up.sh` — detached, pidfile, survives shell exit
- **WWW stop:** `./scripts/www-down.sh`
- **WWW down / smoke fail:** `./scripts/audit-fix.sh` (rebuild + www-up + retry audit)
- Dev foreground (terminal only): `./scripts/dev-up.sh` or `./scripts/mac-start.sh` — **never pipe** `mac-start` (`| tail` kills uvicorn via SIGPIPE)
- Restart: `./scripts/mac-restart.sh` → `www-down` + `www-up`
- Public phone URL: `./scripts/start-public.sh` → `PUBLIC_URL.txt`
- Smoke: `./scripts/audit.sh`
- Cycles in UI stay **explicit** (Bitcoin / presidential / regional). Finance Agent tools include Superokazje / whale / Singularity.
- Desk: `/superokazje` (3D liq heatmap), `/narzedzia/singularity`
- **Asymmetric bets** is a hard desk guideline for the Finance Agent: knowledge seed `ASYMMETRIC_BETS_KNOWLEDGE`, `SYSTEM_PROMPT` RULES, and critic check — pull R:R / size / super_score from tools and state ACCEPT/REJECT/WAIT (thresholds: ≥2 / ≥1.4 / ≥1 / &lt;1; `is_super` ≥72).
- **FOMO Ghost** (`/fomo`): top-30 fomo.family portfolios via Cope Capital + Family bags + Telegram listen — see `docs/FOMO-GHOST.md`; env `CYCLICAL_COPE_API_KEY`, `CYCLICAL_FOMO_TELEGRAM_CHAT_IDS`.
- **Axiom** (`/axiom`): Pulse markets + all positions (FOMO Family bags + optional wallets + Kar Digital firm wallet) — see `docs/AXIOM.md`; env `CYCLICAL_KAR_DIGITAL_WALLET`.
- **Meme Universe · Launch Scout** (`/launch`, **flagship**): Seed (~$200 MC) + Pump top-30 traders + **Wallet Scout** (token + buy/sell + open bags) + **Dex Arena** (per-DEX boards + whale_boost) + Robinhood chain + multi-DEX + whispers — token clicks open Axiom (chain-aware) / DexScreener / Pump fallbacks; whole-DEX home links on lanes; see `docs/LAUNCH-SCOUT.md`.
- **Wallet Scout** (P0 under Launch): net bags from buy+sell events + RPC holdings for top-N wallets; Finance tool `get_wallet_scout`.
- **Dex Arena** (P1 under Launch): per-DEX best picks weighted by Wallet Scout; Finance tool `get_dex_arena`.
- **Session Clock** (P2): Asia/EU/US UTC timetable + meme heatmap + BTC/SOL hourly log-returns; Finance tool `get_session_clock` — see `docs/SESSION-CLOCK.md`.

## Multi-agent priorities (coordinator)

| Priority | Modules |
|----------|---------|
| **P0** | LinkGuard (terminal URLs), **Wallet Scout** (Pump wallet bags / buy·sell), TickWatchdog (`scripts/audit.sh`) |
| **P1** | Launch Scout, **Dex Arena**, Axiom, FOMO Ghost |
| **P2** | Singularity, Finance Agent, Execution Agent, Binance AI bridge, **Session Clock** |
| **P3** | Newsletter, Business leads, Alerts |

Health: `GET /api/coordinator/health` (tick every `CYCLICAL_COORDINATOR_INTERVAL_SECONDS`, default 300s).

Binance AI bridge (offline radar + whale; optional remote bot):

```env
CYCLICAL_BINANCE_AI_BOT_URL=
CYCLICAL_BINANCE_AI_BOT_KEY=
```

Finance Agent tool: `get_binance_ai_support` (radar) + `get_binance_portfolio_sync` (paper vs Binance drift).

See `docs/BINANCE-BOT.md` for portfolio ↔ Binance Trade integration.

## Scoring thresholds (desk map)

| Layer | Metric | Notes |
|-------|--------|-------|
| Launch Scout | `score` (rank) + `confidence` (data completeness) | Tag bonus capped at +40; filters migrated/dex_paid unchanged |
| Superokazje | `super_score` 0–100; `is_super` ≥72 | R:R from ATR/structure SL-TP — **not** from cycle confidence; cycle weight 0.35 |
| Asymmetric bets | R:R ≥2 ACCEPT / ≥1.4 OK / ≥1 WAIT / &lt;1 REJECT | Critic **hard-fails** ACCEPT when tool R:R &lt; 1 |
| Execution size | conf &lt;75 → 0.5×; 75–85 → 1×; ≥85 → 1.25× | R:R 1–1.4 → extra 0.5×; R:R &lt;1 → skip proposal |

## Layout

```
backend/     FastAPI + cycles + scanners + agents (Singularity) + paper + AI
frontend/    React + Vite + Kar Digital brand
scripts/     install / build-www / dev-up / start-public / mac-* / audit
```

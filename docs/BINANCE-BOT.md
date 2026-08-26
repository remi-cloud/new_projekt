# Binance AI BOT — portfel ↔ Binance Trade

Bridge between **Kar Digital paper portfolio** (`/portfel`) and **Binance Spot** — drift detection, trade deep links, dry-run proposals.

## Flow

1. **Paper book** — simulated positions on `/portfel`
2. **Binance Spot** — read-only balances via API keys (BTC/ETH/SOL catalog)
3. **Bridge** — compares quantities, flags drift ≥ `CYCLICAL_BINANCE_DRIFT_ALERT_PCT`
4. **Binance AI BOT** — tick every 2 min: drift check + BUY signal proposals → execution table (`broker=binance`, dry-run default)

Meme/Solana positions from Launch Scout and Axiom are **not** synced to Binance spot — different universe.

## Env

```env
CYCLICAL_BINANCE_API_KEY=
CYCLICAL_BINANCE_API_SECRET=
CYCLICAL_BINANCE_AI_BOT_ENABLED=true
CYCLICAL_BINANCE_AI_BOT_INTERVAL_SECONDS=120
CYCLICAL_BINANCE_AI_BOT_DRY_RUN=true
CYCLICAL_BINANCE_AI_BOT_MIRROR_PAPER=true
CYCLICAL_BINANCE_DRIFT_ALERT_PCT=15
```

Optional radar/whale context (existing bridge):

```env
CYCLICAL_BINANCE_AI_BOT_URL=
CYCLICAL_BINANCE_AI_BOT_KEY=
```

## API

| Endpoint | Opis |
|----------|------|
| `GET /api/portfolio/binance-sync` | connected, paper vs Binance, drift, trade_links |
| Finance Agent `get_binance_portfolio_sync` | same snapshot (cached 2 min) |
| Finance Agent `get_binance_ai_support` | CZ radar + whale bias |

## Safety

- Default: **read-only sync** + **dry-run** proposals only
- Live Binance orders require `CYCLICAL_BINANCE_AI_BOT_DRY_RUN=false` + execution approval flow
- API keys: trade permission OK; **no withdraw**
- Keys never exposed in frontend or logs

## UI

`/portfel` — **Binance AI BOT** banner: status (connected / no keys / dry-run), drift count, **Trade on Binance** links per crypto symbol.

## Start WWW

Production WWW on `:8080` must use detached start (survives shell exit):

```bash
./scripts/www-down.sh
./scripts/build-www.sh   # after frontend changes
./scripts/www-up.sh
./scripts/audit.sh
```

If the browser shows connection refused: `./scripts/audit-fix.sh` (rebuild + www-up + retry).

**Do not** pipe foreground start (`mac-start | tail`) — SIGPIPE kills uvicorn.

Restart shortcut: `./scripts/mac-restart.sh` → `www-down` + `www-up`.

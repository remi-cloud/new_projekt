# Meme Universe · Launch Scout (flagship)

**#1 desk** of Cyclical Trader · Kar Digital. Route: `/launch`.

> Who owns the memes owns the universe.

Agent poluje na **wejście pod pompę z poziomu ~$200 MC** (Seed), zanim tip dojdzie do milionów (np. Mushu @ ~$1.8M jest poza deskiem).

FOMO Ghost (`/fomo`) zostaje osobno (smart-money bags).

## Progi MC

| Tier | Market cap |
|------|------------|
| **Seed** | &lt; $2k (strefa ~$200) |
| **Fresh** | &lt; $100k |
| **Early** | &lt; $500k |
| **Watch** | &lt; $1M |

Liquidity floor domyślnie **$1k**; **Seed / Pump bonding** mogą przejść bez liq. Kandydaci ≥ $1M są odrzucani.

## Źródła

1. **DexScreener** — profiles, boosts, meme/ultra-early search (`new`, `launch`, `bonding`, …) across many chains.
2. **GeckoTerminal** — new pools (best-effort).
3. **Pump.fun** — ultra-early Solana coins (prefer Seed-band MC).
4. **Pump top-30 traders** — agregacja early buyers z public trades (+ opcjonalnie Solana Tracker PnL gdy `CYCLICAL_SOLANA_TRACKER_API_KEY`). Tag `pump_trader`.
5. **BNB Chain · 4meme** — public token search API (`four.meme`) — bonding → Pancake graduation. Tags `4meme`, `bsc`, `bonding` / `pancake`.
6. **BNB Chain · Flap** — DexScreener `flapsh` pairs on BSC. Tags `flap`, `bsc`.
7. **BNB Chain · PancakeSwap** — DexScreener BSC pancake pairs (early tape). Tag `pancake`.
8. **Robinhood chain** — DexScreener `chain=robinhood` early pairs (nie brokerage API). Tagi `rh_chain` / `rh_trader`.
9. **Bitcoin** — DexScreener chain `bitcoin` gdy dostępny (nie CEX spot BTC).
10. **Binance radar** — Google News RSS (CZ / listing / Alpha) — **nie** DEX bonding.
11. **Elon / CZ whispers** — RSS + opcjonalnie X.
12. **FOMO overlay** — lokalne bag-buys → tag `fomo_bag`.

Łańcuchy (domyślnie): solana, base, ethereum, bsc, arbitrum, polygon, avalanche, optimism, blast, tron, sui, bitcoin, robinhood.

## Env

```env
CYCLICAL_LAUNCH_SCOUT_ENABLED=true
CYCLICAL_LAUNCH_SCOUT_INTERVAL_SECONDS=60
CYCLICAL_LAUNCH_SCOUT_MAX_MC=1000000
CYCLICAL_LAUNCH_SCOUT_SEED_MC=2000
CYCLICAL_LAUNCH_SCOUT_FRESH_MC=100000
CYCLICAL_LAUNCH_SCOUT_EARLY_MC=500000
CYCLICAL_LAUNCH_SCOUT_MIN_LIQ_USD=1000
CYCLICAL_LAUNCH_SCOUT_CHAINS=solana,base,ethereum,bsc,arbitrum,polygon,avalanche,optimism,blast,tron,sui,bitcoin,robinhood
CYCLICAL_MEME_WHISPERS_ENABLED=true
CYCLICAL_MEME_WHISPERS_X_ENABLED=true
# CYCLICAL_SOLANA_TRACKER_API_KEY=
```

## API

| Endpoint | Opis |
|----------|------|
| `GET /api/launch/status` | flagship status, Seed counts, traders |
| `GET /api/launch/candidates?tier=seed` | lista (Seed first, MC asc) |
| `GET /api/launch/traders` | Pump top-30 wallets |
| `GET /api/launch/trader-events` | ostatnie ruchy top traderów |
| `GET /api/launch/whispers` | Elon/CZ / Binance radar tape |
| `POST /api/launch/run` | ręczny tick |

SSE: `launch_scout_tick`. Finance Agent tool: `get_launch_scout` (default tier `seed`).

## Terminal links (chain-aware Axiom + fallbacks)

| Chain | Primary (Terminal) | Fallback |
|-------|-------------------|----------|
| Solana | `axiom.trade/meme/{mint}?chain=sol` | DexScreener + Pump.fun when tag `pump` |
| Robinhood | `axiom.trade/meme/{addr}?chain=robinhood` | DexScreener |
| BSC / ETH | Axiom with `chain=bnb` / `chain=eth` | DexScreener |
| Other | DexScreener | — |

LinkGuard runs after each tick (`link_guard` in tick payload). Coordinator: `GET /api/coordinator/health`.

## Interpretacja

- Seed / niski MC ≠ okazja — dużo rugów na Solana meme surface.
- Tip po $1M+ jest za późno dla tego desku.
- Edukacja — nie rekomendacja inwestycyjna.

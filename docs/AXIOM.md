# Axiom desk — Pulse + all positions

Desk **Axiom** aggregates Solana Pulse-style markets and **all bag positions** visible to Kar Digital:

1. **Pulse** — trending/meme markets (Axiom session if cookies set, else DexScreener).
2. **FOMO Family bags** — reconstructed open/closed positions from Cope + Telegram activity.
3. **Tracked wallets** — optional Solana addresses → every SPL token account (public RPC).

## UI

- Desk: `/axiom`
- Also linked from Tools and FOMO Ghost

## Firm wallet · Kar Digital

```env
CYCLICAL_KAR_DIGITAL_WALLET=YourSolanaPubkeyHere
```

Positions appear on `/axiom` with owner **Kar Digital**. Paper book remains on `/portfel` with a firm banner linking to Axiom.

## Env

```env
CYCLICAL_AXIOM_ENABLED=true
CYCLICAL_AXIOM_INTERVAL_SECONDS=90
CYCLICAL_AXIOM_TRENDING_PERIOD=1h
CYCLICAL_AXIOM_INCLUDE_CLOSED=true
# Optional live Axiom Pulse (browser cookies after login on axiom.trade)
CYCLICAL_AXIOM_ACCESS_TOKEN=
CYCLICAL_AXIOM_REFRESH_TOKEN=
# Optional wallets — all open SPL positions
CYCLICAL_AXIOM_WALLETS=
```

Without Axiom cookies the desk stays useful via DexScreener Pulse + FOMO Family bags.

## API

| Endpoint | Opis |
|----------|------|
| `GET /api/axiom/status` | counts / auth / wallets |
| `GET /api/axiom/pulse` | Pulse markets |
| `GET /api/axiom/positions?status=all` | all positions (open+closed) |
| `POST /api/axiom/run` | manual tick |

## Notes

- Educational desk — not custody, not live Axiom trading.
- Family bags are **net buy−sell USD** heuristics from activity, not on-chain exact balances.
- Deep links force Axiom chain context: `?chain=sol&pulseChains=sol` (also `bnb`, `eth`, `robinhood`) so Solana memes open even when your Axiom session had BNB selected.

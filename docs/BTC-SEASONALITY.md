# BTC seasonality vs S&P 500

Generated: `2026-08-05T16:30:24Z`

## Verdict

| Field | Value |
|-------|-------|
| verdict | **partially** |
| regime (rolling 24m) | **mixed** |
| corr monthly full | 0.339 |
| corr rolling 24m latest | 0.43 |
| corr rolling 24m avg | 0.346 |
| month sign agreement | 10/12 |
| Best Six BTC avg | 5.72% |
| Best Six SPX avg | 1.29% |
| Best Six delta (BTC−SPX) | 4.43 pp |
| Worst Six BTC / SPX | 5.32% / 0.89% |
| aligned months | 144 |

Interpretation:
- `similar_to_spx` — calendar seasonality closely tracks equity; lean on ATH phase for crypto edge.
- `partially` — some overlap; cite both phase and month bias.
- `idiosyncratic` — BTC calendar path differs; do not copy US Best Six blindly.

Regime:
- `equity_beta` — recent 24m corr ≥ 0.45 (BTC moves with SPX).
- `mixed` — 0.25–0.45.
- `crypto_idiosyncratic` — corr < 0.25.

## Calendar month averages

| Month | BTC-USD | ^GSPC |
|-------|---------|-------|
| Jan | -1.15% (n=12) | +1.28% (n=16) |
| Feb | +10.19% (n=12) | +0.87% (n=17) |
| Mar | +0.48% (n=12) | +0.48% (n=17) |
| Apr | +10.16% (n=12) | +1.67% (n=17) |
| May | +8.08% (n=12) | +0.54% (n=17) |
| Jun | +0.05% (n=12) | +0.74% (n=17) |
| Jul | +8.88% (n=12) | +2.65% (n=17) |
| Aug | +0.10% (n=13) | -0.08% (n=18) |
| Sep | -1.82% (n=11) | -0.66% (n=16) |
| Oct | +16.63% (n=12) | +2.13% (n=16) |
| Nov | +7.51% (n=12) | +2.90% (n=16) |
| Dec | +7.14% (n=12) | +0.55% (n=16) |

## Presidential term-year averages (monthly means)

| Term year | BTC | SPX |
|-----------|-----|-----|
| Y1 | 9.21 | 1.56 |
| Y2 | -4.76 | 0.58 |
| Y3 | 7.32 | 0.79 |
| Y4 | 10.37 | 1.47 |

## Regeneracja

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/compute_bitcoin_monthly.py
```

Debug JSON: `backend/data/btc_seasonality_debug.json`
Data module: `backend/app/cycles/bitcoin_seasonality_data.py`

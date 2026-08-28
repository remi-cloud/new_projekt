# Session Clock — global meme timetable

Hypothesis: meme pumps are not pure noise — activity often tracks **UTC trading sessions** (Asia → Europe → US) and soft monthly regional seasonality from the global cycle book.

## What it does

1. **Session map (UTC)**
   - Asia: 00–08
   - Europe: 07–16
   - US: 13–22
   - EU∩US overlap: 13–16
2. **Meme heatmap** — buy/sell events + pair creates from Launch Scout bucketed by UTC hour.
3. **Macro log-bias** — hourly `ln(c_t/c_{t-1})` on BTC-USD + SOL-USD (Yahoo 1H).
4. **Month overlay** — soft weights from global cycle book profiles (`asia` / `eu` / `us` / `crypto`).
5. **Soft `session_boost`** (+0…+12) on Launch scores when create time aligns with hot lanes — does **not** change Seed / migrated / dex_paid filters.

## UI

- `/launch` — Session Clock section (now session + 24h bar + macro chips)
- `/cykle` — one-line strip

## API

| Endpoint | Role |
|----------|------|
| `GET /api/cycles/session-clock` | Snapshot |
| `GET /api/launch/session-clock` | Same (meme desk mirror) |

Finance Agent: `get_session_clock`.

## Env

```env
CYCLICAL_SESSION_CLOCK_ENABLED=true
CYCLICAL_SESSION_CLOCK_LOOKBACK_DAYS=14
```

## Notes

Educational timetable — not a prediction that a specific mint pumps at a given UTC hour.

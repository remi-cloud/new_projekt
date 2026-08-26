# FOMO Ghost — top 30 portfeli (Cope Capital)

Agent śledzi **30 największych portfeli** z grafu [fomo.family](https://fomo.family) przez API [Cope Capital](https://api.cope.capital) i pokazuje tokeny wpadające **do plecaka** (buy activity).

## Tryb degraded (Cope offline)

Gdy `api.cope.capital` zwraca Cloudflare **1033/530**, Ghost automatycznie:
1. przełącza się na **lokalny bufor** (top-30 seed + taśma bag-in),
2. pokazuje status `GHOST · DEGRADED`,
3. co tick próbuje wrócić na **LIVE** (auto-register + leaderboard).

Nie wymaga ręcznego klucza, żeby biurko `/fomo` działało.

## Setup klucza (LIVE)

1. Zarejestruj klucz (jednorazowo) — albo zostaw auto-register w ticku:

```bash
curl -X POST https://api.cope.capital/v1/register \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"cyclical-trader-fomo-ghost","description":"FOMO Ghost"}'
```

albo w aplikacji: `POST /api/fomo/register` (przycisk na `/fomo`).

2. Wklej do `.env` / Docker:

```env
CYCLICAL_FOMO_ENABLED=true
CYCLICAL_COPE_API_KEY=cope_xxxxx
CYCLICAL_FOMO_INTERVAL_SECONDS=60
CYCLICAL_FOMO_TOP_N=30
CYCLICAL_FOMO_LEADERBOARD_TIMEFRAME=7d
```

Alias bez prefixu: `COPE_API_KEY=...` (fallback w kliencie).

Klucz z UI trafia też do `backend/data/cope_api_key.txt` (gitignored).

## Jak działa tick (co 60s)

1. `GET /v1/leaderboard?limit=30` — **free** → lokalny snapshot top-30.
2. `GET /v1/activity/poll?since=…` — **free** → jeśli `count==0`, koniec.
3. `GET /v1/activity?since=…` — **liczony** (250/dzień free) → filtr do handle ∈ top-30, persist buy/sell.
4. SSE `fomo_tick` + UI pasek / strona odświeża się co 60s.

## FOMO Family · Bags

Z eventów buy/sell (Cope + Telegram) Ghost buduje **przybliżone plecaki** per handle+mint:

- `GET /api/fomo/family` — otwarte bagi Family
- `GET /api/fomo/bags?include_closed=true` — wszystkie (open/closed)
- UI: sekcja **FOMO Family** na `/fomo` oraz pełna lista na `/axiom`

## Telegram (nasłuch)

Ten sam darmowy bot BotFather co Predator (`CYCLICAL_TELEGRAM_BOT_TOKEN`):

1. Dodaj bota jako admin kanału, do którego forwardujesz alerty FOMO Family.
2. Ustaw chat id:

```env
CYCLICAL_FOMO_TELEGRAM_ENABLED=true
CYCLICAL_FOMO_TELEGRAM_CHAT_IDS=-100xxxxxxxxxx
```

Bez listy chatów parser i tak łapie posty z mintem + buy/sell / `$TICKER` / „fomo.family”.
Poll jest współdzielony z Predator (`getUpdates` — jeden offset).

## UI

- Desk: `/fomo`
- Pasek taśmy: Dashboard + strona FOMO
- Narzędzia → karta FOMO Ghost
- Axiom: `/axiom` (Pulse + wszystkie pozycje Family)

## API

| Endpoint | Opis |
|----------|------|
| `GET /api/fomo/status` | enabled / needs_api_key / last_tick / telegram / family |
| `GET /api/fomo/top` | top 30 |
| `GET /api/fomo/events?side=buy` | feed do plecaka |
| `GET /api/fomo/family` | otwarte bagi FOMO Family |
| `GET /api/fomo/bags` | bagi (opcjonalnie closed) |
| `GET /api/fomo/telegram` | status nasłuchu TG |
| `POST /api/fomo/run?force=true` | ręczny tick |
| `POST /api/fomo/register` | rejestracja Cope |

Finance Agent tool: `get_fomo_ghost`.

## Interpretacja

- **Buy** = token wpadł do bag — może być dokupieniem, nie zawsze nową pozycją.
- **Sell** = wyjście / redukcja (zapisujemy, UI fokusuje buy).
- Bagi Family = heurystyka netto USD, nie gwarantowany bilans on-chain.
- Edukacja — nie rekomendacja inwestycyjna.

## Limity Cope (free)

- Leaderboard + poll: unlimited.
- Activity: **250/dzień**; potem 402 do midnight UTC (albo x402).
- Watchlist Cope (max 10) **nie jest wymagany** — filtrujemy lokalnie do top-30.

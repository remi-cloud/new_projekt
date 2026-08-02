# Cyclical Trader

Skaner rynku 24/7 — sygnały kupna/sprzedaży, superokazje, watchlista i alerty. Nie skalping, nie HFT.

## Co dostajesz

| Funkcja | Opis |
|---|---|
| **Skan automatyczny** | Co 15 minut (konfigurowalne) |
| **Model Alpha / Beta** | Dwa wewnętrzne silniki scoringu (szczegóły niepubliczne) |
| **Dashboard WWW** | Modele, okazje, notowania |
| **Superokazje** | Bid/ask + poziomy wejścia/wyjścia + heatmapa liq |
| **Singularity** | Narzędzie AI (menu Narzędzia) — scoutowie LONG/SHORT → orchestrator |
| **Watchlista** | Dodawaj / wyłączaj / usuwaj instrumenty |
| **Alerty** | ntfy (telefon) + webhook przy zmianie sygnału |
| **Historia** | Log skanów + zmiany sygnałów |

## Źródła danych rynkowych

| Źródło | Użycie |
|---|---|
| Publiczne API krypto | Notowania / referencje |
| Yahoo Finance chart API | Akcje, indeksy, obligacje, surowce, forex |
| Binance Futures (public) | Bid/ask + wolumen (krypto) |
| ntfy.sh | Opcjonalne push-alerty |

Modele scoringu są wewnętrzne — UI pokazuje tylko **Alpha / Beta** i fazy sygnału.

## Monitorowane instrumenty (domyślnie)

- **Krypto**: BTC, ETH, SOL
- **Indeksy USA**: S&P 500, Dow, NASDAQ, Russell (+ SPY/QQQ/IWM)
- **Indeksy świata**: Brazylia (Bovespa), Meksyk, Kanada, Rosja (MOEX/RTS), Japonia, Chiny/HK, Korea, Tajwan, Indie, Singapur, Australia, Europa (FTSE/DAX/CAC/Euro Stoxx/IBEX/…), Bliski Wschód / Afryka + ETF-y krajowe (EWZ, EWJ, FXI, INDA, …)
- **Akcje**: AAPL, MSFT, NVDA, JPM, TSLA, AMZN, META, GOOGL
- **Obligacje** (ETF): TLT, IEF, LQD, HYG
- **Surowce**: Złoto, Srebro, Ropa, Gaz
- **Forex**: EUR/USD, GBP/USD, USD/JPY, USD/BRL, USD/CNY, USD/RUB, DXY

## Uruchomienie (debut / developing)

### Jedna komenda (dev)

```bash
./scripts/dev-up.sh
```

Instaluje zależności, buduje SPA i odpala WWW na **http://localhost:8080**.

### Docker (zalecane na produkcję) — jeden adres WWW

```bash
docker compose up --build
```

- Aplikacja: **http://localhost:8080**
- API: `/api/*`
- Docs: http://localhost:8080/docs

Strony: `/` `/dashboard` `/okazje` `/superokazje` `/modele` `/historia` `/rynki` `/watchlista` `/alerty`

### Cursor Cloud

Konfiguracja debiutu: `.cursor/environment.json` + `./scripts/install.sh`. Terminal `www` uruchamia `./scripts/dev-up.sh`.

### Telefon / publiczny link

```bash
./scripts/start-public.sh
```

`localhost` na telefonie = telefon. Użyj linku `https://….trycloudflare.com`.

### Lokalnie (dev)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/build-www.sh   # z roota repo
uvicorn app.main:app --reload --port 8080
```

**Frontend (hot reload):**
```bash
cd frontend && npm install && npm run dev
```

### Testy

```bash
cd backend && pip install -r requirements.txt && pytest -q
```

## API (wybrane)

| Endpoint | Opis |
|---|---|
| `GET /api/dashboard` | Modele + okazje + notowania |
| `POST /api/scan` | Wymuś skan |
| `GET /api/super-opportunities` | Superokazje |
| `GET /api/history` | Historia skanów / zmian |
| `GET/POST/PATCH/DELETE /api/watchlist` | Watchlista |
| `GET/PUT /api/alerts/settings` | Alerty |
| `GET /api/singularity` | Singularity war room (scouts + specjaliści) |
| `GET /api/health` | Health check |

## Konfiguracja

Prefix `CYCLICAL_` — zobacz `.env.example`.

**Singularity** — narzędzie w `/narzedzia` (API `/api/singularity`), nie baner.

## Architektura

```
backend/          FastAPI + APScheduler + SQLite + httpx
frontend/         React + TypeScript + Vite (serwowane z backend/static)
docker-compose    Jeden serwis WWW :8080
```

## Disclaimer

Cel edukacyjno-analityczny. Nie jest to porada inwestycyjna. Trading wiąże się z ryzykiem utraty kapitału.

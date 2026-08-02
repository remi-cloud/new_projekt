# Cyclical Trader

Skaner rynku 24/7 — sygnały kupna/sprzedaży, superokazje, watchlista i alerty. Nie skalping, nie HFT.

## Co dostajesz

| Funkcja | Opis |
|---|---|
| **Skan automatyczny** | Co 15 minut (konfigurowalne) |
| **Model Alpha / Beta** | Dwa wewnętrzne silniki scoringu (szczegóły niepubliczne) |
| **Dashboard WWW** | Modele, okazje, notowania |
| **Superokazje** | Bid/ask + poziomy wejścia/wyjścia + heatmapa liq |
| **Watchlista** | Dodawaj / wyłączaj / usuwaj instrumenty |
| **Alerty** | ntfy (telefon) + webhook przy zmianie sygnału |
| **Historia** | Log skanów + zmiany sygnałów |
| **Singular** | Opcjonalny Web SDK (atrybucja / eventy) — włącz przez `VITE_SINGULAR_*` |

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
- **Indeksy USA**: S&P 500, Dow Jones, NASDAQ, Russell 2000
- **Akcje**: AAPL, MSFT, NVDA, JPM
- **Obligacje** (ETF): TLT, IEF, LQD, HYG
- **Surowce**: Złoto, Srebro, Ropa, Gaz
- **Forex**: EUR/USD, GBP/USD, USD/JPY, DXY

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
| `GET /api/health` | Health check |

## Konfiguracja

Prefix `CYCLICAL_` — zobacz `.env.example`.

Opcjonalnie Singular Web SDK (build frontend): `VITE_SINGULAR_SDK_KEY`, `VITE_SINGULAR_SDK_SECRET`, `VITE_SINGULAR_PRODUCT_ID`. Bez tych zmiennych moduł jest wyłączony.

## Architektura

```
backend/          FastAPI + APScheduler + SQLite + httpx
frontend/         React + TypeScript + Vite (serwowane z backend/static)
docker-compose    Jeden serwis WWW :8080
```

## Disclaimer

Cel edukacyjno-analityczny. Nie jest to porada inwestycyjna. Trading wiąże się z ryzykiem utraty kapitału.

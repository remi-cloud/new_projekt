# Cyclical Trader

Skaner rynku 24/7, który buduje gotowy produkt sygnałowy dla osób potrzebujących okazji kupna/sprzedaży opartych na **cyklach rynkowych** — nie skalping, nie HFT.

## Co dostajesz

| Funkcja | Opis |
|---|---|
| **Skan automatyczny** | Co 15 minut (konfigurowalne) |
| **Cykl Bitcoin** | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Cykl prezydencki** | Bias lat 1–4 kadencji USA dla akcji, indeksów, obligacji, surowców, forex |
| **Dashboard WWW** | Start, okazje z filtrami, oś czasu cykli, historia zmian sygnałów, rynki |
| **Watchlista** | Dodawaj / wyłączaj / usuwaj instrumenty ze skanera |
| **Alerty** | ntfy (telefon) + webhook przy zmianie sygnału |
| **Historia** | Log skanów + wykrywanie zmian sygnału między przebiegami |

## Źródła danych

| Źródło | Użycie | Link |
|---|---|---|
| **CoinGecko API** | ATH Bitcoina, ceny krypto (BTC/ETH/SOL) | https://www.coingecko.com/en/api |
| **Yahoo Finance chart API** | Notowania akcji, indeksów, obligacji, surowców, forex | `query1.finance.yahoo.com/v8/finance/chart/{symbol}` |
| **ntfy.sh** | Opcjonalne push-alerty na telefon | https://ntfy.sh |

Logika cykli (nie zewnętrzne API):
- Bitcoin: 364 dni bear + 1064 dni bull od ostatniego ATH
- Prezydencki USA: wzorzec lat 1–4 kadencji (Stock Trader's Almanac)

## Filozofia

| Klasa aktywów | Cykl odniesienia | Logika |
|---|---|---|
| **Krypto** | Cykl Bitcoin | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Akcje, indeksy, obligacje, surowce, forex** | Cykl prezydencki USA | Zachowanie w latach 1–4 kadencji prezydenckiej |

### Cykl Bitcoin (krypto)

```
ATH ──► [364 dni BEAR/spadki] ──► [1064 dni BULL/wzrost] ──► [dystrybucja] ──► nowe ATH
```

### Cykl prezydencki (tradycyjne rynki)

| Rok kadencji | Historyczny bias | Sygnał |
|---|---|---|
| Rok 1 (po wyborach) | Słabszy — adaptacja polityki | OBSERWUJ |
| Rok 2 (midterms) | Najsłabszy — lata wyborów do Kongresu | KUPUJ (dołki) |
| Rok 3 (pre-election) | **Najsilniejszy** historycznie | KUPUJ |
| Rok 4 (wybory) | Umiarkowanie pozytywny | TRZYMAJ |

## Monitorowane instrumenty

- **Krypto**: BTC, ETH, SOL
- **Indeksy USA**: S&P 500, Dow Jones, NASDAQ, Russell 2000
- **Akcje**: AAPL, MSFT, NVDA, JPM
- **Obligacje** (ETF): TLT, IEF, LQD, HYG
- **Surowce**: Złoto, Srebro, Ropa, Gaz
- **Forex**: EUR/USD, GBP/USD, USD/JPY, DXY

## Uruchomienie

### Docker (zalecane) — wszystko pod WWW (jeden adres)

```bash
docker compose up --build
```

- Aplikacja WWW: **http://localhost:8080**
- API pod tym samym hostem: `/api/*`
- Docs: http://localhost:8080/docs

Strony: `/` `/dashboard` `/okazje` `/cykle` `/historia` `/rynki` `/watchlista` `/alerty`

### Telefon / publiczny link

`localhost` na telefonie = telefon, nie serwer. Uruchom:

```bash
./scripts/start-public.sh
```

Skrypt buduje UI, startuje apkę na `:8080` i wypisze link `https://….trycloudflare.com` — **ten** otwórz w telefonie.

### Lokalnie (dev)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend dev: http://localhost:5173 (proxy do API na :8000)

### Testy

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

## Strony aplikacji

| Strona | URL | Opis |
|---|---|---|
| Start | `/` | Hero + podsumowanie cykli |
| Dashboard | `/dashboard` | Cykle, top okazje, notowania, skan ręczny |
| Okazje | `/okazje` | Pełna lista z filtrami klasy/sygnału |
| Cykle | `/cykle` | Oś czasu BTC + mapa lat kadencji |
| Historia | `/historia` | Zmiany sygnałów i log skanów |
| Rynki | `/rynki` | Tabela instrumentów |
| Watchlista | `/watchlista` | Zarządzanie monitorowanymi symbolami |
| Alerty | `/alerty` | ntfy + webhook + log dostarczeń |

## API

| Endpoint | Opis |
|---|---|
| `GET /api/dashboard` | Pełny dashboard: cykle, okazje, notowania |
| `POST /api/scan` | Wymuś natychmiastowe skanowanie |
| `GET /api/cycles/bitcoin` | Status cyklu Bitcoin |
| `GET /api/cycles/presidential` | Status cyklu prezydenckiego |
| `GET /api/history` | Log skanów + zmiany sygnałów + ostatnie okazje |
| `GET /api/opportunities/history` | Surowa historia okazji (SQLite) |
| `GET/POST/PATCH/DELETE /api/watchlist` | Watchlista instrumentów |
| `GET/PUT /api/alerts/settings` | Konfiguracja alertów |
| `POST /api/alerts/test` | Test dostarczenia alertu |
| `GET /api/alerts/log` | Log wysłanych alertów |
| `GET /api/health` | Health check + status skanera |

## Deploy

- **Docker:** `docker compose up --build`
- **Render:** zobacz `render.yaml` (API + static frontend)
- Konfiguracja: skopiuj `.env.example` → `.env`

## Konfiguracja

Zmienne środowiskowe (prefix `CYCLICAL_`):

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `SCAN_INTERVAL_MINUTES` | 15 | Interwał skanowania |
| `BTC_BEAR_PHASE_DAYS` | 364 | Dni fazy spadkowej od ATH |
| `BTC_BULL_PHASE_DAYS` | 1064 | Dni fali wzrostowej |
| `DATABASE_PATH` | `data/trader.db` | Ścieżka SQLite |

## Architektura

```
backend/          FastAPI + APScheduler + SQLite + httpx (CoinGecko / Yahoo)
frontend/         React + TypeScript + Vite + React Router
docker-compose    Backend + Frontend (nginx) + healthchecks
```

Źródła danych: CoinGecko (krypto / ATH BTC), Yahoo Finance chart API (instrumenty tradycyjne).

## Disclaimer

Ta aplikacja służy wyłącznie celom edukacyjno-analitycznym. Nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.

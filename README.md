# Cyclical Trader

Aplikacja do tradingu oparta na **cyklach rynkowych** — nie skalping, nie HFT. Monitoruje rynki 24/7 i wyszukuje okazje kupna/sprzedaży na podstawie dwóch fundamentalnych cykli.

## Filozofia

| Klasa aktywów | Cykl odniesienia | Logika |
|---|---|---|
| **Krypto** | Cykl Bitcoin | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Akcje, indeksy, obligacje, surowce, forex** | Cykl prezydencki USA | Zachowanie w latach 1–4 kadencji prezydenckiej |

## Cykl Bitcoin (krypto)

```
ATH ──► [364 dni BEAR/spadki] ──► [1064 dni BULL/wzrost] ──► [dystrybucja] ──► nowe ATH
```

- **Dni 0–364** od ostatniego ATH: faza spadkowa — akumulacja, sygnały KUPUJ/OBSERWUJ
- **Dni 364–1428**: fala wzrostowa — KUPUJ (początek), TRZYMAJ (środek), SPRZEDAJ (koniec)
- **Po 1428 dniach**: dystrybucja — ostrożność do nowego ATH

## Cykl prezydencki (tradycyjne rynki)

| Rok kadencji | Historyczny bias | Sygnał |
|---|---|---|
| Rok 1 (po wyborach) | Słabszy — adaptacja polityki | OBSERWUJ |
| Rok 2 (midterms) | Najsłabszy — lata wyborów do Kongresu | KUPUJ (dystrybucja) |
| Rok 3 (pre-election) | **Najsilniejszy** historycznie | KUPUJ |
| Rok 4 (wybory) | Umiarkowanie pozytywny | TRZYMAJ |

Obligacje i surowce mają dodatkowe modyfikatory w ramach cyklu.

## Monitorowane instrumenty

- **Krypto**: BTC, ETH, SOL
- **Indeksy USA**: S&P 500, Dow Jones, NASDAQ, Russell 2000
- **Akcje**: AAPL, MSFT, NVDA, JPM
- **Obligacje** (ETF): TLT, IEF, LQD, HYG
- **Surowce**: Złoto, Srebro, Ropa, Gaz
- **Forex**: EUR/USD, GBP/USD, USD/JPY, DXY

## Uruchomienie

### Docker (zalecane)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Dokumentacja API: http://localhost:8000/docs

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

Frontend dev server: http://localhost:5173 (proxy do API na :8000)

## API

| Endpoint | Opis |
|---|---|
| `GET /api/dashboard` | Pełny dashboard: cykle, okazje, notowania |
| `POST /api/scan` | Wymuś natychmiastowe skanowanie |
| `GET /api/cycles/bitcoin` | Status cyklu Bitcoin |
| `GET /api/cycles/presidential` | Status cyklu prezydenckiego |
| `GET /api/opportunities/history` | Historia sygnałów (SQLite) |
| `GET /api/health` | Health check + status skanera |

Skaner działa automatycznie co 15 minut (konfigurowalne przez `CYCLICAL_SCAN_INTERVAL_MINUTES`).

## Konfiguracja

Zmienne środowiskowe (prefix `CYCLICAL_`):

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `SCAN_INTERVAL_MINUTES` | 15 | Interwał skanowania |
| `BTC_BEAR_PHASE_DAYS` | 364 | Dni fazy spadkowej od ATH |
| `BTC_BULL_PHASE_DAYS` | 1064 | Dni fali wzrostowej |

## Architektura

```
backend/          FastAPI + APScheduler + SQLite + yfinance
frontend/         React + TypeScript + Vite
docker-compose    Backend + Frontend (nginx)
```

## Disclaimer

Ta aplikacja służy wyłącznie celom edukacyjno-analitycznym. Nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.

# Cyclical Trader

Skaner rynku 24/7, który buduje gotowy produkt sygnałowy dla osób potrzebujących okazji kupna/sprzedaży opartych na **cyklach rynkowych** — nie skalping, nie HFT.

## Co dostajesz

| Funkcja | Opis |
|---|---|
| **Skan automatyczny** | Co 15 minut (konfigurowalne) |
| **Cykl Bitcoin** | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Cykl prezydencki** | Bias lat 1–4 kadencji USA dla akcji, indeksów, obligacji, surowców, forex |
| **Dashboard WWW** | Start, okazje z filtrami, oś czasu cykli, historia zmian sygnałów, rynki |
| **Historia** | Log skanów + wykrywanie zmian sygnału między przebiegami |

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

## API

| Endpoint | Opis |
|---|---|
| `GET /api/dashboard` | Pełny dashboard: cykle, okazje, notowania |
| `POST /api/scan` | Wymuś natychmiastowe skanowanie |
| `GET /api/cycles/bitcoin` | Status cyklu Bitcoin |
| `GET /api/cycles/presidential` | Status cyklu prezydenckiego |
| `GET /api/history` | Log skanów + zmiany sygnałów + ostatnie okazje |
| `GET /api/opportunities/history` | Surowa historia okazji (SQLite) |
| `GET /api/health` | Health check + status skanera |

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

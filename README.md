# Cyclical Trader — wersja WWW

Aplikacja webowa do **tradingu cyklicznego** — monitoruje rynki 24/7 i wyszukuje okazje kupna/sprzedaży na podstawie cykli. Nie skalping, nie HFT.

## Filozofia

| Klasa aktywów | Cykl odniesienia | Logika |
|---|---|---|
| **Krypto** | Cykl Bitcoin | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Akcje, indeksy, obligacje, surowce, forex** | Cykl prezydencki USA + makro regionalne | Lata 1–4 kadencji + bias regionu |

## Szybki start

### Mac (Terminal) — zalecane lokalnie

Od folderów do działającej apki: **[`docs/MAC-SETUP.md`](docs/MAC-SETUP.md)**

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone --branch cursor/paper-trading-21d6 https://github.com/remi-cloud/new_projekt.git
cd new_projekt && ./scripts/mac-bootstrap.sh
./scripts/mac-start.sh         # http://localhost:8080
```

Szczegóły: [`docs/MAC.md`](docs/MAC.md) · Deploy: [`docs/DEPLOY-AWS.md`](docs/DEPLOY-AWS.md)

### Docker (jeden kontener WWW)

```bash
docker compose up --build
```

Otwórz: **http://localhost:8080**

### Lokalnie (dev ręcznie)

```bash
./scripts/build-www.sh
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Frontend hot-reload: `cd frontend && npm install && npm run dev` → http://localhost:5173

## Strony aplikacji WWW

| Strona | URL | Opis |
|--------|-----|------|
| Start | `/` | Strona główna z hero i podsumowaniem cykli |
| Dashboard | `/dashboard` | Cykle + okazje + notowania |
| Cykle | `/cykle` | Szczegóły cykli BTC i prezydenckiego |
| Okazje | `/okazje` | Sygnały z filtrami (klasa, akcja) |
| Rynki | `/rynki` | Tabela instrumentów z filtrami |
| Portfel | `/portfel` | Paper trading |
| Powiadomienia | `/powiadomienia` | Alerty / ntfy / SMS |
| O aplikacji | `/o-aplikacji` | Informacje i disclaimer |

## Cykle rynkowe

### Krypto — cykl Bitcoin (364 / 1064 dni)

```
ATH ──► [364 dni SPADKI] ──► [1064 dni WZROST] ──► [dystrybucja] ──► nowe ATH
```

| Faza | Dni od ATH | Sygnał |
|------|-----------|--------|
| Spadkowa | 0–364 | KUPUJ / OBSERWUJ |
| Wzrostowa | 364–1428 | KUPUJ → TRZYMAJ → SPRZEDAJ |
| Dystrybucja | >1428 | SPRZEDAJ |

### Tradycyjne rynki — cykl prezydencki USA

| Rok kadencji | Bias | Sygnał |
|---|---|---|
| Rok 1 | Słabszy | OBSERWUJ |
| Rok 2 (midterms) | Najsłabszy | KUPUJ |
| Rok 3 (pre-election) | **Najsilniejszy** | KUPUJ |
| Rok 4 (wybory) | Umiarkowany | TRZYMAJ |

## Monitorowane instrumenty (246)

Krypto · Indeksy globalne · **Top 10 akcji / ETF / obligacji** per rynek (USA, Europa, Azja, EM, Polska) · Mag7 · Ekosystem Muska

## API

| Endpoint | Opis |
|---|---|
| `GET /api/dashboard` | Pełne dane dashboardu |
| `POST /api/scan` | Wymuś skanowanie |
| `GET /api/cycles/bitcoin` | Cykl BTC |
| `GET /api/cycles/presidential` | Cykl prezydencki |
| `GET /api/health` | Status serwera + skanera |

Dokumentacja API: http://localhost:8080/docs

## Architektura WWW

```
frontend/     React SPA (React Router, TypeScript, Vite)
backend/      FastAPI — API + serwowanie static SPA
scripts/      mac-bootstrap / build-www / start
Dockerfile    Multi-stage: npm build → Python + static
```

Skaner działa w trybie **real-time**:
- **Ceny** — odświeżanie co 30 s (`CYCLICAL_PRICE_POLL_INTERVAL_SECONDS`)
- **Pełna analiza** — co 5 min (`CYCLICAL_SCAN_INTERVAL_MINUTES`)
- **Powiadomienia** — push (przeglądarka) + SMS (Twilio) przy zmianie sygnału

Konfiguracja: `.env.example` (VAPID, Twilio, progi alertów).

## Disclaimer

Aplikacja edukacyjno-analityczna — nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.

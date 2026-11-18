# Cykliczny Trader · Kar Digital

Aplikacja webowa (**Cyclical Academy**) do **edukacji rynków przez cykle** — tłumaczy fazy rynku i schematy na podstawie cykli. Nie skalping, nie HFT, nie broker.

## Filozofia

| Klasa aktywów | Cykl odniesienia | Logika |
|---|---|---|
| **Krypto** | Cykl Bitcoin | 364 dni spadków od ATH → 1064 dni fali wzrostowej |
| **Akcje, indeksy, obligacje, surowce, forex** | Cykl prezydencki USA + makro regionalne | Lata 1–4 kadencji + bias regionu |

## Szybki start

### Mac (Terminal) — zalecane lokalnie

Od folderów do działającej apki: **[`docs/MAC-SETUP.md`](docs/MAC-SETUP.md)**

```bash
./scripts/mac-bootstrap.sh     # raz
./scripts/mac-start.sh         # http://localhost:8080
```

Szczegóły: [`docs/MAC.md`](docs/MAC.md) · Deploy: [`docs/DEPLOY-AWS.md`](docs/DEPLOY-AWS.md)

### Jedna komenda (dev / Cursor)

```bash
./scripts/dev-up.sh
```

Instaluje zależności, buduje SPA i odpala WWW na **http://localhost:8080**.

### Telefon / publiczny link

```bash
chmod +x scripts/*.sh
./scripts/start-public.sh
```

Opcjonalnie: `brew install cloudflared` (skrypt też pobierze binary do `.tools/`).  
`localhost` na telefonie = telefon — użyj linku `https://….trycloudflare.com` (zapis w `PUBLIC_URL.txt`).

Smoke po starcie: `./scripts/audit.sh`

### Docker

Ten sam `docker compose` działa na **Macu M2 (arm64)** i na serwerze **amd64** (Hetzner). Obrazy bazują na oficjalnych bazach wieloarchitekturowych — Docker sam dobiera wariant procesora. Sekrety (token X, Twilio, klucze API) są tylko w pliku `.env`, nigdy w obrazie. Auto-X jest włączone w kodzie. Żywy wpis czeka, aż `CYCLICAL_SOCIAL_DRY_RUN=false` i `CYCLICAL_PUBLIC_BASE_URL` będzie https na własnej domenie.

Baza i dziennik decyzji oraz cache siedzą na wolumenach (`trader-db`, `app-cache`). Portfel to wspólny folder `backend/data/baza_portfela` — ten sam dla Dockera i lokalnego uvicorn. Serwer działa jako uid 10001. Przy starcie entrypoint tylko na chwilę jest rootem, żeby ten folder był zapisywalny, i oddaje proces użytkownikowi `app`. Gdy folder należy do innego uid i nie da się go otworzyć, w logu jest polecenie `chown -R 10001:10001 backend/data/baza_portfela`.

Posty na X i bot Binance startują w trybie próbnym (`CYCLICAL_SOCIAL_DRY_RUN` i `CYCLICAL_BINANCE_AI_BOT_DRY_RUN` domyślnie true). Tryb próbny blokuje każde prawdziwe API X.

#### Mac M2 (Apple Silicon, arm64)

Potrzebny [Docker Desktop](https://www.docker.com/products/docker-desktop/). Z katalogu projektu:

```bash
cp .env.example .env          # uzupełnij sekrety lokalnie; pliku nie commituj
docker compose up --build -d  # albo: ./scripts/docker-up.sh
```

Strona: **http://localhost:8080**

#### Serwer amd64 (Hetzner)

```bash
git clone <repo> && cd <repo>
cp .env.example .env          # tokeny tylko tutaj
docker compose up --build -d
```

Otwórz port **8080** (albo postaw Caddy/Nginx z HTTPS przed tym portem). Logi: `docker compose logs -f backend frontend`. Stop: `docker compose down`. Skasowanie danych: `docker compose down -v`.

#### Render (amd64)

Blueprint `render.yaml` buduje jeden kontener z głównego `Dockerfile` (strona i API na porcie, który poda Render). Sekrety ustaw w panelu Render. Auto-X zostaje włączone, a `CYCLICAL_SOCIAL_DRY_RUN` zostaw `true`, dopóki domena nie jest Twoim https.

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
| Superokazje | `/superokazje` | Heatmapa 3D + IN/SL/TP + whale + Singularity |
| Narzędzia | `/narzedzia` | Singularity war room + skróty desk |
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
  src/styles/   base.css + theme.css (jeden entry: styles/index.css)
  src/types/    typy domenowe + chart
backend/      FastAPI — API + serwowanie static SPA
  app/api/      routery HTTP (markets, paper, news, ai, …)
  app/main.py   lifespan + rejestracja routerów (~70 linii)
scripts/      mac-bootstrap / build-www / start
Dockerfile    Obraz jednokontenerowy (Render): SPA + API
docker-compose.yml  frontend (nginx) + backend (API), wolumeny danych
backups/      lokalne snapshoty (gitignore — nie commitować)
```

Skaner działa w trybie **real-time**:
- **Ceny** — odświeżanie co 30 s (`CYCLICAL_PRICE_POLL_INTERVAL_SECONDS`)
- **Pełna analiza** — co 5 min (`CYCLICAL_SCAN_INTERVAL_MINUTES`)
- **Powiadomienia** — push (przeglądarka) + SMS (Twilio) przy zmianie sygnału

Konfiguracja: `.env.example` (VAPID, Twilio, progi alertów).

### Backup / auto-save

Pełny snapshot przed wyjściem:

```bash
./scripts/backup-now.sh
```

Zapis trafia do `backups/session_YYYYMMDD_HHMMSS/` (wskaźnik: `backups/LATEST_SESSION.txt`).

Co **20 s** backend kopiuje postęp do `backups/progress/current/` (portfel, trader.db, static).  
W UI: przełącznik **Auto-odświeżanie 20s** (sidebar) — dashboard odświeża dane co 20 s.

## Solana Desk — handel realny

Domyślnie jest papier. Żeby właściciel sam włączył wysyłkę na łańcuch, w `.env` (nigdy w repozytorium) muszą być naraz: `SOLANA_REAL_TRADING=true`, `SOLANA_BOT_PRIVATE_KEY` (base58) i `SOLANA_RPC_URL`. Potem w panelu Solana Desk, po tokenie biurka, przycisk **Uzbrój handel realny**. Bez któregoś z tych zamków kod wysyłki się nie wykonuje. Restart serwera sam rozbraja zamek.

Trasa: Jupiter Swap API v1 (`lite-api.jup.ag`) — kwotowanie, lokalny podpis, `simulateTransaction`, dopiero potem `sendTransaction` i potwierdzenie. Sygnatura i link Solscan trafiają do dziennika. Limity: maks. SOL na transakcję, dzienny limit straty, liczba pozycji, rezerwa SOL na portfelu, sufit poślizgu i opłaty priorytetowej. Wyłącznik awaryjny zatrzymuje nowe kupna i sprzedaje otwarte pozycje. Checker jest ten sam co na papierze.

Ryzyko: to prawdziwe SOL. Symulacja może przejść, a transakcja i tak się nie udać albo potwierdzić za późno. Token bez kwotowania Jupitera nie jest wysyłany.

Stop: **Rozbrój handel realny**, albo `SOLANA_REAL_TRADING=false` i restart. Wyłącznik awaryjny w panelu zamyka nowe wejścia.

## Disclaimer

Aplikacja edukacyjno-analityczna — nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.

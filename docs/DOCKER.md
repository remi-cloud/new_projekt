# Docker — Cyclical Trader · Kar Digital

Dwa kontenery: **frontend** (strona na porcie **8080**) i **backend** (API). Baza, dziennik decyzji i cache są na wolumenach. Portfel jest bind-mountem tego samego folderu co lokalny uvicorn. Auto-publikacja na X jest wyłączona. Posty i bot Binance są w trybie próbnym, dopóki w `.env` nie ustawisz `CYCLICAL_SOCIAL_DRY_RUN=false` albo `CYCLICAL_BINANCE_AI_BOT_DRY_RUN=false`.

## Wymagania

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac) — włączony (ikona wieloryba)
- W Terminalu: `docker compose version`

## Start lokalnie

```bash
cd "/Users/remigiuszgoraus/Desktop/Cykliczny Trader Kar Digital"

# Zalecane — sam odpali Docker Desktop jeśli engine „wisi”:
./scripts/docker-up.sh

# albo ręcznie:
# opcjonalnie: cp .env.example .env
docker compose up --build -d
```

**Jeśli UI Dockera jest otwarte, a `docker compose` mówi „no such file docker.sock”:**
silnik VM nie wstał. Whale menu → **Restart**, potem `./scripts/docker-up.sh`.
Nie trzymaj drugiej kopii `Docker.app` na Desktopie — używaj `/Applications/Docker.app`.

| | |
|---|---|
| Aplikacja | http://127.0.0.1:8080 |
| Health | http://127.0.0.1:8080/api/health |
| Logi | `docker compose logs -f backend frontend` |
| Stop | `docker compose down` |
| Stop + kasuj dane | `docker compose down -v` |

Smoke: `./scripts/audit.sh http://127.0.0.1:8080`

## Volume’y (pamięć)

| Volume / mount | Ścieżka w kontenerze | Co trzyma |
|----------------|----------------------|-----------|
| `trader-db` | `/data/db` | `trader.db` — alerty, newsy i **dziennik decyzji** (`social_decisions`) |
| `./backend/data/baza_portfela` | `/data/portfolio` | paper `portfolio.db`, snapshot, **ledger/** — ten sam folder co lokalny uvicorn |
| `app-cache` | `/app/data` | cache notowań, grafiki newsów |

`docker compose down -v` kasuje wolumeny bazy i cache. Folder portfela na dysku zostaje.

### Prawa portfela (uid 10001)

Proces API to użytkownik `app` (uid 10001), nie root. Entrypoint na starcie jest rootem tylko po to, by na `backend/data/baza_portfela` ustawić zapis dla tego uid i dla właściciela folderu na Macu, potem odpala serwer przez `gosu app`.

Gdy kontener nie może być rootem, a folder należy do innego uid, start kończy się komunikatem. Na hoście:

```bash
chmod -R a+rwX backend/data/baza_portfela
```

Potem `docker compose up -d`. Lokalny uvicorn i Docker czytają ten sam `portfolio.db`.

## Produkcja — domena .ph (zalecane na Mac + Docker)

Stały HTTPS (nie `trycloudflare.com`):

1. Kup domenę + Cloudflare named tunnel — checklista: [`DOMAIN-PH.md`](DOMAIN-PH.md)
2. W `.env`: `CYCLICAL_PUBLIC_BASE_URL=https://kardigital.ph` (lub Twoja nazwa)
3. `./scripts/docker-up.sh`
4. `./scripts/tunnel-named.sh` (wymaga `CLOUDFLARE_TUNNEL_TOKEN`)

Demo / jednorazowy publiczny URL: `./scripts/start-public.sh` (zmienny hostname — nie pod social).

## Produkcja (VPS / Lightsail)

```bash
git clone <repo> && cd <repo>
cp .env.example .env   # uzupełnij sekrety + CYCLICAL_PUBLIC_BASE_URL
docker compose up --build -d
```

Potem reverse proxy (Caddy/Nginx) → `localhost:8080` **albo** Cloudflare tunnel jak w [`DOMAIN-PH.md`](DOMAIN-PH.md).

Szczegóły AWS: [`DEPLOY-AWS.md`](DEPLOY-AWS.md).

## Link z www KAR Digital

Na stronie firmowej dodaj link:

`https://kardigital.ph/` → Cyclical Academy (po zakupie domeny)  
Deep linki: `/agent`, `/superokazje`, `/portfel`, `/news`

# Docker — Cyclical Trader · Kar Digital

Jeden kontener = API + WWW na porcie **8080**. Portfel i trader DB na volume (przeżywają restart).

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
| Logi | `docker compose logs -f www` |
| Stop | `docker compose down` |
| Stop + kasuj dane | `docker compose down -v` |

Smoke: `./scripts/audit.sh http://127.0.0.1:8080`

## Volume’y (pamięć)

| Volume / mount | Ścieżka w kontenerze | Co trzyma |
|----------------|----------------------|-----------|
| `trader-data` | `/app/data` | `trader.db` (AI, alerty, news) |
| bind-mount `./backend/data/baza_portfela` | `/app/data/baza_portfela` | paper `portfolio.db`, snapshot, **ledger/** |

**Portfel = ten folder na Macu.** Lokalny uvicorn i Docker czytają tę samą ścieżkę `backend/data/baza_portfela/` (w tym `ledger/trades.jsonl` — biblia transakcji). Dzięki temu przełączenie lokal↔Docker nie wygląda jak „reset” portfela. Po restarcie agent ledger uzgadnia / odtwarza SQLite z pliku na dysku.

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

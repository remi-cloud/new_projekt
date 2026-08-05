# Domena Filipiny (.ph) + Docker

Stały HTTPS pod marką **KAR Digital · Cyclical Academy**, zamiast losowego `*.trycloudflare.com`.

## 1. Kup domenę (Ty)

Rejestracja `.ph` jest otwarta dla każdego (bez rezydencji PH). Registry: [dotPH](https://www.dot.ph/).

**Kolejność nazw** (sprawdź dostępność w registrarze przed płatnością):

1. `kardigital.ph` — preferowana
2. `cyclicalacademy.ph` — fallback
3. `cyclical.ph` — krótka, jeśli wolna

Gdy `.ph` zajęte: spróbuj `.com.ph` tej samej nazwy.

**Registrar:** [dot.ph](https://www.dot.ph/), Namecheap lub GoDaddy (obsługa `.ph`).

Checklist po zakupie:

- [ ] Okres 1–2 lata + **auto-renew** włączony
- [ ] Potwierdź e-mail rejestranta (bez tego domena może zostać zawieszona)
- [ ] Zapisz login registrara w menedżerze haseł
- [ ] Zanotuj wybraną kanoniczną nazwę (dalej: `TWOJA_DOMENA.ph`)

## 2. Cloudflare DNS + named tunnel

Quick tunnel (`./scripts/start-public.sh`) jest tylko do demo. Produkcja = **named tunnel**.

### A. Konto i zona

1. Załóż darmowe konto [Cloudflare](https://dash.cloudflare.com/).
2. **Add site** → wpisz `TWOJA_DOMENA.ph`.
3. Cloudflare pokaże nameservery (np. `xxx.ns.cloudflare.com`).
4. W panelu registrara ustaw te nameservery i poczekaj na Active (często 5–60 min).

### B. Tunnel (Zero Trust)

1. Cloudflare Dashboard → **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel**.
2. Typ: **Cloudflared**. Nazwa np. `cyclical-trader-mac`.
3. Skopiuj **token** instalacji (jednorazowy string) — **nie commituj** do gita.
4. **Public Hostname**:
   - Subdomain: (puste) → `TWOJA_DOMENA.ph`
   - Type: HTTP
   - URL: `http://127.0.0.1:8080`
5. Opcjonalnie drugi hostname: `www` → ten sam service, plus Page Rule / Bulk Redirect `www` → apex.

### C. SSL

- SSL/TLS mode: **Full** (tunnel kończy TLS po stronie Cloudflare; origin to lokalny HTTP).
- Unikaj Mixed Content (app już serwuje względne `/api`).

### D. Uruchomienie na Macu

```bash
# 1) Docker WWW na :8080
./scripts/docker-up.sh

# 2) Token z Cloudflare (raz):
export CLOUDFLARE_TUNNEL_TOKEN='eyJ...'   # lub dopisz do lokalnego .env

# 3) Named tunnel
./scripts/tunnel-named.sh
```

Token możesz też zapisać w `.env` (gitignored):

```
CLOUDFLARE_TUNNEL_TOKEN=eyJ...
CYCLICAL_PUBLIC_BASE_URL=https://kardigital.ph
```

Smoke po starcie:

```bash
curl -sS "https://TWOJA_DOMENA.ph/api/health"
# oczekiwane: JSON z ok/status
```

## 3. Env + Docker

W `.env` (obok `docker-compose.yml`):

```
CYCLICAL_PUBLIC_BASE_URL=https://kardigital.ph
```

Potem:

```bash
./scripts/docker-up.sh
# albo: docker compose up -d --build
```

Compose już przekazuje `CYCLICAL_PUBLIC_BASE_URL` do kontenera.

W stopkach postów Social desk pojawi się `{PUBLIC_BASE_URL}/news` — patrz [`SOCIAL.md`](SOCIAL.md).

## 4. Social / OAuth

W panelach X i LinkedIn jako website URL ustaw tę samą domenę co `CYCLICAL_PUBLIC_BASE_URL`.  
Social zostaje **dry-run**, aż uzupełnisz tokeny i zrobisz ręczne „Publikuj”.

## Warstwy dostępu

| Cel | URL |
|-----|-----|
| Lokal / Docker | `http://127.0.0.1:8080` |
| Demo (zmienny) | `*.trycloudflare.com` via `start-public.sh` |
| Prod (.ph) | `https://TWOJA_DOMENA.ph` via `tunnel-named.sh` |

## Kryterium sukcesu

- `https://TWOJA_DOMENA.ph/api/health` → 200
- `/news` otwiera się przez domenę
- `CYCLICAL_PUBLIC_BASE_URL` w kontenerze = ta domena (Social desk / posty)

# Kontynuacja pracy — Mac + Terminal → AWS

## Branch

```bash
git clone https://github.com/remi-cloud/new_projekt.git
cd new_projekt
git checkout cursor/paper-trading-21d6
git pull
```

**PR:** https://github.com/remi-cloud/new_projekt/pull/4

## 1) Mac — Terminal (teraz)

**Od zera (foldery → instalacja → dysk):** [`docs/MAC-SETUP.md`](MAC-SETUP.md)

```bash
mkdir -p ~/Projects && cd ~/Projects
# … potem clone / mac-bootstrap — patrz MAC-SETUP.md

cd ~/Projects/new_projekt
chmod +x scripts/*.sh
./scripts/mac-bootstrap.sh   # raz: narzędzia + zależności
./scripts/mac-start.sh       # codziennie
```

→ **http://localhost:8080**

Zatrzymaj: `Ctrl+C` albo `./scripts/mac-stop.sh`

## 2) Online — AWS później

Najprościej: **Lightsail + Docker** (~\$5/mies.)

Patrz: [`docs/DEPLOY-AWS.md`](DEPLOY-AWS.md)

```bash
# na serwerze Ubuntu
docker compose up --build -d
# http://<IP>:8080
```

## Portfel

| Plik | Zawartość |
|------|-----------|
| `backups/portfolio_latest.sqlite` | Backup pozycji |
| `backups/portfolio_snapshot_latest.json` | Podgląd JSON |

`mac-start.sh` przy pierwszym starcie kopiuje backup do  
`backend/data/baza_portfela/portfolio.db` (jeśli brak lokalnej bazy).

## Co działa

- Paper trading (1M PLN, short, zamknij pozycję, otwarto: data)
- Wykresy + markery transakcji
- Persystencja portfela
- Alerty ntfy / opcjonalnie Twilio (numer tylko w `.env` lokalnie)

## Testy

```bash
cd backend && source .venv/bin/activate && pytest -q
```

## Plan na sesję

1. Odpal na Macu (`mac-start.sh`)
2. Sprawdź Portfel / Zamknij / wykresy
3. Jak działa — idziemy w Lightsail (Deploy-AWS)

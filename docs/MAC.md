# Cyclical Trader na Macu (Terminal)

## Wymagania (raz)

```bash
# Homebrew — jeśli jeszcze nie masz:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12 node
```

Python ≥ 3.11, Node.js ≥ 18.

## Start (jeden skrypt)

```bash
git clone https://github.com/remi-cloud/new_projekt.git
cd new_projekt
git checkout cursor/paper-trading-21d6
git pull

chmod +x scripts/mac-start.sh scripts/mac-stop.sh scripts/build-www.sh
./scripts/mac-start.sh
```

Otworzy się przeglądarka na **http://localhost:8080**.

Zatrzymanie: **Ctrl+C** w Terminalu albo:

```bash
./scripts/mac-stop.sh
```

## Przydatne

| Cel | Komenda |
|-----|---------|
| Inny port | `PORT=8090 ./scripts/mac-start.sh` |
| Bez otwierania przeglądarki | `OPEN_BROWSER=0 ./scripts/mac-start.sh` |
| Przebudowa frontendu | `./scripts/build-www.sh` |
| Testy | `cd backend && source .venv/bin/activate && pytest -q` |

## Portfel

Przy pierwszym starcie, jeśli nie ma lokalnej bazy, skrypt kopiuje  
`backups/portfolio_latest.sqlite` → `backend/data/baza_portfela/portfolio.db`.

Dane zostają na dysku Maca między restartami.

## Numer SMS (opcjonalnie)

Nie commituj numeru. Lokalnie:

```bash
cp .env.example backend/.env
# edytuj CYCLICAL_ALERT_PHONE_NUMBER=
```

albo ustaw w aplikacji: **Powiadomienia**.

## Co dalej — online

Patrz: [`docs/DEPLOY-AWS.md`](DEPLOY-AWS.md) (Lightsail / EC2 / Docker).

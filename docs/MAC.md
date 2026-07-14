# Cyclical Trader na Macu (Terminal)

**Pierwszy raz?** Zacznij od folderów: [`MAC-SETUP.md`](MAC-SETUP.md)

## Codzienny start

```bash
cd ~/Projects/new_projekt
git pull
./scripts/mac-start.sh
```

→ **http://localhost:8080**  
Stop: `Ctrl+C` albo `./scripts/mac-stop.sh`

## Przydatne

| Cel | Komenda |
|-----|---------|
| Pełna instalacja od zera | `./scripts/mac-bootstrap.sh` |
| Inny port | `PORT=8090 ./scripts/mac-start.sh` |
| Bez przeglądarki | `OPEN_BROWSER=0 ./scripts/mac-start.sh` |
| Przebudowa frontendu | `./scripts/build-www.sh` |
| Testy | `cd backend && source .venv/bin/activate && pytest -q` |

## Portfel

Przy pierwszym starcie backup z `backups/` trafia do  
`backend/data/baza_portfela/portfolio.db` i zostaje na dysku Maca.

## Online później

[`DEPLOY-AWS.md`](DEPLOY-AWS.md)

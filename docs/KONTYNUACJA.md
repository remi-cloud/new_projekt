# Kontynuacja pracy — 13.07.2026

Zapis stanu projektu, żeby jutro na laptopie nic nie zginęło.

## Git — co pobrać

```bash
git clone https://github.com/remi-cloud/new_projekt.git
cd new_projekt
git checkout cursor/paper-trading-21d6
git pull
```

**Pull Request (cała praca paper trading):**  
https://github.com/remi-cloud/new_projekt/pull/4

**Ostatni commit:** `fffec39` — zamknięcie pozycji, data otwarcia, markery na wykresie

## Uruchomienie na laptopie

```bash
./scripts/build-www.sh          # WAŻNE: kopiuje frontend do backend/static
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Otwórz: **http://localhost:8080**

> Bez `./scripts/build-www.sh` nie zobaczysz przycisku **Zamknij pozycję** — serwer serwuje pliki z `backend/static`, nie z `frontend/dist`.

## Portfel paper trading — nie stracisz pozycji

Stan konta zapisany w repozytorium:

| Plik | Zawartość |
|------|-----------|
| `backups/portfolio_latest.sqlite` | Baza SQLite (pozycje, transakcje, gotówka) |
| `backups/portfolio_snapshot_latest.json` | Podgląd JSON (tylko do odczytu) |

**Przy pierwszym starcie** na pustym laptopie agent portfela automatycznie skopiuje backup do  
`backend/data/baza_portfela/portfolio.db`.

Stan z momentu zapisu (13.07.2026 ~16:43 UTC):

- Gotówka: **990 000 PLN**
- Pozycje: **BTC-USD** (0,040625 szt.) + **PKO.WA** (50 szt.)
- Wartość portfela: **~1 005 580 PLN** (+0,56%)

## Co już działa

- Paper trading: 1 000 000 PLN start, short selling, prowizja 0,1%
- Persystencja portfela w `baza_portfela/`
- **Zamknij pozycję** — Portfel + panel instrumentu
- **Otwarto: data/godzina** przy każdej pozycji
- Markery na wykresie: ▲ kupno, ▼ sprzedaż, ● OTW (otwarcie pozycji)
- Presety wykresu intraday: 1m, 5m, 15m, 30m, 1H, 4H

## Tunel Cloudflare (opcjonalnie)

Quick tunnels **wygasają** po restarcie — błąd 1033 to normalne.

```bash
/tmp/cloudflared tunnel --url http://127.0.0.1:8080
# Skopiuj nowy URL z konsoli (https://....trycloudflare.com)
```

Na laptopie zwykle wystarczy `localhost:8080`.

## Testy

```bash
cd backend && source .venv/bin/activate && pytest -q
# 39 testów powinno przejść
```

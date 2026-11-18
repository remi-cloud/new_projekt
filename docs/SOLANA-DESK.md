# Solana Desk

Papierowe biurko memecoinów Solany. Cztery agenty czytają publiczne rynki i prowadzą symulowany portfel. Nic nie jest podpisywane ani wysyłane na łańcuch.

## Agenty

- **Scout** — nowe minty (Rugcheck `new_tokens`) oraz pary pumpswap / Raydium z DexScreener. Publiczne API pump.fun zwraca 403, więc nie jest źródłem.
- **Checker** — mint i freeze authority, koncentracja holderów, portfel dev, płynność, wiek, wolumen, podatek, honeypot. Brak danych oznacza odrzucenie.
- **Sniper** — po przejściu filtra składa zlecenie i wypełnia je dopiero na **następnej** cenie.
- **Exit** — stop -6%, take-profit, trailing, time-stop, wyłącznik awaryjny. Wypełnienie idzie po kolejnej cenie, nie po poziomie stopu.

## Uruchomienie

Lokalna strona (pętla startuje razem z API):

```bash
./scripts/www-up.sh
```

Potem odśwież `http://127.0.0.1:8080/solana`.

Docker, osobny worker, który wstaje po restarcie:

```bash
docker compose up -d --build backend solana-desk frontend
```

W compose API ma `SOLANA_DESK_AUTOSTART=false`. Tyka usługa `solana-desk`. Baza jest na wolumenie `trader-db`.

Gość widzi saldo, PnL, win rate, dziennik i raport. Start, stop, wyłącznik i ustawienia wymagają tokenu biurka (`CYCLICAL_DESK_TOKEN`), tak jak reszta zapisów.

## Założenia symulacji

- Opłata sieci: 5 000 lamportów za podpis plus priorytet (domyślnie 0,00005 SOL).
- Opłata pump.fun: 1% od strony.
- Poślizg: 50 bps plus wpływ `nominał / (2 × płynność)`, sufit 15%. Cienka księga ślizga się mocniej.
- Opóźnienie: sygnał nie wypełnia się w tym samym obiegu. Cena wejścia to następny odczyt, pogorszony o poślizg.
- Stop -6% tylko **uruchamia** wyjście. Jeśli kolejna cena jest niżej (rug, luka), fill jest po tej cenie, nie po -6%.
- Dzienny limit liczy zmianę kapitału od początku doby UTC, razem z wyceną otwartych pozycji po koszcie wyjścia.
- Start: 1 SOL. Zamiast tego, na pustym rachunku, można podać 20–50 USD i przeliczyć po kursie SOL.

Dziennik (czas UTC, mint, ceny, opłaty, poślizg, PnL, powody) siedzi w SQLite i schodzi jako CSV z panelu.

## Tryb realny — wyłączony

`SOLANA_REAL_TRADING` domyślnie nie jest `true`. Bez `SOLANA_BOT_PRIVATE_KEY` w `.env` właściciela i tak zostaje papier. Klucza nie ma w repozytorium, w logu ani w odpowiedzi API.

Nawet gdy oba warunki są spełnione, ta wersja **nie podpisuje i nie wysyła**. `JupiterSwapGateway` buduje tylko intencję (quote/swap Jupiter, zapasowo pump.fun, podpis lokalny). Prawdziwy podpis da link `https://solscan.io/tx/…`. W papierze pole jest puste.

Czego brakuje do żywego handlu: implementacji podpisu lokalnego, wysłania transakcji Jupiter albo pump.fun, potwierdzenia na RPC i wpisania sygnatury do dziennika. Do tego czasu bramka rzuca `RealTradingLocked`.

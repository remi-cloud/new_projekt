# Solana Desk

Biurko memecoinów Solany. Cztery agenty czytają publiczne rynki. Domyślnie prowadzą papier. Wysyłka na łańcuch jest osobną, wyłączoną ścieżką.

## Agenty

- **Scout** — nowe minty (Rugcheck `new_tokens`) oraz pary pumpswap / Raydium z DexScreener. Publiczne API pump.fun zwraca 403, więc nie jest źródłem.
- **Checker** — mint i freeze authority, koncentracja holderów, portfel dev, płynność, wiek, wolumen, podatek, honeypot. Najpierw tani filtr DexScreener (płynność, wolumen, wiek, cena), potem raport Rugcheck dla czołówki (domyślnie 15, cache 10 min). Brak raportu to „czeka na dane”, nie odrzucenie.
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

## Handel realny — domyślnie wyłączony

Wysyłka idzie przez **Jupiter Swap API v1** (`https://lite-api.jup.ag/swap/v1`): kwotowanie, podpis lokalny (`solders`), `simulateTransaction` na `SOLANA_RPC_URL`, potem `sendTransaction` i potwierdzenie. Sygnatura i link Solscan lądują w dzienniku i w CSV.

Żeby cokolwiek wyszło na łańcuch, naraz muszą być: `SOLANA_REAL_TRADING=true`, niepusty `SOLANA_BOT_PRIVATE_KEY` (base58), `SOLANA_RPC_URL` i zamek **Uzbrój handel realny** w panelu (token biurka). Zamek jest w bazie i każdy start procesu ustawia go na rozbrojony. Bez kompletu bramek funkcja wysyłki wraca zanim dotknie Jupitera i RPC.

Limity wspólne z papierem, plus rezerwa SOL na portfelu, sufit poślizgu (domyślnie 100 bps, twardo 300) i sufit opłaty priorytetowej (0,01 SOL). Wyłącznik awaryjny blokuje nowe kupna. Otwarta pozycja realna schodzi sprzedażą Jupitera; pozycja papierowa bez ilości w jednostkach mint nie jest sprzedawana „na ślepo”.

Klucz nie wchodzi do logu, odpowiedzi API ani repozytorium. W `.env.example` są tylko puste pola. Ryzyko i sposób stopu: README, sekcja „Solana Desk — handel realny”.

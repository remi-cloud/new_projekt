# Solana Desk · Grok Bot Terminal

Jedna ścieżka egzekucji dla papieru i handlu na łańcuchu. Papier różni się tylko ostatnim krokiem: zamiast `sendTransaction` fill bierze się z kwotowania (albo z symulacji, gdy jest publiczny klucz). Reszta jest prawdziwa: Jupiter, zapasowy Raydium, wpływ na cenę, opłata priorytetowa, budowa transakcji i `simulateTransaction`, gdy znamy pubkey.

Panel jest na `/solana`. Liczby pochodzą z silnika, bazy albo strumienia. Brak danych widać jako `— no data …` albo `no close yet`. Stopka to `paper · real quotes` albo `LIVE · on-chain`.

## Agenty

| Agent | Robi | Nie robi |
|---|---|---|
| Scanner | Nowe pary DexScreener, spike `vol_5m / avg_5m(1h)`, udział kupna, LP | nie handluje |
| Rug Check | Rugcheck plus mint na RPC (mint/freeze, Token-2022), holderzy, LP, test sprzedaży token→SOL | nie dobiera wielkości |
| Sizer | `equity × clamp(ryzyko / stop)` , domyślnie 1,5% / 6% = 25%, widełki 5–40%. Ścina rozmiar, aż wpływ kwotowania mieści się w limicie poślizgu. Twardy sufit `max_per_trade_sol` | nie używa stałego `position_sol` (zostaje tylko do migracji, przestarzałe) |
| Executor | Bramki, kwotowanie, budowa, symulacja, a na żywo podpis i wysyłka z ponowieniem do 3 razy | nie otwiera bez świeżego PASS i SIZE (< 120 s) |
| Logger | Jedyny zapis decyzji, numer linii, powód obowiązkowy | nie ucina historii do 200 wierszy (retencja 90 dni) |
| Equity | Wycena otwartych pozycji kwotowaniem sprzedaży. Zrzut przy każdym zamknięciu i co 60 s. Wygrane i przegrane liczone osobno | nie handluje |
| You | Nieprzeczytane linie w przeglądarce | — |

Na przyszłość, bez kart na panelu: Whale, Shill, Head of Desk.

Kolejność na kandydata jest stała: skan → sprawdzenie → wielkość → egzekucja → log. Lekcje mogą tylko zaostrzyć regułę i wchodzą do powodu decyzji.

## Rytm

- Odkrywanie: `SOLANA_DESK_INTERVAL_SECONDS`, domyślnie 10 s (minimum 10).
- Ceny i wyjścia: co 2 s, DexScreener, zapasowo Jupiter Price. Otwarte pozycje i cztery ostatnie chipy.
- Strumień: `GET /api/solana/stream` (SSE). API czyta SQLite co 1 s, więc worker może stać w innym procesie. Zdarzenia: `snapshot`, `decision`, `tick`, `heartbeat`, `lesson`. Nagłówek `Last-Event-ID` wznawia decyzje. Nginx ma `proxy_buffering off` dla `/api/`. Odpowiedź niesie `X-Accel-Buffering: no`. Cloudflare Tunnel przepuszcza `text/event-stream` bez bufora; tu nie było osobnego tunelu do sprawdzenia na żywo.
- Gdy strumień padnie, panel pisze `stream offline · retrying` i odpytuje `/terminal` co 3 s.

## Ryzyko

- Poślizg: `max_slippage_pct`, domyślnie 2,0%, twardo nie więcej niż 3%. Sprawdzany na kwotowaniu i po fillu.
- Rezerwa SOL, dzienny limit straty, maks. otwartych, maks. na transakcję i wyłącznik awaryjny zostają.
- Opłata priorytetowa nie przekracza 0,01 SOL.
- Pusty powód decyzji podnosi `ValueError`.
- Gdy Jupiter i Raydium milczą, nie ma nowego wejścia (`no quote: jupiter+raydium down`). Wyjście może zejść modelem (`fill_source=model`, znacznik MODEL). To nie jest kwotowanie.

## Nauka

Każdy agent (i agent finansowy strony) dostaje lekcję jako regułę z białej listy, nie jako luźny tekst. Model proponuje JSON przez `app.ai.llm.simple_complete` (temperatura 0,2). Gdy nie ma klucza albo JSON jest zły, regułę składa deterministyczny miner. Strażnik odrzuca poluzowanie: wyższy poślizg, większy rozmiar, `factor > 1`, luźniejszy próg rug, wyłączony check, flaga realna, klucz, RPC, kill switch. Nowa lekcja z niską pewnością albo sam LLM bez zgodnego minera startuje jako `shadow` (5 trafień). Powtórzony ten sam błąd (`rule_key` już widziany) wchodzi od razu jako `active`. Po ≥10 trafieniach lekcja, której zablokowane tokeny wyszłyby lepiej niż biurko, schodzi do `retired` i zostaje w bazie. Panel pokazuje `lessons N · last: …`.

## Jak włączyć handel na łańcuchu

Robi ustawia to sam, w środowisku, nigdy w repozytorium:

```env
SOLANA_REAL_TRADING=true
SOLANA_BOT_PRIVATE_KEY=
SOLANA_RPC_URL=
```

Potem restart procesu. Klucz czyta tylko podpis. Nie wchodzi do logu, API ani bazy. `SOLANA_REQUIRE_PANEL_ARM` domyślnie `false`. Gdy jest `true`, dochodzi zamek w panelu i restart go zdejmuje, jak dotychczas.

`SOLANA_PAPER_WALLET_PUBKEY` to sam adres (bez klucza). Wtedy papier buduje i symuluje transakcję. `JUPITER_API_KEY` przełącza kwotowanie na `https://api.jup.ag/swap/v1` z nagłówkiem `x-api-key`. `JUPITER_BASE` może nadpisać adres.

## Jak wycofać

`SOLANA_REAL_TRADING=false` i restart. Nowe wejścia zostają papierem na prawdziwych kwotowaniach. Wyłącznik awaryjny w panelu zamyka nowe kupna od razu.

## Zdrowie i self-test

`GET /api/solana/health` — status agenta: ok, degraded, down, idle.

`POST /api/solana/selftest` (token biurka, raz na 60 s) nie wysyła transakcji. Czyta DexScreener, sprawdza BONK, liczy wielkość, kwotuje SOL→USDC i buduje swap, a symuluje tylko gdy jest pubkey. Logger wstawia wiersz i robi rollback. Wynik: `GET /api/solana/selftest/last`.

## Baza

Nowe tabele: `solana_desk_decisions`, `solana_desk_equity`, `solana_desk_ticks`, `solana_desk_agent_health`, `solana_desk_selftest`, `solana_desk_lessons`, `solana_desk_lesson_hits`. Stare zdarzenia są przenoszone do decyzji raz. Wolumen `trader-db` trzyma to przez restart kontenera.

# Telegram Predator — darmowy relay (BotFather)

PredatorAiBot / kanały VIP **nie dają** darmowego API do odczytu cudzego bota.
Działa za darmo tak:

1. Telegram → [@BotFather](https://t.me/BotFather) → `/newbot` → skopiuj **token** (darmowy).
2. Utwórz kanał prywatny np. `KAR Predator Relay`.
3. Dodaj swojego bota jako **administratora** kanału (prawo do postów).
4. Z Predatora (app / kanał / VIP) **przekazuj (Forward)** sygnały do tego kanału  
   albo wklejaj tekst ręcznie.
5. W `.env`:

```bash
CYCLICAL_TELEGRAM_PREDATOR_ENABLED=true
CYCLICAL_TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
# opcjonalnie — tylko ten chat (id kanału, często zaczyna się od -100...)
CYCLICAL_TELEGRAM_PREDATOR_CHAT_ID=
CYCLICAL_TELEGRAM_PREDATOR_NOTIFY=true
CYCLICAL_TELEGRAM_PREDATOR_INTERVAL_SECONDS=60
```

6. Restart WWW / Docker.
7. Sprawdź: `GET /api/predator/status` · `POST /api/predator/poll` · UI **Alerty**.

## Co robi aplikacja

- Czyta nowe posty kanału (Bot API `getUpdates`) — **0 zł**.
- Parsuje `LONG/SHORT/BUY/SELL` + ticker → `BTC-USD` itd.
- Zapisuje sygnały + wysyła alert (ntfy/push) jak inne sygnały biurka.
- **Nie** handluje automatycznie — tylko informacja edukacyjna.

## Chat ID

Napisz coś na kanale, odpal `POST /api/predator/poll`, potem w `GET /api/predator/signals` zobaczysz `chat_id`. Wklej go do `CYCLICAL_TELEGRAM_PREDATOR_CHAT_ID`.

## Uwaga

Nie udostępniaj tokenu BotFather w gicie. Forward z płatnego Predatora nadal jest legalnym „korzystaniem z informacji” po Twojej stronie — to Ty decydujesz, co wklejasz.

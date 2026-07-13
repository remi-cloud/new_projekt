# Konfiguracja SMS (Twilio) — Włochy +39

Nie da się założyć konta Twilio automatycznie — wymaga Twojego e-maila i weryfikacji numeru (~5 min).

## Krok 1: Załóż konto (darmowy trial)

1. Wejdź na **https://www.twilio.com/try-twilio**
2. Podaj e-mail, hasło, numer **** (weryfikacja kodem SMS)
3. Wybierz produkt: **SMS** → use case: **Notifications**

## Krok 2: Numer nadawcy

1. W konsoli Twilio: **Phone Numbers → Buy a number**
2. Wybierz numer z Włoch (+39) lub trialowy numer
3. Skopiuj numer w formacie E.164 (np. `+393xxxxxxxx`)

## Krok 3: Zweryfikuj odbiorcę (trial)

Na koncie trial musisz **zweryfikować ** jako Verified Caller ID:
**Console → Phone Numbers → Verified Caller IDs → Add**

## Krok 4: Wklej dane w aplikacji

1. **Console → Account → API keys & tokens**
2. Skopiuj **Account SID** i **Auth Token**
3. W aplikacji: **Powiadomienia → SMS Twilio → wklej i Zapisz**

Dane są zapisywane lokalnie na serwerze (`backend/data/credentials.local.json`, gitignored).

## Od razu bez Twilio: ntfy

Na stronie **Powiadomienia** jest unikalny link `https://ntfy.sh/cyclical-...`:
1. Zainstaluj aplikację **ntfy** na telefonie
2. Subskrybuj ten temat
3. Kliknij **Wyślij test powiadomienia**

Powiadomienia trafią na telefon bez konta SMS.

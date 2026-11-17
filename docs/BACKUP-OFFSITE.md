# Kopia baz poza serwer

Skrypt `scripts/backup-offsite.sh` kopiuje tylko `trader.db`, `portfolio.db` i katalog `ledger`. Nie czyta `.env` i nie wkłada sekretów do archiwum.

## Jednorazowo

```bash
CYCLICAL_BACKUP_DEST=user@backup.example:/var/backups/kar-digital ./scripts/backup-offsite.sh
```

Cel lokalny (dysk, który nie jest dyskiem aplikacji):

```bash
CYCLICAL_BACKUP_DEST=/mnt/offsite/kar-digital ./scripts/backup-offsite.sh
```

Na hoście docelowym zostaje katalog o nazwie UTC, na przykład `20261117T180000Z`.

## Cron (serwer)

Cel musi być inną maszyną albo innym dyskiem niż ten, na którym chodzi aplikacja.

```cron
15 3 * * * CYCLICAL_BACKUP_DEST=user@backup.example:/var/backups/kar-digital /opt/kar-digital/scripts/backup-offsite.sh
```

Klucz SSH użytkownika crona musi mieć dostęp do celu. Nie zapisuj hasła w repozytorium ani w crontabie.

## launchd (Mac)

Plik `~/Library/LaunchAgents/com.kardigital.backup.plist`. `ProgramArguments` woła skrypt, a cel jest w `EnvironmentVariables`. Dysk docelowy nie może być dyskiem projektu.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.kardigital.backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/YOU/kar-digital/scripts/backup-offsite.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CYCLICAL_BACKUP_DEST</key>
    <string>/Volumes/Offsite/kar-digital</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>15</integer>
  </dict>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.kardigital.backup.plist
```

## Przywracanie

Zatrzymaj aplikację, skopiuj pliki z powrotem na ścieżki `CYCLICAL_DATABASE_PATH` i `CYCLICAL_PORTFOLIO_DATABASE_PATH`, ustaw właściciela `10001:10001` w Dockerze, uruchom ponownie.

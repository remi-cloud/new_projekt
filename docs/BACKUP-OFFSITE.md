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

## Cron

```cron
15 3 * * * CYCLICAL_BACKUP_DEST=user@backup.example:/var/backups/kar-digital /opt/kar-digital/scripts/backup-offsite.sh
```

Klucz SSH użytkownika crona musi mieć dostęp do celu. Nie zapisuj hasła w repozytorium.

## Przywracanie

Zatrzymaj aplikację, skopiuj pliki z powrotem na ścieżki `CYCLICAL_DATABASE_PATH` i `CYCLICAL_PORTFOLIO_DATABASE_PATH`, ustaw właściciela `10001:10001` w Dockerze, uruchom ponownie.

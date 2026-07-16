# Backups (lokalne — nie commitowane)

Snapshoty i auto-zapis żyją tylko na dysku. Katalogi `session_*`, `sessions_auto/`, `progress/` są w `.gitignore`.

## Pełny snapshot (zrób przed wyjściem z domu)

```bash
./scripts/backup-now.sh
```

- Folder: `backups/session_YYYYMMDD_HHMMSS/` (~cały projekt bez node_modules/.venv)
- Wskaźnik: `backups/LATEST_SESSION.txt`

## Auto-zapis postępu (co 20 s, gdy backend działa)

- `backups/progress/current/` — portfel, trader.db, static, env.example
- `backups/progress/latest.json` — timestamp ostatniego zapisu
- Rotacja: `backups/sessions_auto/progress_*` (trzymaj max 2–3 lokalnie)

Env: `CYCLICAL_AUTO_BACKUP_ENABLED=true`, `CYCLICAL_AUTO_BACKUP_INTERVAL_SECONDS=20`

API: `GET /api/backup/status`, `POST /api/backup/now`

#!/bin/sh
# Open data directories, then run the server as uid 10001 (app).
# Root is used only for this setup step. The application process is not root.
set -eu

mkdir -p /data/db /data/portfolio /app/data/news_images /backups

# Portfolio stays private to uid 10001. No world-writable bits.
share_portfolio() {
  dir=/data/portfolio
  chown -R app:app "$dir" || return 1
  chmod 750 "$dir" || return 1
  find "$dir" -type d -exec chmod 750 {} +
  find "$dir" -type f -exec chmod 640 {} +
}

if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data/db /app/data /backups
  if ! share_portfolio; then
    echo "Nie udało się otworzyć zapisu portfela w /data/portfolio." >&2
    exit 1
  fi
  umask 027
  exec gosu app "$0" "$@"
fi

for dir in /data/db /data/portfolio /app/data; do
  if [ ! -w "$dir" ]; then
    owner="$(stat -c '%u:%g' "$dir" 2>/dev/null || echo '?')"
    echo "Katalog $dir należy do uid $owner i nie jest zapisywalny dla uid $(id -u) (app)." >&2
    echo "Aplikacja nie działa jako root. Na hoście ustaw prawa wspólnego portfela:" >&2
    echo "  sudo chown -R 10001:10001 backend/data/baza_portfela" >&2
    echo "Szczegóły: docs/DOCKER.md" >&2
    exit 1
  fi
done

umask 027
exec "$@"

#!/bin/sh
# Open data directories, then run the server as uid 10001 (app).
# Root is used only for this setup step. The application process is not root.
set -eu

mkdir -p /data/db /data/portfolio /app/data/news_images /backups

# Shared with local uvicorn: keep the host owner's uid, but let uid 10001 write.
share_portfolio() {
  dir=/data/portfolio
  chmod a+rwx "$dir" || return 1
  find "$dir" -type d -exec chmod a+rwx {} +
  find "$dir" -type f -exec chmod a+rw {} +
}

if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data/db /app/data /backups
  if ! share_portfolio; then
    echo "Nie udało się otworzyć zapisu portfela w /data/portfolio." >&2
    exit 1
  fi
  # New sqlite files stay writable for the Mac user who shares this folder.
  umask 000
  exec gosu app "$0" "$@"
fi

for dir in /data/db /data/portfolio /app/data; do
  if [ ! -w "$dir" ]; then
    owner="$(stat -c '%u:%g' "$dir" 2>/dev/null || echo '?')"
    echo "Katalog $dir należy do uid $owner i nie jest zapisywalny dla uid $(id -u) (app)." >&2
    echo "Aplikacja nie działa jako root. Na hoście ustaw prawa wspólnego portfela:" >&2
    echo "  chmod -R a+rwX backend/data/baza_portfela" >&2
    echo "Szczegóły: docs/DOCKER.md" >&2
    exit 1
  fi
done

umask 000
exec "$@"

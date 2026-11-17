#!/bin/sh
# Prepare data dirs, then run the server as the non-root app user.
set -eu

mkdir -p /data/db /data/portfolio /app/data/news_images /backups

if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data /app/data /backups
  exec gosu app /app/docker-entrypoint.sh "$@"
fi

for dir in /data/db /data/portfolio /app/data; do
  if [ ! -w "$dir" ]; then
    echo "Katalog danych nie jest zapisywalny: $dir (uid $(id -u))" >&2
    exit 1
  fi
done

exec "$@"

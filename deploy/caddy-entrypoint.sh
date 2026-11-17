#!/bin/sh
# Render Caddy for the public profile. Basic auth is on only when both env vars are set.
set -eu
DOMAIN="${SITE_DOMAIN:?set SITE_DOMAIN}"
USER_NAME="${CYCLICAL_CADDY_BASIC_USER:-}"
HASH="${CYCLICAL_CADDY_BASIC_HASH:-}"
{
  printf '%s {\n' "$DOMAIN"
  printf '\tencode gzip\n'
  if [ -n "$USER_NAME" ] && [ -n "$HASH" ]; then
    printf '\tbasic_auth {\n'
    printf '\t\t%s %s\n' "$USER_NAME" "$HASH"
    printf '\t}\n'
  fi
  printf '\treverse_proxy frontend:8080\n'
  printf '}\n'
} > /tmp/Caddyfile
exec caddy run --config /tmp/Caddyfile --adapter caddyfile

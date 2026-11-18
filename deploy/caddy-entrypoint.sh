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
  printf '\theader {\n'
  printf '\t\tStrict-Transport-Security "max-age=15552000; includeSubDomains"\n'
  printf '\t}\n'
  # Replace, do not append: the visitor must not choose the scheme or the first hop.
  printf '\treverse_proxy frontend:8080 {\n'
  printf '\t\theader_up X-Forwarded-For {remote_host}\n'
  printf '\t\theader_up X-Forwarded-Proto {scheme}\n'
  printf '\t}\n'
  printf '}\n'
} > /tmp/Caddyfile
exec caddy run --config /tmp/Caddyfile --adapter caddyfile

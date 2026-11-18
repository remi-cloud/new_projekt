#!/bin/sh
set -eu
PORT="${PORT:-8000}"
# Uvicorn must not rewrite the client from X-Forwarded-*. A wildcard trust
# list keeps the leftmost address, so any caller could pick the IP used for
# login limits. The app reads those headers only for CYCLICAL_TRUSTED_PROXIES.
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-proxy-headers

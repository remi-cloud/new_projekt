#!/usr/bin/env bash
# Wybierz najlepszy Python 3.11+ na Macu (source this file)
resolve_mac_python() {
  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
  elif [ -x /opt/homebrew/opt/python@3.12/bin/python3.12 ]; then
    PYTHON_BIN="/opt/homebrew/opt/python@3.12/bin/python3.12"
  elif [ -x /usr/local/opt/python@3.12/bin/python3.12 ]; then
    PYTHON_BIN="/usr/local/opt/python@3.12/bin/python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    return 1
  fi
  export PYTHON_BIN
}

ensure_brew_path() {
  if command -v brew >/dev/null 2>&1; then
    return 0
  fi
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

check_python_version() {
  local ver major minor
  ver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  major="${ver%%.*}"
  minor="${ver#*.}"
  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
    return 1
  fi
  return 0
}

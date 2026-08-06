#!/usr/bin/env bash
# Public smoke audit — backend API + frontend static + core pages + AI/news.
set -euo pipefail
BASE="${1:-http://127.0.0.1:8080}"
PORT="${PORT:-8080}"
fail=0

check() {
  local path="$1" expect="$2"
  local code body attempt
  body=$(mktemp)
  code=000
  for attempt in 1 2 3 4 5; do
    code=$(curl -sS -o "$body" -w '%{http_code}' --max-time 60 "$BASE$path" || echo 000)
    if [[ "$code" == "$expect" ]]; then
      break
    fi
    # Cold start: dashboard/scan may return 503 briefly
    if [[ "$code" == "503" || "$code" == "000" ]]; then
      sleep 2
      continue
    fi
    break
  done
  if [[ "$code" != "$expect" ]]; then
    echo "FAIL $path -> HTTP $code (want $expect)"
    fail=1
  else
    echo "OK   $path -> $code"
  fi
  rm -f "$body"
}

check_json_field() {
  local path="$1" py="$2" label="$3"
  local raw val
  raw=$(curl -sf --max-time 30 "$BASE$path" || true)
  if [[ -z "$raw" ]]; then
    echo "FAIL $label ($path) — empty/unreachable"
    fail=1
    return
  fi
  val=$(printf '%s' "$raw" | python3 -c "$py" 2>/dev/null || true)
  if [[ -z "$val" || "$val" == "False" || "$val" == "false" || "$val" == "none" ]]; then
    echo "FAIL $label -> $val"
    fail=1
  else
    echo "OK   $label -> $val"
  fi
}

echo "=== Audit $BASE ==="

if command -v lsof >/dev/null 2>&1; then
  if [[ "$BASE" == http://127.0.0.1:* || "$BASE" == http://localhost:* ]]; then
    if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "OK   port :$PORT LISTEN"
    else
      echo "FAIL port :$PORT not LISTEN"
      fail=1
    fi
  fi
fi

check /api/health 200
check / 200
check /rynki 200
check /dashboard 200
check /portfel 200
check /superokazje 200
check /agent 200
check /news 200
check /api/dashboard 200
check /api/cycles/bitcoin 200
check_json_field /api/cycles/bitcoin \
  'import sys,json;d=json.load(sys.stdin);ok=len(d.get("month_returns") or [])==12 and d.get("spx_comparison");print("ok" if ok else "")' \
  "bitcoin.month_returns+spx_comparison"
check_json_field /api/cycles/presidential \
  'import sys,json;d=json.load(sys.stdin);ok=len(d.get("month_matrices") or [])==4 and d.get("next_term_outlook");print("ok" if ok else "")' \
  "presidential.month_matrices+next_term"
check /api/cycles/seasonality-health 200
check_json_field "/api/cycles/intramonth?month=8&universe=us" \
  'import sys,json;d=json.load(sys.stdin);ok=len(d.get("days") or [])==31 and len(d.get("weeks") or [])==4;print("ok" if ok else "")' \
  "intramonth.us"
check_json_field "/api/cycles/intramonth?month=8&universe=btc" \
  'import sys,json;d=json.load(sys.stdin);ok=len(d.get("days") or [])==31;print("ok" if ok else "")' \
  "intramonth.btc"
check_json_field "/api/cycles/global-book?status=all" \
  'import sys,json;d=json.load(sys.stdin);ok=isinstance(d.get("order_book"), list) and isinstance(d.get("profiles"), dict);print("ok" if ok else "")' \
  "cycles.global-book"
check_json_field "/api/cycles/month-pumps?month=11&limit=5" \
  'import sys,json;d=json.load(sys.stdin);ok=d.get("month")==11 and isinstance(d.get("pumped"), list);print("ok" if ok else "")' \
  "cycles.month-pumps"
check_json_field "/api/cycles/month-pumps/snippet?month=11" \
  'import sys,json;d=json.load(sys.stdin);ok=bool(d.get("text"));print("ok" if ok else "")' \
  "cycles.month-pumps.snippet"
check "/api/cycles/calendar-search?q=AAPL" 200
check /api/telemetry/agent-vs-sp500 200
check_json_field /api/roi/program-us-1995 \
  'import sys,json;d=json.load(sys.stdin);p=d.get("program") or {};ok=d.get("final_value") is not None and p.get("agent_final") is not None;print("ok" if ok else "")' \
  "roi.program-us-1995"
check /api/public/live 200
check /api/paper/portfolio 200
check /api/super-opportunities 200
check /api/whale-flows 200
check /api/singularity/status 200
check /api/ai/status 200
check /api/news/macro 200
check "/api/news/calendar?year=$(date +%Y)&month=$(date +%-m 2>/dev/null || date +%m)" 200

HEALTH_RAW=$(curl -sf --max-time 30 "$BASE/api/health" || true)
STATUS=$(printf '%s' "$HEALTH_RAW" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("status",""))' 2>/dev/null || true)
if [[ "$STATUS" != "ok" ]]; then
  echo "FAIL /api/health status=$STATUS"
  fail=1
else
  echo "OK   /api/health status=ok"
fi

WWW=$(printf '%s' "$HEALTH_RAW" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("www",False))' 2>/dev/null || true)
if [[ "$WWW" != "True" && "$WWW" != "true" ]]; then
  echo "FAIL www static missing (health.www=$WWW) — run ./scripts/build-www.sh"
  fail=1
else
  echo "OK   www static present"
fi

check_json_field /api/ai/status \
  'import sys,json;d=json.load(sys.stdin);print(d.get("provider") or "none")' \
  "ai.provider"

check_json_field /api/ai/status \
  'import sys,json;d=json.load(sys.stdin);print("self_learn" if "self_learn" in (d.get("features") or []) else "")' \
  "ai.feature self_learn"

FEATURES=$(curl -sf --max-time 30 "$BASE/api/ai/status" | python3 -c 'import sys,json;print(",".join(json.load(sys.stdin).get("features") or []))' 2>/dev/null || true)
if [[ "$FEATURES" == *free_llm7* || "$FEATURES" == *self_learn* ]]; then
  echo "OK   ai.features present"
else
  echo "FAIL ai.features thin: $FEATURES"
  fail=1
fi

check_json_field /api/paper/portfolio \
  'import sys,json;d=json.load(sys.stdin);print("ok" if "cash_pln" in d and ("total_equity_pln" in d or "equity" in d or "total_equity" in d) else "")' \
  "paper.cash_pln+equity"

check /api/paper/ledger/status 200
check_json_field /api/paper/ledger/status \
  'import sys,json;d=json.load(sys.stdin);ok=d.get("ledger_dir") and d.get("ledger_trades") is not None and d.get("db_trades") is not None;print("ok" if ok else "")' \
  "paper.ledger.status"

PAPER_RAW=$(curl -sf --max-time 30 "$BASE/api/paper/portfolio" || true)
if [[ -n "$PAPER_RAW" ]]; then
  CASH=$(printf '%s' "$PAPER_RAW" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("cash_pln",""))' 2>/dev/null || true)
  EQUITY=$(printf '%s' "$PAPER_RAW" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("total_equity_pln", d.get("equity","")))' 2>/dev/null || true)
  POS=$(printf '%s' "$PAPER_RAW" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("positions_count", len(d.get("positions") or [])))' 2>/dev/null || true)
  if [[ -n "$CASH" && -n "$EQUITY" ]]; then
    echo "OK   paper portfolio cash_pln=$CASH equity=$EQUITY positions=$POS"
  else
    echo "FAIL paper portfolio missing cash/equity fields"
    fail=1
  fi
fi

if [[ "$fail" -ne 0 ]]; then
  echo "=== AUDIT FAILED ==="
  exit 1
fi
echo "=== AUDIT PASSED ==="

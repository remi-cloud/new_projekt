#!/usr/bin/env bash
# Verify every MONITORED_ASSETS symbol has a live Yahoo (or mapped) price.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
python <<'PY'
import asyncio, json, sys
from app.data.assets import MONITORED_ASSETS, resolve_yahoo_symbol, is_price_proxy
from app.paper.pricing import get_live_price_async, PaperTradeError

assets, seen = [], set()
for a in MONITORED_ASSETS:
    if a["symbol"] in seen:
        continue
    seen.add(a["symbol"])
    assets.append(a)

sem = asyncio.Semaphore(12)

async def one(a):
    async with sem:
        sym = a["symbol"]
        try:
            p, c = await get_live_price_async(sym)
            return {"symbol": sym, "ok": True, "price": float(p), "currency": c,
                    "yahoo": resolve_yahoo_symbol(sym), "proxy": is_price_proxy(sym)}
        except Exception as e:
            msg = e.message if isinstance(e, PaperTradeError) else f"{type(e).__name__}:{e}"
            return {"symbol": sym, "ok": False, "err": msg,
                    "yahoo": resolve_yahoo_symbol(sym), "proxy": is_price_proxy(sym)}

async def main():
    out = []
    for i in range(0, len(assets), 25):
        out.extend(await asyncio.gather(*[one(a) for a in assets[i:i+25]]))
        print(f"{min(i+25,len(assets))}/{len(assets)}", flush=True)
    fail = [r for r in out if not r["ok"]]
    print(json.dumps({
        "total": len(out),
        "ok": len(out) - len(fail),
        "fail": len(fail),
        "proxies": sum(1 for r in out if r.get("proxy")),
        "failures": fail,
    }, indent=2))
    sys.exit(1 if fail else 0)

asyncio.run(main())
PY

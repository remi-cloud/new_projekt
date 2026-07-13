#!/usr/bin/env python3
"""Benchmark hot paths — answers: is Python the bottleneck?"""

from __future__ import annotations

import asyncio
import resource
import sys
import time
import tracemalloc
from pathlib import Path

# backend/ on path when run from repo root or backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.cycles.regional_macro import build_regional_cycles_snapshot
from app.data.assets import MONITORED_ASSETS
from app.data.fast_quotes import fetch_fast_quotes
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes_with_stats
from app.scanners.asset_analyzer import analyzer, build_market_summary
from app.scanners.opportunity_scanner import ASSET_MAP


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


async def timed(label: str, coro):
    t0 = time.perf_counter()
    result = await coro
    elapsed = time.perf_counter() - t0
    return label, elapsed, result


async def run_benchmarks(runs: int = 2) -> None:
    n = len(MONITORED_ASSETS)
    print("=" * 60)
    print("CYCLICAL TRADER — benchmark wydajności (Python)")
    print("=" * 60)
    print(f"Instrumentów monitorowanych: {n}")
    print(f"RSS przed startem: {_rss_mb():.1f} MB")
    print()

    tracemalloc.start()
    t_total = time.perf_counter()

    # 1. Cycles (pure CPU)
    _, t_btc_ath, btc_data = await timed("CoinGecko BTC ATH", fetch_bitcoin_ath())
    ath_date, ath_price, btc_price = btc_data
    t0 = time.perf_counter()
    bitcoin_cycle = analyze_bitcoin_cycle(ath_date, ath_price, btc_price)
    presidential_cycle = analyze_presidential_cycle()
    build_regional_cycles_snapshot()
    t_cycles = time.perf_counter() - t0
    print(f"  CoinGecko BTC ATH .............. {t_btc_ath:6.2f}s")
    print(f"  Analiza cykli (CPU, lokalnie) ... {t_cycles:6.3f}s")

    # 2. Full quotes + 52w stats (dominant I/O in full scan)
    tick_times: list[float] = []
    scan_times: list[float] = []
    quotes = []
    price_stats = {}
    reassess_times: list[float] = []

    for i in range(runs):
        _, t_scan_io, (quotes, price_stats) = await timed(
            f"fetch_quotes_with_stats run {i+1}",
            fetch_quotes_with_stats(),
        )
        scan_times.append(t_scan_io)

        t0 = time.perf_counter()
        assessments = analyzer.assess_all(
            quotes, ASSET_MAP, bitcoin_cycle, presidential_cycle, price_stats
        )
        build_market_summary(assessments)
        reassess_times.append(time.perf_counter() - t0)

        _, t_tick, fast = await timed(f"fetch_fast_quotes run {i+1}", fetch_fast_quotes())
        tick_times.append(t_tick)
        print(f"  Run {i+1}: pełny fetch+stats {t_scan_io:.2f}s | reassess {reassess_times[-1]:.3f}s | fast tick {t_tick:.2f}s ({len(fast)} quotes)")

    avg_scan = sum(scan_times) / len(scan_times)
    avg_tick = sum(tick_times) / len(tick_times)
    avg_reassess = sum(reassess_times) / len(reassess_times)
    total_scan = t_btc_ath + t_cycles + avg_scan + avg_reassess

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - t_total

    print()
    print("-" * 60)
    print("PODSUMOWANIE (średnia z runów I/O)")
    print("-" * 60)
    print(f"  Pełny skan (I/O Yahoo/Investing) ... {avg_scan:6.2f}s  ({avg_scan/total_scan*100:.0f}% czasu skanu)")
    print(f"  Reassessment 246 instrumentów .... {avg_reassess:6.3f}s  ({avg_reassess/total_scan*100:.1f}% czasu skanu)")
    print(f"  Cykle + CoinGecko ................ {t_btc_ath + t_cycles:6.2f}s")
    print(f"  → Szacowany pełny skan ........... {total_scan:6.2f}s")
    print(f"  Tick cen (co 30s) ................ {avg_tick:6.2f}s")
    print()
    print(f"  Pobrane notowania (ostatni run) .. {len(quotes)}/{n}")
    print(f"  RSS peak ......................... {_rss_mb():.1f} MB")
    print(f"  Python heap peak (tracemalloc) ... {peak / 1024 / 1024:.1f} MB")
    print(f"  Czas całego benchmarku ........... {elapsed:.1f}s")
    print()
    print("WERDYKT")
    print("-" * 60)
    io_pct = avg_scan / total_scan * 100 if total_scan else 0
    if io_pct > 85:
        print(f"  Wąskie gardło: SIEĆ I/O ({io_pct:.0f}%), nie Python.")
        print("  Rust przyspieszy głównie równoległość HTTP — zysk umiarkowany")
        print("  dopóki Yahoo/Investing limitują requesty.")
    elif avg_reassess > 2.0:
        print("  Wąskie gardło: logika reassessment — Rust mógłby tu pomóc.")
    else:
        print("  Python wystarcza — CPU < 2s, dominuje I/O zewnętrzne API.")

    if total_scan > 120:
        print(f"  ⚠ Skan > 2 min — UX cierpi, ale głównie przez {n} requestów HTTP.")
    if avg_tick > 15:
        print(f"  ⚠ Tick > 15s — ryzyko nakładania się ticków (interwał 30s).")
    elif avg_tick < 5:
        print(f"  ✓ Tick {avg_tick:.1f}s << 30s interwał — OK.")

    print("=" * 60)


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    asyncio.run(run_benchmarks(runs=runs))

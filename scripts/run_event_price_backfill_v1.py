#!/usr/bin/env python3
"""Signal Spine IO v1 — Event Price Backfill Demo Runner (RC).

Usage:
    # Fixture mode (default, no network, deterministic)
    python scripts/run_event_price_backfill_v1.py --mode fixture

    # Network mode (real Binance, no fixture fallback)
    python scripts/run_event_price_backfill_v1.py --mode network

    # With custom output directory
    python scripts/run_event_price_backfill_v1.py --mode fixture --output-dir ./results/price_backfill

Design:
  - Three modes: fixture / network / network_with_cache
  - fixture mode: deterministic, offline, uses pre-built data
  - network mode: real Binance API; failure returns unavailable, NOT fixture
  - All times in UTC
  - No API key required (Binance public REST)
  - No write-back to Notion, database, or production
  - No trading decisions or recommendations
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.event_price_backfill import (
    EventPriceBackfill,
    PriceBackfillResult,
    BackfillMode,
    OBSERVATION_WINDOWS,
    FIXTURE_REFERENCE_TIME_UTC,
    utc_now,
)


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_pass(text: str, indent: int = 2):
    print(f"{' ' * indent}[PASS] {text}")


def print_fail(text: str, indent: int = 2):
    print(f"{' ' * indent}[FAIL] {text}")


def print_info(text: str, indent: int = 2):
    print(f"{' ' * indent}[INFO] {text}")


def fmt_dec(val):
    if val is None:
        return "N/A"
    return f"{val:+.6f}"


def fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val:+.4f}%"


def run_fixture_demo(output_dir: str, mode: str):
    """Run fixture-based price backfill demo."""
    print_header(f"Fixture Demo (mode={mode}) — Full 24h Data (BTC, ETH, SOL)")

    bf = EventPriceBackfill(mode=mode)
    results = bf.backfill(
        event_id="fixture_demo_001",
        event_time=FIXTURE_REFERENCE_TIME_UTC,
        assets=["BTC", "ETH", "SOL"],
        fixture_id="kline_full_24h",
    )

    for r in results:
        t0 = r.t0_snapshot
        print_info(f"[{r.asset} -> {r.mapped_symbol}] t0={t0.price} source={t0.source} lag={t0.lag_seconds}s | status={r.backfill_status} mode={r.mode}")
        for w in r.windows:
            snap = w.target_price_snapshot
            ret_d = fmt_dec(w.return_decimal)
            ret_p = fmt_pct(w.return_percent)
            btc_ab = fmt_dec(w.btc_abnormal_return_decimal)
            eth_ab = fmt_dec(w.eth_abnormal_return_decimal)
            print_info(f"  {w.window}: price={snap.price} ret={ret_d}({ret_p}) "
                       f"btc_ab={btc_ab} eth_ab={eth_ab} "
                       f"[{w.status}] lag={snap.lag_seconds}s src={snap.source}")

    # Verify self-benchmark
    btc_result = next((r for r in results if r.asset == "BTC"), None)
    if btc_result:
        for w in btc_result.windows:
            if w.btc_abnormal_return_decimal is not None:
                print_fail(f"BTC self-benchmark: btc_abnormal should be None, got {w.btc_abnormal_return_decimal}")
            else:
                print_pass(f"BTC {w.window}: self-benchmark correct (btc_abnormal=None)")

    return results


def run_network_demo(output_dir: str):
    """Run with real Binance API (may fail without network — that's OK)."""
    print_header("Network Demo — Real Binance API")

    bf = EventPriceBackfill(mode=BackfillMode.NETWORK)
    results = bf.backfill(
        event_id="network_demo_001",
        event_time=utc_now(),
        assets=["BTC", "ETH"],
    )

    for r in results:
        t0 = r.t0_snapshot
        net_err = r.network_error or ""
        print_info(f"[{r.asset}] t0={t0.price} src={t0.source} "
                   f"status={r.backfill_status} err={net_err[:80] if net_err else 'none'}")
        for w in r.windows:
            snap = w.target_price_snapshot
            ret_d = fmt_dec(w.return_decimal) if w.status == "completed" else "N/A"
            print_info(f"  {w.window}: price={snap.price} ret={ret_d} [{w.status}] src={snap.source}")

    return results


def save_json_output(results: list[PriceBackfillResult], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "price_backfill_results.json")
    data = {
        "generated_at": utc_now(),
        "result_count": len(results),
        "results": [r.as_dict() for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_csv_output(results: list[PriceBackfillResult], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "price_backfill_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "event_id", "mode", "asset", "symbol", "t0_price", "t0_source", "t0_lag_s",
            "window", "target_price", "return_decimal", "return_percent",
            "btc_abnormal_dec", "eth_abnormal_dec", "status", "snapshot_source", "snapshot_lag_s",
        ])
        for r in results:
            for w in r.windows:
                snap = w.target_price_snapshot
                writer.writerow([
                    r.event_id, r.mode, r.asset, r.mapped_symbol,
                    r.t0_snapshot.price, r.t0_snapshot.source, r.t0_snapshot.lag_seconds,
                    w.window, snap.price,
                    f"{w.return_decimal:.6f}" if w.return_decimal is not None else "",
                    f"{w.return_percent:.4f}" if w.return_percent is not None else "",
                    f"{w.btc_abnormal_return_decimal:.6f}" if w.btc_abnormal_return_decimal is not None else "",
                    f"{w.eth_abnormal_return_decimal:.6f}" if w.eth_abnormal_return_decimal is not None else "",
                    w.status, snap.source, snap.lag_seconds,
                ])
    return path


def print_results_summary(results: list[PriceBackfillResult]):
    print_header("Results Summary")
    print(f"  Total assets: {len(results)} | Mode: {results[0].mode if results else '?'}")
    for r in results:
        t0 = r.t0_snapshot
        print(f"\n  [{r.asset} -> {r.mapped_symbol}] t0={t0.price}(src={t0.source}) "
              f"status={r.backfill_status} calc_ver={r.calculation_version}")
        if r.error_reason:
            print(f"    ERROR: {r.error_reason}")
        for w in r.windows:
            snap = w.target_price_snapshot
            if w.status == "completed":
                print(f"    {w.window}: {fmt_dec(w.return_decimal)} ({fmt_pct(w.return_percent)}) "
                      f"ab_btc={fmt_dec(w.btc_abnormal_return_decimal)} "
                      f"ab_eth={fmt_dec(w.eth_abnormal_return_decimal)} "
                      f"[price={snap.price} lag={snap.lag_seconds}s src={snap.source}]")
            elif w.status == "pending":
                print(f"    {w.window}: [PENDING — event not yet mature]")
            else:
                print(f"    {w.window}: [{w.status}] {snap.error_reason or ''}")


def main():
    parser = argparse.ArgumentParser(
        description="Event Price Backfill v1 (RC) — Demo Runner",
    )
    parser.add_argument(
        "--mode", type=str, default="fixture",
        choices=["fixture", "network", "network_with_cache"],
        help="Backfill mode (default: fixture)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: ./results/price_backfill)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(_PROJECT_ROOT, "results", "price_backfill")
    os.makedirs(output_dir, exist_ok=True)

    mode_label = {"fixture": "FIXTURE (offline, deterministic)",
                  "network": "NETWORK (real Binance, no fixture fallback)",
                  "network_with_cache": "NETWORK_WITH_CACHE"}.get(args.mode, args.mode)

    print(f"{'=' * 60}")
    print(f"  Event Price Backfill v1 (RC) — Demo Runner")
    print(f"  Mode:   {mode_label}")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 60}")

    if args.mode == "fixture":
        results = run_fixture_demo(output_dir, args.mode)
    else:
        results = run_network_demo(output_dir)

    print_results_summary(results)

    json_path = save_json_output(results, output_dir)
    csv_path = save_csv_output(results, output_dir)
    print(f"\n  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    print(f"\n{'=' * 60}")
    print(f"  Demo Complete")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

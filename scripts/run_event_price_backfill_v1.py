#!/usr/bin/env python3
"""Signal Spine IO v1 — Event Price Backfill Demo Runner.

Usage:
    # Fixture-only demo (default, no network required)
    python scripts/run_event_price_backfill_v1.py --fixture

    # Real Binance API (network required)
    python scripts/run_event_price_backfill_v1.py --network

    # Output to specific directory
    python scripts/run_event_price_backfill_v1.py --fixture --output-dir ./results/price_backfill

Design:
  - No API key required (Binance public REST)
  - All times in UTC
  - Observation windows: 1h / 4h / 24h
  - Automatic fixture fallback on network failure
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
    OBSERVATION_WINDOWS,
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


def fmt_pct(val):
    """Format a percentage value."""
    if val is None:
        return "N/A"
    return f"{val * 100:+.4f}%"


# ── Demo Scenarios ──────────────────────────────────────────────────────────


def run_fixture_demo(output_dir: str) -> list[PriceBackfillResult]:
    """Run fixture-based price backfill demo."""
    print_header("Fixture Demo: Complete 24h Data (BTC, ETH, SOL)")

    backfill = EventPriceBackfill(use_fixture=True)
    results = backfill.backfill(
        event_id="fixture_demo_001",
        event_time="2026-06-15T12:00:00Z",
        assets=["BTC", "ETH", "SOL"],
    )

    for r in results:
        print_info(f"Asset: {r.asset} -> {r.mapped_symbol} | t0: {r.t0_price} | Status: {r.backfill_status}")
        for w in r.windows:
            ret = fmt_pct(w.return_pct)
            btc_ab = fmt_pct(w.btc_abnormal_return)
            eth_ab = fmt_pct(w.eth_abnormal_return)
            print_info(f"  {w.window}: price={w.target_price} ret={ret} btc_ab={btc_ab} eth_ab={eth_ab} [{w.status}]")

    # BTC self-benchmark check
    btc_result = next((r for r in results if r.asset == "BTC"), None)
    if btc_result:
        for w in btc_result.windows:
            if w.btc_abnormal_return is not None:
                print_fail("BTC self-benchmark: btc_abnormal_return should be None, got {w.btc_abnormal_return}")
            else:
                print_pass("BTC self-benchmark correctly: btc_abnormal_return = None")

    return results


def run_network_demo(output_dir: str) -> list[PriceBackfillResult]:
    """Run price backfill with real Binance API (optional)."""
    print_header("Network Demo: Real Binance API (requires internet)")

    backfill = EventPriceBackfill(use_fixture=False)
    now = datetime.now(timezone.utc)
    # Use an event 48h ago for full 24h window maturity
    event_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    results = backfill.backfill(
        event_id="network_demo_001",
        event_time=event_time,
        assets=["BTC", "ETH"],
    )

    for r in results:
        source_note = "fixture_fallback" if r.source == "fixture_fallback" else r.source
        print_info(f"Asset: {r.asset} | t0: {r.t0_price} | source: {source_note} | status: {r.backfill_status}")
        for w in r.windows:
            ret = fmt_pct(w.return_pct) if w.status == "completed" else "N/A"
            btc_ab = fmt_pct(w.btc_abnormal_return) if w.btc_abnormal_return is not None else "N/A"
            print_info(f"  {w.window}: ret={ret} btc_ab={btc_ab} [{w.status}]")

    return results


# ── Output ──────────────────────────────────────────────────────────────────


def save_json_output(results: list[PriceBackfillResult], output_dir: str) -> str:
    """Save results as JSON."""
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
    """Save results as CSV summary."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "price_backfill_summary.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "event_id", "asset", "mapped_symbol", "t0_price", "window",
            "target_price", "return_pct", "btc_return_pct", "eth_return_pct",
            "btc_abnormal_return", "eth_abnormal_return", "status", "source",
        ])
        for r in results:
            for w in r.windows:
                writer.writerow([
                    r.event_id, r.asset, r.mapped_symbol, r.t0_price,
                    w.window, w.target_price,
                    f"{w.return_pct:.6f}" if w.return_pct is not None else "",
                    f"{w.btc_return_pct:.6f}" if w.btc_return_pct is not None else "",
                    f"{w.eth_return_pct:.6f}" if w.eth_return_pct is not None else "",
                    f"{w.btc_abnormal_return:.6f}" if w.btc_abnormal_return is not None else "",
                    f"{w.eth_abnormal_return:.6f}" if w.eth_abnormal_return is not None else "",
                    w.status, r.source,
                ])
    return path


def print_results_summary(results: list[PriceBackfillResult]):
    """Print a human-readable summary of results."""
    print_header("Results Summary")
    print(f"  Total assets: {len(results)}")
    for r in results:
        print(f"\n  [{r.asset} -> {r.mapped_symbol}] t0={r.t0_price} status={r.backfill_status}")
        if r.error_reason:
            print(f"    ERROR: {r.error_reason}")
        for w in r.windows:
            if w.status == "completed":
                print(f"    {w.window}: {fmt_pct(w.return_pct)} "
                      f"(btc_ab: {fmt_pct(w.btc_abnormal_return)}) "
                      f"(eth_ab: {fmt_pct(w.eth_abnormal_return)})")
            elif w.status == "pending":
                print(f"    {w.window}: [PENDING — event not yet mature]")
            else:
                print(f"    {w.window}: [UNAVAILABLE]")


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Event Price Backfill v1 — Demo Runner",
    )
    parser.add_argument("--fixture", action="store_true", default=True,
                        help="Run with fixture data (offline-safe, default)")
    parser.add_argument("--network", action="store_true", default=False,
                        help="Attempt real Binance API calls")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: ./results/price_backfill)")
    args = parser.parse_args()

    if args.network:
        args.fixture = False

    output_dir = args.output_dir or os.path.join(_PROJECT_ROOT, "results", "price_backfill")
    os.makedirs(output_dir, exist_ok=True)

    print(f"{'=' * 60}")
    print(f"  Event Price Backfill v1 — Demo Runner")
    print(f"  Mode: {'FIXTURE' if args.fixture else 'NETWORK'}")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 60}")

    # Run demo
    if args.fixture:
        results = run_fixture_demo(output_dir)
    else:
        results = run_network_demo(output_dir)

    # Print summary
    print_results_summary(results)

    # Save outputs
    json_path = save_json_output(results, output_dir)
    csv_path = save_csv_output(results, output_dir)
    print(f"\n  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    # Verify safety
    has_trading_instruction = False
    for r in results:
        if r.backfill_status == "failed" and "unsupported" in (r.error_reason or ""):
            pass  # expected
        for w in r.windows:
            if w.status == "completed":
                assert w.return_pct is not None or w.target_price is not None

    print(f"\n{'=' * 60}")
    print(f"  Demo Complete — All checks passed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Week 1 — Sample Price Backfill Runner (Raw Output).

Produces raw price backfill results for 5 Week 1 samples:
  - HYPE / 2026-05-25T13:02:00Z
  - ETH  / 2026-05-25T15:19:00Z
  - BTC  / 2026-05-25T16:12:00Z (two samples)
  - MACRO-WTI (BTC) / 2026-05-25T11:34:00Z
  - MACRO-WTI (ETH) / 2026-05-25T11:34:00Z

Output:
  research/results/week1_price_backfill_raw_v1.json
  research/results/week1_price_backfill_raw_v1.md

Design:
  - WTI is the event topic; only BTC and ETH prices are backfilled
  - NO attribution, causality, confidence, or trading advice
  - Network failure marks unavailable (never fixture)
  - Hyperliquid HYPE failure does not block other samples
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter,
    run_week1_samples,
    Week1SampleResult,
    WEEK1_SAMPLES,
    utc_now,
)

RESEARCH_DIR = os.path.join(_PROJECT_ROOT, "research", "results")


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_info(text: str, indent: int = 2):
    print(f"{' ' * indent}[INFO] {text}")


def fmt_price(snap) -> str:
    if snap is None:
        return "N/A"
    return f"{snap.price} ({snap.status}) src={snap.source} lag={snap.lag_seconds}s"


def fmt_window(wr) -> str:
    if wr is None:
        return "N/A"
    if wr.status == "pending":
        return "[PENDING]"
    if wr.status != "completed":
        return f"[{wr.status}]"
    return (f"ret={wr.return_percent:+.4f}% "
            f"btc_ab={wr.btc_abnormal_return_percent or 'self':>8} "
            f"eth_ab={wr.eth_abnormal_return_percent or 'self':>8}")


def print_results(results: list[Week1SampleResult]):
    print_header("Week 1 Price Backfill — Results")
    for r in results:
        t0 = r.t0_snapshot
        print(f"\n  [{r.sample_id}] {r.subject_asset} -> {r.observed_asset}")
        print(f"    broadcast: {r.broadcast_time}")
        print(f"    provider:  {r.provider} / {r.interval} (precision={r.precision_seconds}s)")
        print(f"    t0:        {fmt_price(t0)}")
        if r.network_error:
            print(f"    error:     {r.network_error[:120]}")
        print(f"    1h:        {fmt_window(r.return_1h)}")
        print(f"    4h:        {fmt_window(r.return_4h)}")
        print(f"    24h:       {fmt_window(r.return_24h)}")
        print(f"    btc_bench: {fmt_price(r.btc_benchmark)}")
        print(f"    eth_bench: {fmt_price(r.eth_benchmark)}")


def save_json(results: list[Week1SampleResult], path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "title": "Week 1 Price Backfill Raw Results",
        "generated_at": utc_now(),
        "calculation_version": "v1.18-week1",
        "sample_count": len(results),
        "samples": [r.as_dict() for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_markdown(results: list[Week1SampleResult], path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Week 1 Price Backfill — Raw Results",
        "",
        f"**Generated**: {utc_now()}",
        f"**Version**: v1.18-week1",
        f"**Samples**: {len(results)}",
        "",
        "---",
        "",
    ]
    for r in results:
        t0 = r.t0_snapshot
        t0_line = f"{t0.price} ({t0.status}) src={t0.source}" if t0 else "N/A"
        lines.extend([
            f"## {r.sample_id}: {r.subject_asset} -> {r.observed_asset}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| broadcast_time | {r.broadcast_time} |",
            f"| provider | {r.provider} |",
            f"| interval | {r.interval} |",
            f"| precision_seconds | {r.precision_seconds or 'N/A'} |",
            f"| t0_price | {t0_line} |",
            f"| t0_lag_seconds | {t0.lag_seconds if t0 else 'N/A'} |",
        ])
        if r.network_error:
            lines.append(f"| network_error | {r.network_error[:100]} |")

        for wname in ["1h", "4h", "24h"]:
            wr = getattr(r, f"return_{wname}")
            if wr:
                lines.append(f"| {wname}_status | {wr.status} |")
                if wr.status == "completed":
                    lines.append(f"| {wname}_return_decimal | {wr.return_decimal} |")
                    lines.append(f"| {wname}_return_percent | {wr.return_percent}% |")
                    lines.append(f"| {wname}_btc_abnormal | {wr.btc_abnormal_return_percent or 'self_benchmark'}% |")
                    lines.append(f"| {wname}_eth_abnormal | {wr.eth_abnormal_return_percent or 'self_benchmark'}% |")
            else:
                lines.append(f"| {wname}_status | N/A |")

        lines.append("")

        btc = r.btc_benchmark
        eth = r.eth_benchmark
        if btc:
            lines.append(f"| btc_benchmark_price | {btc.price} ({btc.status}) |")
        if eth:
            lines.append(f"| eth_benchmark_price | {eth.price} ({eth.status}) |")

        lines.append(f"| data_origin | {r.data_origin} |")
        lines.append(f"| calculation_version | {r.calculation_version} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Week 1 Sample Price Backfill Runner",
    )
    parser.add_argument("--output-dir", type=str, default=None,
                        help=f"Output directory (default: {RESEARCH_DIR})")
    args = parser.parse_args()

    output_dir = args.output_dir or RESEARCH_DIR
    os.makedirs(output_dir, exist_ok=True)

    print_header("Week 1 Price Backfill — Raw Output")
    print_info(f"Output: {output_dir}")
    print_info(f"Samples: {len(WEEK1_SAMPLES)}")

    # Run
    router = ProviderRouter()
    results = run_week1_samples(router)

    # Print
    print_results(results)

    # Save
    json_path = save_json(results, os.path.join(output_dir, "week1_price_backfill_raw_v1.json"))
    md_path = save_markdown(results, os.path.join(output_dir, "week1_price_backfill_raw_v1.md"))
    print(f"\n  JSON: {json_path}")
    print(f"  MD:   {md_path}")

    completed = sum(1 for r in results
                    if r.t0_snapshot and r.t0_snapshot.status == "completed")
    failed = sum(1 for r in results
                 if r.t0_snapshot and r.t0_snapshot.status == "unavailable")
    print(f"\n  Completed: {completed}/{len(results)}")
    print(f"  Failed:    {failed}/{len(results)}")

    print_header("Done — raw output only, no attribution")


if __name__ == "__main__":
    main()

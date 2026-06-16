#!/usr/bin/env python3
"""Week 1 RC — Network Price Backfill Runner (Real API, no fixture).

Usage:
    python -X utf8 scripts/run_week1_sample_backfill_v1.py --mode network

Output:
    research/week1_price_backfill_raw_v1.json
    research/week1_price_backfill_raw_v1.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter, run_week1, Week1ObservationResult,
    W1_SAMPLES, W1_WTI, utc_now,
)


OUTPUT_DIR = os.path.join(PROJ, "research")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fmt_px(snap) -> str:
    if snap is None:
        return "N/A"
    return f"{snap.price} ({snap.status}) src={snap.source} lag={snap.lag_seconds}s"


def fmt_win(w) -> str:
    if w is None:
        return "N/A"
    if w.status == "pending":
        return "[PENDING]"
    if w.status != "completed":
        return f"[{w.status}]"
    return (f"ret={w.return_percent:+.4f}%  "
            f"btc_ab={w.btc_abnormal_return_percent or 'self':>8}  "
            f"eth_ab={w.eth_abnormal_return_percent or 'self':>8}")


def print_results(results: list[Week1ObservationResult]):
    print(f"\n{'=' * 60}")
    print(f"  Week 1 Price Backfill — {len(results)} Observations")
    print(f"{'=' * 60}")
    for r in results:
        print(f"\n  [{r.result_id}] {r.subject_asset} -> {r.observed_asset}")
        print(f"    bt:       {r.broadcast_time_utc}")
        print(f"    provider: {r.provider} / {r.interval}  sel={r.selection_policy}")
        print(f"    signed_lag: {r.signed_lag_seconds}s")
        print(f"    t0:       {fmt_px(r.t0_snapshot)}")
        if r.network_error:
            print(f"    error:    {r.network_error[:120]}")
        print(f"    1h:       {fmt_win(r.return_1h)}")
        print(f"    4h:       {fmt_win(r.return_4h)}")
        print(f"    24h:      {fmt_win(r.return_24h)}")


def save_json(results, path):
    completed = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "completed")
    unavail = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "unavailable")
    partial = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status not in ("completed", "unavailable"))
    errors = [r.network_error for r in results if r.network_error]

    data = {
        "run_mode": "network",
        "generated_at": utc_now(),
        "source_branch": "workbench/week1-price-providers-v1",
        "source_commit": os.popen("git rev-parse HEAD 2>/dev/null").read().strip() or "unknown",
        "calculation_version": "v1.18-week1-rc",
        "samples_expected": 5,
        "observations_expected": 6,
        "observations_completed": completed,
        "observations_unavailable": unavail,
        "observations_partial": partial,
        "network_errors": errors if errors else [],
        "results": [r.as_dict() for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_md(results, path):
    lines = ["# Week 1 Price Backfill — Network Raw Results", "",
             f"**Run mode**: network", f"**Generated**: {utc_now()}", f"**Observations**: {len(results)}", "",
             "---", ""]
    for r in results:
        t0 = r.t0_snapshot
        t0l = f"{t0.price} ({t0.status}) src={t0.source}" if t0 else "N/A"
        lines += [f"## {r.result_id}: {r.subject_asset} -> {r.observed_asset}", "",
                  f"| Field | Value |", f"|-------|-------|",
                  f"| broadcast_time_utc | {r.broadcast_time_utc} |",
                  f"| provider | {r.provider} |", f"| interval | {r.interval} |",
                  f"| precision_seconds | {r.precision_seconds or 'N/A'} |",
                  f"| selection_policy | {r.selection_policy or 'N/A'} |",
                  f"| signed_lag_seconds | {r.signed_lag_seconds or 'N/A'} |",
                  f"| t0_price | {t0l} |"]
        if r.network_error:
            lines.append(f"| network_error | {r.network_error[:100]} |")
        for wn in ("1h", "4h", "24h"):
            w = getattr(r, f"return_{wn}")
            if w:
                lines.append(f"| {wn}_status | {w.status} |")
                if w.status == "completed":
                    lines.append(f"| {wn}_return_percent | {w.return_percent}% |")
                    lines.append(f"| {wn}_btc_abnormal | {w.btc_abnormal_return_percent or 'self_benchmark'}% |")
                    lines.append(f"| {wn}_eth_abnormal | {w.eth_abnormal_return_percent or 'self_benchmark'}% |")
        lines += [f"| data_origin | {r.data_origin} |",
                  f"| calculation_version | {r.calculation_version} |", "", "---", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser(description="Week 1 RC — Network Price Backfill")
    parser.add_argument("--mode", default="network", choices=["network"],
                        help="Run mode (must be 'network' for real API)")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"  Week 1 Price Backfill — mode={args.mode}")
    print(f"  Samples: {len(W1_SAMPLES)} + {len(W1_WTI)} WTI = {len(W1_SAMPLES) + len(W1_WTI)} observations")
    print(f"{'=' * 60}")

    router = ProviderRouter()
    results = run_week1(router)

    print_results(results)

    jp = save_json(results, os.path.join(OUTPUT_DIR, "week1_price_backfill_raw_v1.json"))
    mp = save_md(results, os.path.join(OUTPUT_DIR, "week1_price_backfill_raw_v1.md"))

    comp = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "completed")
    fail = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "unavailable")
    print(f"\n  JSON: {jp}")
    print(f"  MD:   {mp}")
    print(f"  Completed: {comp}/{len(results)} | Unavailable: {fail}/{len(results)}")
    print(f"{'=' * 60}")
    print(f"  Done — raw output only, no attribution")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

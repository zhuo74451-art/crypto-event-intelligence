#!/usr/bin/env python3
"""Week 1 RC — Network Price Backfill Runner (Real API, no fixture).

Usage:
    python -X utf8 scripts/run_week1_sample_backfill_v1.py --mode network

Output:
    research/week1_price_backfill_raw_v1.json
    research/week1_price_backfill_raw_v1.md
"""

import argparse
import json
import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter, run_week1, Week1ObservationResult,
    W1_SAMPLES, W1_WTI, utc_now,
)

OUTPUT_DIR = os.path.join(PROJ, "research")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _git_head() -> str:
    """Get current commit SHA via subprocess with explicit cwd."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJ, text=True,
        ).strip()
    except Exception:
        return "unknown"


def fmt_px(snap):
    if snap is None:
        return "N/A"
    return f"{snap.price} ({snap.status}) src={snap.source} lag={snap.lag_seconds}s"


def _val_or_na(val, fmt=None):
    """Return formatted value, or 'N/A' if None."""
    if val is None:
        return "N/A"
    if fmt:
        return fmt(val)
    return str(val)


def _self_or_val(val):
    """Return 'self_benchmark' if None, else the value."""
    if val is None:
        return "self_benchmark"
    return val


def fmt_win(w):
    if w is None:
        return "N/A"
    if w.status == "pending":
        return "[PENDING]"
    if w.status != "completed":
        return f"[{w.status}]"
    btc_ab = _self_or_val(w.btc_abnormal_return_percent)
    eth_ab = _self_or_val(w.eth_abnormal_return_percent)
    return f"ret={w.return_percent:+.4f}%  btc_ab={btc_ab:>8}  eth_ab={eth_ab:>8}"


def print_results(results):
    print(f"\n{'=' * 60}")
    print(f"  Week 1 Price Backfill — {len(results)} Observations")
    print(f"{'=' * 60}")
    for r in results:
        sl = _val_or_na(r.signed_lag_seconds)
        print(f"\n  [{r.result_id}] {r.subject_asset} -> {r.observed_asset}")
        print(f"    bt:       {r.broadcast_time_utc}")
        print(f"    t0_basis: {r.t0_basis}")
        print(f"    provider: {r.provider} / {r.interval}  sel={r.selection_policy}  lag={sl}s")
        print(f"    t0:       {fmt_px(r.t0_snapshot)}")
        if r.network_error:
            print(f"    error:    {r.network_error[:120]}")
        for wn in ("1h", "4h", "24h"):
            w = getattr(r, f"return_{wn}")
            print(f"    {wn}:       {fmt_win(w)}")


def save_json(results, path, code_commit=None):
    completed = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "completed")
    unavail = sum(1 for r in results if r.t0_snapshot and r.t0_snapshot.status == "unavailable")
    errors = [r.network_error for r in results if r.network_error]
    unique_poks = list({r.price_observation_key for r in results}) if results else []
    data = {
        "run_mode": "network",
        "generated_at": utc_now(),
        "source_branch": "workbench/week1-price-providers-v1",
        "source_commit": _git_head(),
        "calculation_code_commit": code_commit or _git_head(),
        "calculation_version": "v1.18-week1-rc",
        "samples_expected": 5,
        "observations_expected": 6,
        "sample_links_expected": 6,
        "sample_links_actual": len(results),
        "unique_price_observations": len(unique_poks),
        "price_observation_keys": unique_poks,
        "observations_completed": completed,
        "observations_unavailable": unavail,
        "observations_partial": 0,
        "network_errors": errors if errors else [],
        "results": [r.as_dict() for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_md(results, path):
    lines = [
        "# Week 1 Price Backfill — Network Raw Results", "",
        f"**Run mode**: network", f"**Generated**: {utc_now()}", f"**Observations**: {len(results)}",
        f"**Source commit**: {_git_head()}", "",
        "---", "",
    ]
    for r in results:
        t0 = r.t0_snapshot
        t0_line = f"{t0.price} ({t0.status}) src={t0.source} lag={t0.lag_seconds}s" if t0 else "N/A"
        sl = _val_or_na(r.signed_lag_seconds)
        lines += [
            f"## {r.result_id}: {r.subject_asset} -> {r.observed_asset}", "",
            "| Field | Value |", "|-------|-------|",
            f"| broadcast_time_utc | {r.broadcast_time_utc} |",
            f"| t0_basis | {r.t0_basis} |",
            f"| provider | {r.provider} |",
            f"| interval | {r.interval} |",
            f"| precision_seconds | {_val_or_na(r.precision_seconds)} |",
            f"| selection_policy | {_val_or_na(r.selection_policy)} |",
            f"| signed_lag_seconds | {sl} |",
            f"| t0_price | {t0_line} |",
        ]
        if r.network_error:
            lines.append(f"| network_error | {r.network_error[:100]} |")
        for wn in ("1h", "4h", "24h"):
            w = getattr(r, f"return_{wn}")
            if w:
                lines.append(f"| {wn}_status | {w.status} |")
                if w.status == "completed":
                    ab_btc = _self_or_val(w.btc_abnormal_return_percent)
                    ab_eth = _self_or_val(w.eth_abnormal_return_percent)
                    ws = _val_or_na(w.signed_lag_seconds)
                    lines += [
                        f"| {wn}_return_percent | {w.return_percent}% |",
                        f"| {wn}_target_price | {w.target_snapshot.price if w.target_snapshot else 'N/A'} |",
                        f"| {wn}_signed_lag_s | {ws} |",
                        f"| {wn}_btc_abnormal | {ab_btc}% |",
                        f"| {wn}_eth_abnormal | {ab_eth}% |",
                        f"| {wn}_sel_policy | {_val_or_na(w.selection_policy)} |",
                    ]
        lines += [
            f"| data_origin | {r.data_origin} |",
            f"| calculation_version | {r.calculation_version} |", "", "---", "",
        ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser(description="Week 1 RC — Network Price Backfill")
    parser.add_argument("--mode", default="network", choices=["network"])
    parser.add_argument("--code-commit", default=None,
                        help="Commit SHA of the code producing these results (Commit A)")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"  Week 1 Price Backfill — mode={args.mode}")
    print(f"  Code commit: {args.code_commit or _git_head()}")
    print(f"  Observations: {len(W1_SAMPLES) + len(W1_WTI)}")
    print(f"{'=' * 60}")

    router = ProviderRouter()
    results = run_week1(router)

    print_results(results)

    jp = save_json(results, os.path.join(OUTPUT_DIR, "week1_price_backfill_raw_v1.json"),
                   code_commit=args.code_commit)
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

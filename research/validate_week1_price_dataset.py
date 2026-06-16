#!/usr/bin/env python3
"""Week 1 — Dataset Consistency Validator.

Usage:
    python -X utf8 research/validate_week1_price_dataset.py research/week1_price_backfill_raw_v1.json

Exits 0 on pass, 1 on fail with detailed report.
"""

import json
import sys
from collections import Counter


def validate(data: dict) -> tuple[bool, list[str]]:
    """Validate dataset consistency.

    Returns (passed, list_of_violations).
    """
    violations = []
    results = data.get("results", [])

    # ── Summary counts ──
    expected_counts = {
        "observations_expected": 6,
        "samples_expected": 5,
    }
    for field, expected in expected_counts.items():
        actual = data.get(field)
        if actual != expected:
            violations.append(f"{field}: expected {expected}, got {actual}")

    # ── Observed count vs actual ──
    completed = sum(1 for r in results if r.get("t0_snapshot") and r["t0_snapshot"].get("status") == "completed")
    unavailable = sum(1 for r in results if r.get("t0_snapshot") and r["t0_snapshot"].get("status") == "unavailable")
    other = sum(1 for r in results if r not in (completed, unavailable))
    declared_completed = data.get("observations_completed", -1)
    declared_unavail = data.get("observations_unavailable", -1)
    if completed != declared_completed:
        violations.append(f"observations_completed: declared={declared_completed}, actual={completed}")
    if unavailable != declared_unavail:
        violations.append(f"observations_unavailable: declared={declared_unavail}, actual={unavailable}")

    # ── t0_basis check ──
    for r in results:
        rid = r.get("result_id", "?")
        if r.get("t0_basis") != "broadcast_time":
            tb = r.get("t0_basis", "")
            violations.append(f"{rid}: t0_basis='{tb}' != 'broadcast_time'")
        bt = r.get("broadcast_time_utc", "")
        if not bt.endswith("Z"):
            violations.append(f"{rid}: broadcast_time_utc '{bt}' not ending with Z")

    # ── Consistency: t0 unavailable → no completed windows ──
    for r in results:
        rid = r.get("result_id", "?")
        t0 = r.get("t0_snapshot") or {}
        t0_status = t0.get("status", "missing")
        for wn in ("return_1h", "return_4h", "return_24h"):
            w = r.get(wn) or {}
            if t0_status != "completed" and w.get("status") == "completed":
                violations.append(f"{rid}/{wn}: t0={t0_status} but window=completed (impossible)")
            if w.get("status") == "completed":
                ts = w.get("target_snapshot") or {}
                if not ts.get("price"):
                    violations.append(f"{rid}/{wn}: completed but missing target_snapshot price")
                # Recompute return from snapshots
                t0p = t0.get("price")
                tp = ts.get("price")
                if t0p and tp:
                    expected_ret = round((tp / t0p) - 1.0, 6)
                    declared_ret = w.get("return_decimal")
                    if declared_ret is not None and abs(expected_ret - declared_ret) > 0.0001:
                        violations.append(f"{rid}/{wn}: return_decimal mismatch: "
                                          f"recomputed={expected_ret}, declared={declared_ret}")
                # Check benchmark snapshots
                for bm in ("btc_benchmark_t0_snapshot", "btc_benchmark_target_snapshot",
                           "eth_benchmark_t0_snapshot", "eth_benchmark_target_snapshot"):
                    if w.get(bm) is None and w.get("status") == "completed":
                        violations.append(f"{rid}/{wn}: completed but missing {bm}")

    # ── price_observation_key and reuse consistency ──
    seen_poks: dict[str, list[dict]] = {}
    for r in results:
        rid = r.get("result_id", "?")
        pok = r.get("price_observation_key", "")
        if not pok:
            violations.append(f"{rid}: missing price_observation_key")
            continue
        if pok not in seen_poks:
            seen_poks[pok] = []
        seen_poks[pok].append(r)

    for pok, entries in seen_poks.items():
        if len(entries) > 1:
            # Check all entries with same pok have identical snapshots/returns
            first = entries[0]
            for e in entries[1:]:
                eid = e.get("result_id", "?")
                if not e.get("observation_reused"):
                    violations.append(f"{eid}: shares pok '{pok}' with {first.get('result_id')} "
                                      f"but observation_reused=false")
                for wn in ("return_1h", "return_4h", "return_24h"):
                    fw = first.get(wn) or {}
                    ew = e.get(wn) or {}
                    if fw.get("return_decimal") != ew.get("return_decimal"):
                        violations.append(f"{eid}/{wn}: return_decimal differs from {first.get('result_id')} "
                                          f"({ew.get('return_decimal')} vs {fw.get('return_decimal')})")
                    fts = fw.get("target_snapshot") or {}
                    ets = ew.get("target_snapshot") or {}
                    if fts.get("price") != ets.get("price"):
                        violations.append(f"{eid}/{wn}: target price differs from {first.get('result_id')}")

    # ── No fixture sources in network mode ──
    if data.get("run_mode") == "network":
        for r in results:
            rid = r.get("result_id", "?")
            t0 = r.get("t0_snapshot") or {}
            if t0.get("source") and "fixture" in t0["source"]:
                violations.append(f"{rid}: fixture source '{t0['source']}' in network mode")
            for wn in ("return_1h", "return_4h", "return_24h"):
                w = r.get(wn) or {}
                ts = w.get("target_snapshot") or {}
                if ts.get("source") and "fixture" in ts["source"]:
                    violations.append(f"{rid}/{wn}: fixture source '{ts['source']}' in network mode")

    passed = len(violations) == 0
    return passed, violations


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_week1_price_dataset.py <json_file>")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    passed, violations = validate(data)
    print(f"File: {path}")
    print(f"Results: {len(data.get('results', []))}")
    print(f"Completed: {data.get('observations_completed', '?')}")
    print(f"Unavailable: {data.get('observations_unavailable', '?')}")
    print(f"Network errors: {len(data.get('network_errors', []))}")
    print(f"Passed: {passed}")
    if violations:
        print(f"\nViolations ({len(violations)}):")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("[PASS] All consistency checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()

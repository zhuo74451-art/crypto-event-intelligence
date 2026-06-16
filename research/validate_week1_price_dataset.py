#!/usr/bin/env python3
"""Week 1 — Dataset Consistency Validator (v2).

Usage: python -X utf8 research/validate_week1_price_dataset.py <json_file>
Exit 0 = pass, 1 = fail.
"""

import json
import re
import sys


def validate(data: dict) -> tuple[bool, list[str]]:
    violations = []
    results = data.get("results", [])

    # ── 1. calculation_code_commit non-empty 40-char SHA ──
    cc = data.get("calculation_code_commit", "")
    if not re.match(r"^[0-9a-f]{40}$", cc):
        violations.append(f"calculation_code_commit invalid: '{cc}' (expected 40-char hex)")

    # ── 2. source_commit == calculation_code_commit ──
    sc = data.get("source_commit", "")
    if sc != cc:
        violations.append(f"source_commit '{sc}' != calculation_code_commit '{cc}'")

    # ── 3. sample_links_expected == len(results) ──
    sle = data.get("sample_links_expected", -1)
    if sle != len(results):
        violations.append(f"sample_links_expected={sle} != results={len(results)}")

    # ── 4. sample_links_actual == len(results) ──
    sla = data.get("sample_links_actual", -1)
    if sla != len(results):
        violations.append(f"sample_links_actual={sla} != results={len(results)}")

    # ── 5. unique_price_observations == number of unique keys == 5 ──
    actual_poks = {r.get("price_observation_key", "") for r in results}
    declared_upo = data.get("unique_price_observations", -1)
    if declared_upo != len(actual_poks):
        violations.append(f"unique_price_observations declared={declared_upo} actual={len(actual_poks)}")
    if len(actual_poks) != 5:
        violations.append(f"unique_price_observations={len(actual_poks)} != 5")

    # ── 6. price_observation_keys matches actual keys ──
    declared_keys = set(data.get("price_observation_keys", []))
    if declared_keys != actual_poks:
        violations.append(f"price_observation_keys mismatch: declared={declared_keys} actual={actual_poks}")

    # ── 7. Summary counts vs actual ──
    completed = sum(1 for r in results if r.get("t0_snapshot") and r["t0_snapshot"].get("status") == "completed")
    unavailable = sum(1 for r in results if r.get("t0_snapshot") and r["t0_snapshot"].get("status") == "unavailable")
    partial = len(results) - completed - unavailable
    for decl, actual, label in [
        (data.get("observations_completed", -1), completed, "observations_completed"),
        (data.get("observations_unavailable", -1), unavailable, "observations_unavailable"),
    ]:
        if decl != actual:
            violations.append(f"{label}: declared={decl} actual={actual}")

    # ── 8. t0_basis and broadcast_time ──
    for r in results:
        rid = r.get("result_id", "?")
        tb = r.get("t0_basis", "")
        if tb != "broadcast_time":
            violations.append(f"{rid}: t0_basis='{tb}' != broadcast_time")
        bt = r.get("broadcast_time_utc", "")
        if not bt.endswith("Z"):
            violations.append(f"{rid}: broadcast_time_utc '{bt}' not ending with Z")

    # ── 9. t0 unavailable → no completed windows ──
    for r in results:
        rid = r.get("result_id", "?")
        t0 = r.get("t0_snapshot") or {}
        t0s = t0.get("status", "missing")
        for wn in ("return_1h", "return_4h", "return_24h"):
            w = r.get(wn) or {}
            if t0s != "completed" and w.get("status") == "completed":
                violations.append(f"{rid}/{wn}: t0={t0s} but window=completed (impossible)")

    # ── 10. completed: check top-level and window metadata ──
    for r in results:
        rid = r.get("result_id", "?")
        t0s = (r.get("t0_snapshot") or {}).get("status", "")
        if t0s == "completed":
            for field, label in [("selection_policy", "selection_policy"),
                                  ("precision_seconds", "precision_seconds"),
                                  ("signed_lag_seconds", "signed_lag_seconds")]:
                val = r.get(field)
                if val is None:
                    violations.append(f"{rid}: completed but top-level {label} is None")
        for wn in ("return_1h", "return_4h", "return_24h"):
            w = r.get(wn) or {}
            if w.get("status") == "completed":
                for field, label in [("selection_policy", "selection_policy"),
                                      ("precision_seconds", "precision_seconds"),
                                      ("signed_lag_seconds", "signed_lag_seconds"),
                                      ("absolute_lag_seconds", "absolute_lag_seconds")]:
                    if w.get(field) is None:
                        violations.append(f"{rid}/{wn}: completed but {label} is None")
                ts = w.get("target_snapshot") or {}
                if not ts.get("price"):
                    violations.append(f"{rid}/{wn}: completed but missing target_snapshot price")
                # Recompute return
                t0p = (r.get("t0_snapshot") or {}).get("price")
                tp = ts.get("price")
                if t0p and tp:
                    expected = round((tp / t0p) - 1.0, 6)
                    declared = w.get("return_decimal")
                    if declared is not None and abs(expected - declared) > 0.0001:
                        violations.append(f"{rid}/{wn}: return_decimal mismatch: recalc={expected} decl={declared}")

    # ── 11. signed_lag_seconds absolute value == target_snapshot.lag_seconds ──
    for r in results:
        for wn in ("return_1h", "return_4h", "return_24h"):
            w = r.get(wn) or {}
            if w.get("status") == "completed":
                sl = w.get("signed_lag_seconds")
                ts = w.get("target_snapshot") or {}
                tl = ts.get("lag_seconds")
                if sl is not None and tl is not None:
                    if abs(sl) != tl:
                        violations.append(f"{r.get('result_id','?')}/{wn}: |signed_lag|={abs(sl)} != lag_seconds={tl}")

    # ── 12. HYPE windows: nearest_candle_open + precision_seconds=900 ──
    for r in results:
        rid = r.get("result_id", "?")
        obs = r.get("observed_asset", "")
        if obs.upper() == "HYPE":
            for wn in ("return_1h", "return_4h", "return_24h"):
                w = r.get(wn) or {}
                if w.get("status") == "completed":
                    if w.get("selection_policy") != "nearest_candle_open":
                        violations.append(f"{rid}/{wn}: HYPE policy={w.get('selection_policy')} != nearest_candle_open")
                    if w.get("precision_seconds") != 900:
                        violations.append(f"{rid}/{wn}: HYPE precision={w.get('precision_seconds')} != 900")

    # ── 13. Binance windows: first_after_target + precision_seconds=60 ──
    for r in results:
        rid = r.get("result_id", "?")
        obs = r.get("observed_asset", "")
        if obs.upper() in ("BTC", "ETH"):
            for wn in ("return_1h", "return_4h", "return_24h"):
                w = r.get(wn) or {}
                if w.get("status") == "completed":
                    if w.get("selection_policy") != "first_after_target":
                        violations.append(f"{rid}/{wn}: {obs} policy={w.get('selection_policy')} != first_after_target")
                    if w.get("precision_seconds") != 60:
                        violations.append(f"{rid}/{wn}: {obs} precision={w.get('precision_seconds')} != 60")

    # ── 14. Same price_observation_key → identical payload (excluding metadata) ──
    EXCLUDE_KEYS = {"sample_id", "result_id", "observation_reused", "reused_from_result_id", "calculated_at"}
    pok_groups: dict[str, list[dict]] = {}
    for r in results:
        pok = r.get("price_observation_key", "")
        if pok:
            pok_groups.setdefault(pok, []).append(r)
    for pok, entries in pok_groups.items():
        if len(entries) < 2:
            continue
        first = entries[0]
        for e in entries[1:]:
            eid = e.get("result_id", "?")
            # Compare key fields recursively (ignore EXCLUDE_KEYS)
            diffs = _compare_results(first, e, EXCLUDE_KEYS, path="")
            for d in diffs:
                violations.append(f"{eid}: shared pok '{pok}' differs from {first.get('result_id')}: {d}")

    # ── 15. No fixture in network mode ──
    if data.get("run_mode") == "network":
        for r in results:
            rid = r.get("result_id", "?")
            t0 = r.get("t0_snapshot") or {}
            if t0.get("source") and "fixture" in t0["source"]:
                violations.append(f"{rid}: fixture source in network mode")
            for wn in ("return_1h", "return_4h", "return_24h"):
                w = r.get(wn) or {}
                ts = w.get("target_snapshot") or {}
                if ts.get("source") and "fixture" in ts["source"]:
                    violations.append(f"{rid}/{wn}: fixture source in network mode")

    passed = len(violations) == 0
    return passed, violations


def _compare_results(a: dict, b: dict, exclude: set, path: str) -> list[str]:
    """Recursively compare two result dicts, excluding certain top-level keys."""
    diffs = []
    for key in a:
        if key in exclude:
            continue
        full = f"{path}.{key}" if path else key
        if key not in b:
            diffs.append(f"{full}: missing in second")
            continue
        va, vb = a[key], b[key]
        if isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(_compare_dicts(va, vb, full))
        elif va != vb:
            diffs.append(f"{full}: {va} != {vb}")
    return diffs


def _compare_dicts(a: dict, b: dict, path: str) -> list[str]:
    diffs = []
    for k in a:
        fk = f"{path}.{k}"
        if k not in b:
            diffs.append(f"{fk}: missing in second")
            continue
        va, vb = a[k], b[k]
        if isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(_compare_dicts(va, vb, fk))
        elif va != vb:
            diffs.append(f"{fk}: {va} != {vb}")
    return diffs


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
    print(f"Unique obs: {data.get('unique_price_observations', '?')}")
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

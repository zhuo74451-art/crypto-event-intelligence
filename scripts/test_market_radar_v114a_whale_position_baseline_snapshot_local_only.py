#!/usr/bin/env python3
"""
Test suite for v114A Whale Position Baseline Snapshot — Local Only
==================================================================
Validates that the runner produced correct outputs with all safety invariants.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

V112X_STOP = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_stop_decision.json")
V113D_SEAL = os.path.join(RESULTS_DIR, "market_radar_v113d_degraded_whale_review_pack_seal_result.json")
RESULT_JSON = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
SNAPSHOT_JSON = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot.json")
POSITIONS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_positions.jsonl")
REPORT_MD = os.path.join(RUNS_DIR, "v114a_whale_position_baseline_snapshot_local_only.md")
HANDOFF_MD = os.path.join(RUNS_DIR, "v114a_whale_position_baseline_snapshot_local_only_handoff.md")

passed = 0
failed = 0
failures = []


def check(description: str, condition: bool, detail: str = ""):
    global passed, failed, failures
    if condition:
        passed += 1
        print(f"  [PASS] {description}")
    else:
        failed += 1
        msg = f"  [FAIL] {description}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        failures.append(msg)


def file_exists(path: str, label: str) -> bool:
    ok = os.path.exists(path)
    if not ok:
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1)
        return True
    except Exception:
        return False


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    global passed, failed

    print("=" * 70)
    print("v114A Test Suite — Whale Position Baseline Snapshot Local Only")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. File existence
    # ------------------------------------------------------------------
    print("\n[1] File Existence")
    check("result JSON exists", file_exists(RESULT_JSON, "result"))
    check("baseline snapshot JSON exists", file_exists(SNAPSHOT_JSON, "snapshot"))
    check("baseline positions JSONL exists", file_exists(POSITIONS_JSONL, "positions"))
    check("markdown report exists", file_exists(REPORT_MD, "report"))
    check("handoff markdown exists", file_exists(HANDOFF_MD, "handoff"))

    # ------------------------------------------------------------------
    # 2. Load data
    # ------------------------------------------------------------------
    print("\n[2] Data Loading")
    result = load_json(RESULT_JSON)
    snapshot = load_json(SNAPSHOT_JSON)
    positions = load_jsonl(POSITIONS_JSONL)
    v112x_stop = load_json(V112X_STOP)
    v113d_seal = load_json(V113D_SEAL)
    check("result JSON parsed", isinstance(result, dict))
    check("snapshot JSON parsed", isinstance(snapshot, dict))
    check("positions JSONL parsed", isinstance(positions, list))

    # ------------------------------------------------------------------
    # 3. Source validations
    # ------------------------------------------------------------------
    print("\n[3] Source Validations")
    check("v112X stop decision = DEGRADE_TO_MOCK",
          v112x_stop["stop_decision"] == "DEGRADE_TO_MOCK",
          f"got: {v112x_stop['stop_decision']}")
    check("v113D seal = sealed=true",
          v113d_seal["sealed"] is True,
          f"got: {v113d_seal['sealed']}")

    # ------------------------------------------------------------------
    # 4. Position counts
    # ------------------------------------------------------------------
    print("\n[4] Position Counts")
    check("positions loaded = 10",
          result["positions_loaded"] == 10,
          f"got: {result['positions_loaded']}")
    check("baseline records written = 10",
          result["baseline_records_written"] == 10,
          f"got: {result['baseline_records_written']}")
    check("unique addresses count = 4",
          result["unique_addresses_count"] == 4,
          f"got: {result['unique_addresses_count']}")
    check("positions JSONL record count = 10",
          len(positions) == 10,
          f"got: {len(positions)}")

    # ------------------------------------------------------------------
    # 5. Safety invariants — result level
    # ------------------------------------------------------------------
    print("\n[5] Safety Invariants — Result Level")
    check("local_baseline_only = True",
          result["local_baseline_only"] is True)
    check("external_api_called = False",
          result["external_api_called"] is False)
    check("prod_state_write = False",
          result["prod_state_write"] is False)
    check("eligible_for_real_send_count = 0",
          result["eligible_for_real_send_count"] == 0,
          f"got: {result['eligible_for_real_send_count']}")
    check("tg_send_allowed_count = 0",
          result["tg_send_allowed_count"] == 0,
          f"got: {result['tg_send_allowed_count']}")
    check("real_send_candidate_count = 0",
          result["real_send_candidate_count"] == 0,
          f"got: {result['real_send_candidate_count']}")
    check("credentials_read = False",
          result["credentials_read"] is False)
    check("daemon_started = False",
          result["daemon_started"] is False)
    check("watcher_started = False",
          result["watcher_started"] is False)
    check("files_deleted = False",
          result["files_deleted"] is False)

    # ------------------------------------------------------------------
    # 6. Safety invariants — snapshot level
    # ------------------------------------------------------------------
    print("\n[6] Safety Invariants — Snapshot Level")
    check("snapshot local_baseline_only = True",
          snapshot["local_baseline_only"] is True)
    check("snapshot prod_state_write = False",
          snapshot["prod_state_write"] is False)
    check("snapshot eligible_for_real_send_count = 0",
          snapshot["eligible_for_real_send_count"] == 0)
    check("snapshot tg_send_allowed_count = 0",
          snapshot["tg_send_allowed_count"] == 0)

    # ------------------------------------------------------------------
    # 7. Label confidence distribution
    # ------------------------------------------------------------------
    print("\n[7] Label Confidence Distribution")
    lcd = result.get("label_confidence_distribution", {})
    check("label_confidence high = 0",
          lcd.get("high", -1) == 0,
          f"got: {lcd.get('high')}")
    check("label_confidence medium = 8",
          lcd.get("medium", -1) == 8,
          f"got: {lcd.get('medium')}")
    check("label_confidence low = 2",
          lcd.get("low", -1) == 2,
          f"got: {lcd.get('low')}")

    # ------------------------------------------------------------------
    # 8. Liquidation price
    # ------------------------------------------------------------------
    print("\n[8] Liquidation Price Availability")
    check("liquidation_price null count = 7",
          result.get("liquidation_price_null_count", -1) == 7,
          f"got: {result.get('liquidation_price_null_count')}")

    # ------------------------------------------------------------------
    # 9. Per-record safety invariants
    # ------------------------------------------------------------------
    print("\n[9] Per-Record Safety Invariants")
    for i, record in enumerate(positions):
        prefix = f"record[{i}] ({record.get('asset','?')} {record.get('side','?')})"
        check(f"{prefix} local_baseline_only = True",
              record.get("local_baseline_only") is True)
        check(f"{prefix} prod_state_write = False",
              record.get("prod_state_write") is False)
        check(f"{prefix} eligible_for_real_send = False",
              record.get("eligible_for_real_send") is False)
        check(f"{prefix} tg_send_allowed = False",
              record.get("tg_send_allowed") is False)
        check(f"{prefix} has position_identity_key",
              bool(record.get("position_identity_key")),
              f"got: {record.get('position_identity_key')}")
        check(f"{prefix} has baseline_hash",
              bool(record.get("baseline_hash")),
              f"got: {record.get('baseline_hash')}")
        check(f"{prefix} future_delta_ready = True",
              record.get("future_delta_ready") is True)

    # ------------------------------------------------------------------
    # 10. Cross-version checks
    # ------------------------------------------------------------------
    print("\n[10] Cross-Version Integrity")
    check("result version = v114A",
          result["version"] == "v114A")
    check("snapshot version = v114A",
          snapshot["version"] == "v114A")
    check("result next_step correct",
          result["next_step"] == "v114b_whale_second_probe_delta_compare_readonly")
    check("snapshot next_step correct",
          snapshot["next_step"] == "v114b_whale_second_probe_delta_compare_readonly")
    check("snapshot source_live_probe = v112X",
          snapshot["source_live_probe"] == "v112X")
    check("snapshot sealed_source_stage = v113D",
          snapshot["sealed_source_stage"] == "v113D")

    # ------------------------------------------------------------------
    # 11. No production state or send readiness
    # ------------------------------------------------------------------
    print("\n[11] Production/Send Readiness Prohibitions")
    check("result status = passed",
          result["status"] == "passed")
    check("result baseline_snapshot_created = True",
          result["baseline_snapshot_created"] is True)

    # Verify no record is marked as production or send-ready
    for i, record in enumerate(positions):
        prefix = f"record[{i}]"
        is_prod = record.get("is_production_state") or record.get("production") or record.get("prod")
        is_send = record.get("send_ready") or record.get("tg_send_ready") or record.get("ready_to_send")
        check(f"{prefix} not marked production state",
              not is_prod,
              f"unexpected production marker found")
        check(f"{prefix} not marked send ready",
              not is_send,
              f"unexpected send marker found")

    # ------------------------------------------------------------------
    # 12. Unique addresses verification
    # ------------------------------------------------------------------
    print("\n[12] Unique Addresses Verification")
    addresses = set(r["address"] for r in positions)
    check("unique addresses from records = 4",
          len(addresses) == 4,
          f"got {len(addresses)}: {addresses}")
    expected_addresses = {
        "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "0x082e843a431aef031264dc232693dd710aedca88",
        "0x50b309f78e774a756a2230e1769729094cac9f20",
    }
    check("addresses match expected set",
          addresses == expected_addresses,
          f"diff: {addresses ^ expected_addresses}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)
    if failed:
        print("\nFAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    else:
        print("\nAll tests passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

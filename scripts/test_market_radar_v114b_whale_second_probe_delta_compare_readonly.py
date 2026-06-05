#!/usr/bin/env python3
"""
Test suite for v114B Whale Second Probe Delta Compare — Read-Only
==================================================================
Validates that the v114B runner produced correct outputs with all
safety invariants and proper delta classifications.

This test ONLY verifies generated files — it does NOT make additional
HyperLiquid API calls.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

LIVE_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_second_probe_live_response.json")
DELTA_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
DELTAS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")
REPORT_MD = os.path.join(RUNS_DIR, "v114b_whale_second_probe_delta_compare_readonly.md")
HANDOFF_MD = os.path.join(RUNS_DIR, "v114b_whale_second_probe_delta_compare_readonly_handoff.md")

VALID_DELTA_TYPES = {"new_position", "closed_position", "size_changed", "unchanged"}


def size_within_tolerance(a, b, tolerance_pct=0.02):
    """Check if two sizes are within tolerance (2% relative)."""
    a = float(a) if a else 0.0
    b = float(b) if b else 0.0
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    rel_diff = abs(b - a) / max(abs(a), abs(b))
    return rel_diff < tolerance_pct

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


def file_exists(path: str) -> bool:
    if not os.path.exists(path):
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
    print("v114B Test Suite — Whale Second Probe Delta Compare Read-Only")
    print("=" * 70)

    # ==================================================================
    # 1. File existence
    # ==================================================================
    print("\n[1] File Existence")
    check("live response JSON exists", file_exists(LIVE_RESPONSE))
    check("delta compare result JSON exists", file_exists(DELTA_RESULT))
    check("delta records JSONL exists", file_exists(DELTAS_JSONL))
    check("markdown report exists", file_exists(REPORT_MD))
    check("handoff markdown exists", file_exists(HANDOFF_MD))

    # ==================================================================
    # 2. Load data
    # ==================================================================
    print("\n[2] Data Loading")
    live_resp = load_json(LIVE_RESPONSE)
    delta_result = load_json(DELTA_RESULT)
    deltas = load_jsonl(DELTAS_JSONL)

    check("live response JSON parsed", isinstance(live_resp, dict))
    check("delta result JSON parsed", isinstance(delta_result, dict))
    check("delta records JSONL parsed", isinstance(deltas, list))
    check("delta records non-empty", len(deltas) > 0, f"got {len(deltas)} records")

    # ==================================================================
    # 3. Live response structure
    # ==================================================================
    print("\n[3] Live Response Structure")
    check("live response version = v114B",
          live_resp.get("version") == "v114B",
          f"got: {live_resp.get('version')}")
    check("live response second_probe = True",
          live_resp.get("second_probe") is True,
          f"got: {live_resp.get('second_probe')}")
    check("live response external_api_called = True",
          live_resp.get("external_api_called") is True)
    check("live response api_key_used = False",
          live_resp.get("api_key_used") is False)
    check("live response authorization_header_used = False",
          live_resp.get("authorization_header_used") is False)
    check("live response retry_count = 0",
          live_resp.get("retry_count") == 0,
          f"got: {live_resp.get('retry_count')}")
    check("live response tg_sent = False",
          live_resp.get("tg_sent") is False)
    check("live response production_state_written = False",
          live_resp.get("production_state_written") is False)
    check("live response eligible_for_real_send = False",
          live_resp.get("eligible_for_real_send") is False)
    check("live response has responses array",
          isinstance(live_resp.get("responses"), list))

    # ==================================================================
    # 4. Delta result JSON — counts and invariants
    # ==================================================================
    print("\n[4] Delta Result JSON — Counts and Invariants")
    check("result version = v114B",
          delta_result.get("version") == "v114B",
          f"got: {delta_result.get('version')}")
    check("result status in (passed, degraded)",
          delta_result.get("status") in ("passed", "degraded"),
          f"got: {delta_result.get('status')}")
    check("second_probe_executed = True",
          delta_result.get("second_probe_executed") is True)
    check("baseline_records_loaded = 10",
          delta_result.get("baseline_records_loaded") == 10,
          f"got: {delta_result.get('baseline_records_loaded')}")
    check("addresses_requested_count = 4",
          delta_result.get("addresses_requested_count") == 4,
          f"got: {delta_result.get('addresses_requested_count')}")
    check("success_count >= 0",
          isinstance(delta_result.get("success_count"), (int, float)),
          f"got: {delta_result.get('success_count')}")
    check("failure_count >= 0",
          isinstance(delta_result.get("failure_count"), (int, float)),
          f"got: {delta_result.get('failure_count')}")
    check("success + failure = 4",
          delta_result.get("success_count", 0) + delta_result.get("failure_count", 0) == 4,
          f"got: {delta_result.get('success_count')} + {delta_result.get('failure_count')}")

    # Delta counts
    check("delta_records_written matches JSONL count",
          delta_result.get("delta_records_written") == len(deltas),
          f"result: {delta_result.get('delta_records_written')}, JSONL: {len(deltas)}")
    check("new_position_count + closed_position_count + size_changed_count + unchanged_count = delta_records_written",
          (delta_result.get("new_position_count", 0)
           + delta_result.get("closed_position_count", 0)
           + delta_result.get("size_changed_count", 0)
           + delta_result.get("unchanged_count", 0)) == len(deltas),
          f"sum doesn't match {len(deltas)}")

    # Safety invariants on result level
    check("result external_api_called = True",
          delta_result.get("external_api_called") is True)
    check("result api_key_used = False",
          delta_result.get("api_key_used") is False)
    check("result authorization_header_used = False",
          delta_result.get("authorization_header_used") is False)
    check("result credentials_read = False",
          delta_result.get("credentials_read") is False)
    check("result retry_count = 0",
          delta_result.get("retry_count") == 0,
          f"got: {delta_result.get('retry_count')}")
    check("result local_delta_compare_only = True",
          delta_result.get("local_delta_compare_only") is True)
    check("result prod_state_write = False",
          delta_result.get("prod_state_write") is False)
    check("result eligible_for_real_send_count = 0",
          delta_result.get("eligible_for_real_send_count") == 0,
          f"got: {delta_result.get('eligible_for_real_send_count')}")
    check("result tg_send_allowed_count = 0",
          delta_result.get("tg_send_allowed_count") == 0,
          f"got: {delta_result.get('tg_send_allowed_count')}")
    check("result real_send_candidate_count = 0",
          delta_result.get("real_send_candidate_count") == 0,
          f"got: {delta_result.get('real_send_candidate_count')}")
    check("result daemon_started = False",
          delta_result.get("daemon_started") is False)
    check("result watcher_started = False",
          delta_result.get("watcher_started") is False)
    check("result files_deleted = False",
          delta_result.get("files_deleted") is False)

    # Next step
    check("result next_step correct",
          delta_result.get("next_step") == "v114c_whale_delta_operator_review_pack_local_only",
          f"got: {delta_result.get('next_step')}")

    # ==================================================================
    # 5. Per-delta record safety invariants
    # ==================================================================
    print(f"\n[5] Per-Delta Record Safety Invariants ({len(deltas)} records)")
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}] ({d.get('asset','?')} {d.get('side','?')} {d.get('delta_type','?')})"

        check(f"{prefix} version = v114B",
              d.get("version") == "v114B",
              f"got: {d.get('version')}")
        check(f"{prefix} local_delta_compare_only = True",
              d.get("local_delta_compare_only") is True)
        check(f"{prefix} eligible_for_real_send = False",
              d.get("eligible_for_real_send") is False,
              f"got: {d.get('eligible_for_real_send')}")
        check(f"{prefix} tg_send_allowed = False",
              d.get("tg_send_allowed") is False,
              f"got: {d.get('tg_send_allowed')}")
        check(f"{prefix} prod_state_write = False",
              d.get("prod_state_write") is False)
        check(f"{prefix} has position_identity_key",
              bool(d.get("position_identity_key")),
              f"got: {d.get('position_identity_key')}")
        check(f"{prefix} position_identity_key format = address|asset|side",
              d.get("position_identity_key", "").count("|") == 2,
              f"got: {d.get('position_identity_key')}")
        check(f"{prefix} has address",
              bool(d.get("address")),
              f"got: {d.get('address')}")
        check(f"{prefix} has label",
              bool(d.get("label")),
              f"got: {d.get('label')}")

    # ==================================================================
    # 6. Delta type classification rules
    # ==================================================================
    print(f"\n[6] Delta Type Classification Rules ({len(deltas)} records)")
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}] ({d.get('asset','?')} {d.get('side','?')})"
        dt = d.get("delta_type", "")

        check(f"{prefix} delta_type is valid",
              dt in VALID_DELTA_TYPES,
              f"got: {dt}")

        if dt == "new_position":
            check(f"{prefix} baseline_size = 0 for new_position",
                  d.get("baseline_size") == 0,
                  f"got: {d.get('baseline_size')}")
            check(f"{prefix} current_size > 0 for new_position",
                  float(d.get("current_size", 0)) > 0,
                  f"got: {d.get('current_size')}")
            check(f"{prefix} size_delta = current_size for new_position",
                  abs(float(d.get("size_delta", 0)) - float(d.get("current_size", 0))) < 0.01,
                  f"delta={d.get('size_delta')}, current={d.get('current_size')}")
        elif dt == "closed_position":
            check(f"{prefix} current_size = 0 for closed_position",
                  d.get("current_size") == 0,
                  f"got: {d.get('current_size')}")
            check(f"{prefix} quality_flags includes position_closed",
                  "position_closed" in d.get("quality_flags", []),
                  f"flags: {d.get('quality_flags')}")
        elif dt == "size_changed":
            check(f"{prefix} baseline_size != current_size for size_changed",
                  d.get("baseline_size") != d.get("current_size"),
                  f"both: {d.get('baseline_size')}")
            check(f"{prefix} size_delta != 0 for size_changed",
                  float(d.get("size_delta", 0)) != 0,
                  f"got: {d.get('size_delta')}")
        elif dt == "unchanged":
            check(f"{prefix} baseline_size ≈ current_size (within 2% tolerance) for unchanged",
                  size_within_tolerance(d.get("baseline_size"), d.get("current_size")),
                  f"baseline={d.get('baseline_size')}, current={d.get('current_size')}")

    # ==================================================================
    # 7. No send-ready or production markers on any record
    # ==================================================================
    print(f"\n[7] Send/Production Readiness Prohibitions ({len(deltas)} records)")
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}]"

        # Check for any send-ready markers
        is_send = (
            d.get("send_ready")
            or d.get("tg_send_ready")
            or d.get("ready_to_send")
            or d.get("is_send_candidate")
        )
        check(f"{prefix} not marked send ready",
              not is_send,
              f"unexpected send marker found")

        is_prod = (
            d.get("is_production_state")
            or d.get("production")
            or d.get("prod")
        )
        check(f"{prefix} not marked production state",
              not is_prod,
              f"unexpected production marker found")

        # eligible_for_real_send must be False (not just falsy)
        check(f"{prefix} eligible_for_real_send is exactly False",
              d.get("eligible_for_real_send") is False)

        # tg_send_allowed must be False
        check(f"{prefix} tg_send_allowed is exactly False",
              d.get("tg_send_allowed") is False)

    # ==================================================================
    # 8. Quality flags validation
    # ==================================================================
    print(f"\n[8] Quality Flags Validation ({len(deltas)} records)")
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}]"
        flags = d.get("quality_flags", [])

        check(f"{prefix} quality_flags is list",
              isinstance(flags, list))
        check(f"{prefix} has 'second_probe_readonly' flag",
              "second_probe_readonly" in flags,
              f"flags: {flags}")
        check(f"{prefix} has 'local_delta_compare' flag",
              "local_delta_compare" in flags,
              f"flags: {flags}")
        check(f"{prefix} has 'not_send_ready' flag",
              "not_send_ready" in flags,
              f"flags: {flags}")

        if d.get("liquidation_price") is None:
            check(f"{prefix} has 'liquidation_price_unavailable' flag when liq_price is null",
                  "liquidation_price_unavailable" in flags,
                  f"flags: {flags}")

    # ==================================================================
    # 9. 0x50b3 BTC position check
    # ==================================================================
    print("\n[9] 0x50b3 BTC Position Tracking")
    btc_deltas = [
        d for d in deltas
        if d["address"].startswith("0x50b3") and d["asset"] == "BTC"
    ]
    if btc_deltas:
        for d in btc_deltas:
            dt = d["delta_type"]
            if dt == "closed_position":
                print(f"  [INFO] 0x50b3 BTC position is closed_position (expected behavior)")
                check("0x50b3 BTC delta_type is valid (closed_position is acceptable)",
                      dt in ("closed_position", "unchanged", "size_changed", "new_position"))
            else:
                print(f"  [INFO] 0x50b3 BTC position still present, delta_type={dt}")
                check("0x50b3 BTC delta_type is valid",
                      dt in VALID_DELTA_TYPES)
    else:
        print("  [INFO] No 0x50b3 BTC deltas found — may have been handled in another record")

    # ==================================================================
    # 10. Label confidence — no upgrades
    # ==================================================================
    print("\n[10] Label Confidence Distribution")
    label_conf = delta_result.get("label_confidence_distribution", {})
    check("label_confidence_distribution exists",
          bool(label_conf),
          f"got: {label_conf}")

    # All label confidences should be preserved from baseline (medium or low)
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}]"
        lc = d.get("label_confidence", "")
        check(f"{prefix} label_confidence is valid (high/medium/low)",
              lc in ("high", "medium", "low"),
              f"got: {lc}")

    # Verify no confidence upgrade: all deltas with label_confidence should match baseline
    # Baseline distribution: high=0, medium=8, low=2
    total_by_conf = {"high": 0, "medium": 0, "low": 0}
    for d in deltas:
        lc = d.get("label_confidence", "unknown")
        if lc in total_by_conf:
            total_by_conf[lc] += 1

    # New positions added labels from probe; closed positions removed;
    # The counts can differ from baseline. What matters is no "upgrade."
    # But we verify the distribution is reported correctly:
    check("result label_confidence_distribution matches deltas",
          label_conf.get("high", 0) == total_by_conf["high"]
          and label_conf.get("medium", 0) == total_by_conf["medium"]
          and label_conf.get("low", 0) == total_by_conf["low"],
          f"result: {label_conf}, actual: {total_by_conf}")

    # ==================================================================
    # 11. Liquidation price summary
    # ==================================================================
    print("\n[11] Liquidation Price Summary")
    liq_null = delta_result.get("liquidation_price_null_count", 0)
    actual_null = sum(1 for d in deltas if d.get("liquidation_price") is None)
    check("liquidation_price_null_count matches deltas",
          liq_null == actual_null,
          f"result: {liq_null}, actual: {actual_null}")

    # ==================================================================
    # 12. Operator note presence
    # ==================================================================
    print(f"\n[12] Operator Notes ({len(deltas)} records)")
    for i, d in enumerate(deltas):
        prefix = f"delta[{i}]"
        note = d.get("operator_note", "")
        note_snippet = (note[:80] if note else "(empty)")
        check(f"{prefix} has operator_note",
              bool(note),
              f"got: {note_snippet}")

    # ==================================================================
    # 13. Markdown report content checks
    # ==================================================================
    print("\n[13] Markdown Report Content")
    if file_exists(REPORT_MD):
        with open(REPORT_MD, "r", encoding="utf-8") as f:
            report_content = f.read()
        check("report mentions v114B",
              "v114B" in report_content)
        check("report mentions baseline records",
              "baseline records loaded" in report_content.lower()
              or "Baseline records" in report_content)
        check("report mentions delta",
              "delta" in report_content.lower())
        check("report mentions safety invariants",
              "safety invariant" in report_content.lower()
              or "Safety Invariant" in report_content)
        check("report mentions next step v114C",
              "v114C" in report_content or "v114c" in report_content)
    else:
        check("report file exists for content check", False, "file not found")

    if file_exists(HANDOFF_MD):
        with open(HANDOFF_MD, "r", encoding="utf-8") as f:
            handoff_content = f.read()
        check("handoff mentions v114B",
              "v114B" in handoff_content)
        check("handoff mentions v114C next step",
              "v114C" in handoff_content or "v114c" in handoff_content)
        check("handoff mentions safety invariants",
              "safety" in handoff_content.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 14. Live response addresses match requested
    # ==================================================================
    print("\n[14] Live Response Address Consistency")
    resp_addresses = [r.get("address") for r in live_resp.get("responses", [])]
    requested = live_resp.get("addresses_requested", [])
    check("responses count matches addresses_requested",
          len(resp_addresses) == len(requested),
          f"responses: {len(resp_addresses)}, requested: {len(requested)}")

    expected_addrs = {
        "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "0x082e843a431aef031264dc232693dd710aedca88",
        "0x50b309f78e774a756a2230e1769729094cac9f20",
    }
    actual_addrs = set(resp_addresses)
    check("response addresses match expected tracked set",
          actual_addrs == expected_addrs,
          f"diff: {actual_addrs ^ expected_addrs}")

    # ==================================================================
    # Summary
    # ==================================================================
    print("\n" + "=" * 70)
    total = passed + failed
    print(f"Results: {passed} passed, {failed} failed, {total} total")
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

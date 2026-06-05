#!/usr/bin/env python3
"""
Test suite for v114C Whale Delta Operator Review Pack — Local Only
==================================================================
Validates that the v114C runner produced correct outputs with all
safety invariants, correct delta classifications, and proper
operator review card structures.

This test ONLY verifies generated files — it does NOT make any
external API calls.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

V114C_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_pack_result.json")
V114C_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")
V114C_REPORT = os.path.join(RUNS_DIR, "v114c_whale_delta_operator_review_pack_local_only.md")
V114C_HANDOFF = os.path.join(RUNS_DIR, "v114c_whale_delta_operator_review_pack_local_only_handoff.md")

VALID_DELTA_TYPES = {"new_position", "closed_position", "size_changed", "unchanged"}
VALID_ATTENTION_LEVELS = {"high", "medium", "low"}

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
    print("v114C Test Suite — Whale Delta Operator Review Pack Local Only")
    print("=" * 70)

    # ==================================================================
    # 1. File existence
    # ==================================================================
    print("\n[1] File Existence")
    check("result JSON exists", file_exists(V114C_RESULT))
    check("review cards JSONL exists", file_exists(V114C_CARDS))
    check("markdown report exists", file_exists(V114C_REPORT))
    check("handoff markdown exists", file_exists(V114C_HANDOFF))

    # ==================================================================
    # 2. Load data
    # ==================================================================
    print("\n[2] Data Loading")
    result = load_json(V114C_RESULT)
    cards = load_jsonl(V114C_CARDS)

    check("result JSON parsed", isinstance(result, dict))
    check("review cards JSONL parsed", isinstance(cards, list))
    check("review cards non-empty", len(cards) > 0, f"got {len(cards)} records")

    # ==================================================================
    # 3. Result JSON — counts
    # ==================================================================
    print("\n[3] Result JSON — Counts")
    check("version = v114C",
          result.get("version") == "v114C",
          f"got: {result.get('version')}")
    check("status = passed",
          result.get("status") == "passed",
          f"got: {result.get('status')}")
    check("input_delta_records_loaded = 10",
          result.get("input_delta_records_loaded") == 10,
          f"got: {result.get('input_delta_records_loaded')}")
    check("operator_review_cards_written = 10",
          result.get("operator_review_cards_written") == 10,
          f"got: {result.get('operator_review_cards_written')}")
    check("review cards JSONL count matches result",
          len(cards) == result.get("operator_review_cards_written"),
          f"result: {result.get('operator_review_cards_written')}, JSONL: {len(cards)}")

    # Delta type counts
    check("closed_position_count = 1",
          result.get("closed_position_count") == 1,
          f"got: {result.get('closed_position_count')}")
    check("size_changed_count = 5",
          result.get("size_changed_count") == 5,
          f"got: {result.get('size_changed_count')}")
    check("unchanged_count = 4",
          result.get("unchanged_count") == 4,
          f"got: {result.get('unchanged_count')}")
    check("new_position_count = 0",
          result.get("new_position_count") == 0,
          f"got: {result.get('new_position_count')}")

    # Verify delta type counts from cards
    actual_closed = sum(1 for c in cards if c.get("delta_type") == "closed_position")
    actual_changed = sum(1 for c in cards if c.get("delta_type") == "size_changed")
    actual_unchanged = sum(1 for c in cards if c.get("delta_type") == "unchanged")
    actual_new = sum(1 for c in cards if c.get("delta_type") == "new_position")
    check("actual closed_position count = 1",
          actual_closed == 1, f"got: {actual_closed}")
    check("actual size_changed count = 5",
          actual_changed == 5, f"got: {actual_changed}")
    check("actual unchanged count = 4",
          actual_unchanged == 4, f"got: {actual_unchanged}")
    check("actual new_position count = 0",
          actual_new == 0, f"got: {actual_new}")
    check("delta type sum = total cards",
          actual_closed + actual_changed + actual_unchanged + actual_new == len(cards))

    # Attention counts
    check("high_attention_count >= 1",
          result.get("high_attention_count", 0) >= 1,
          f"got: {result.get('high_attention_count')}")
    check("medium_attention_count = 5",
          result.get("medium_attention_count") == 5,
          f"got: {result.get('medium_attention_count')}")
    check("low_attention_count = 4",
          result.get("low_attention_count") == 4,
          f"got: {result.get('low_attention_count')}")

    actual_high = sum(1 for c in cards if c.get("operator_attention_level") == "high")
    actual_medium = sum(1 for c in cards if c.get("operator_attention_level") == "medium")
    actual_low = sum(1 for c in cards if c.get("operator_attention_level") == "low")
    check("actual high_attention matches result",
          actual_high == result.get("high_attention_count"),
          f"result: {result.get('high_attention_count')}, actual: {actual_high}")
    check("actual medium_attention matches result",
          actual_medium == result.get("medium_attention_count"),
          f"result: {result.get('medium_attention_count')}, actual: {actual_medium}")
    check("actual low_attention matches result",
          actual_low == result.get("low_attention_count"),
          f"result: {result.get('low_attention_count')}, actual: {actual_low}")

    # ==================================================================
    # 4. Result JSON — safety invariants
    # ==================================================================
    print("\n[4] Result JSON — Safety Invariants")
    check("result external_api_called = False",
          result.get("external_api_called") is False)
    check("result local_review_only = True",
          result.get("local_review_only") is True)
    check("result eligible_for_real_send_count = 0",
          result.get("eligible_for_real_send_count") == 0,
          f"got: {result.get('eligible_for_real_send_count')}")
    check("result real_send_candidate_count = 0",
          result.get("real_send_candidate_count") == 0,
          f"got: {result.get('real_send_candidate_count')}")
    check("result tg_send_allowed_count = 0",
          result.get("tg_send_allowed_count") == 0,
          f"got: {result.get('tg_send_allowed_count')}")
    check("result prod_state_write = False",
          result.get("prod_state_write") is False)
    check("result credentials_read = False",
          result.get("credentials_read") is False)
    check("result daemon_started = False",
          result.get("daemon_started") is False)
    check("result watcher_started = False",
          result.get("watcher_started") is False)
    check("result files_deleted = False",
          result.get("files_deleted") is False)
    check("result known_data_consistency_note exists",
          bool(result.get("known_data_consistency_note")),
          f"got: {result.get('known_data_consistency_note', '')[:80]}")
    check("result known_data_consistency_note mentions v113D",
          "v113D" in result.get("known_data_consistency_note", ""))
    check("result next_step correct",
          result.get("next_step") == "v114d_whale_delta_review_pack_seal_local_only",
          f"got: {result.get('next_step')}")

    # ==================================================================
    # 5. BTC short closed_position
    # ==================================================================
    print("\n[5] BTC Short Closed Position")
    btc_closed = [
        c for c in cards
        if c.get("delta_type") == "closed_position"
        and c.get("asset") == "BTC"
        and c.get("side") == "short"
    ]
    check("BTC short closed_position exists in cards",
          len(btc_closed) >= 1,
          f"found {len(btc_closed)} matching cards")

    if btc_closed:
        c = btc_closed[0]
        check("BTC closed_position address = 0x50b3...",
              c.get("address", "").startswith("0x50b3"),
              f"got: {c.get('address')}")
        check("BTC closed_position operator_attention_level = high",
              c.get("operator_attention_level") == "high",
              f"got: {c.get('operator_attention_level')}")
        check("BTC closed_position label_confidence = low",
              c.get("label_confidence") == "low",
              f"got: {c.get('label_confidence')}")
        check("BTC closed_position label is NOT a confident institution",
              c.get("label_confidence") != "high",
              "low-confidence label correctly NOT presented as institution")
        check("BTC closed_position has review_summary",
              bool(c.get("review_summary")),
              f"got: {c.get('review_summary', '')[:80]}")
        check("BTC closed_position review_summary mentions closed_position",
              "closed_position" in c.get("review_summary", ""))
        check("BTC closed_position NOT written as error",
              "error" not in c.get("review_summary", "").lower())
        check("BTC closed_position has source_delta_hash",
              bool(c.get("source_delta_hash")),
              f"got: {c.get('source_delta_hash', '')[:20]}")
        check("BTC closed_position baseline_size > 0",
              float(c.get("baseline_size", 0)) > 0,
              f"got: {c.get('baseline_size')}")
        check("BTC closed_position current_size = 0",
              c.get("current_size") == 0,
              f"got: {c.get('current_size')}")

    # ==================================================================
    # 6. Per-card safety invariants
    # ==================================================================
    print(f"\n[6] Per-Card Safety Invariants ({len(cards)} cards)")
    for i, c in enumerate(cards):
        prefix = f"card[{i}] ({c.get('asset','?')} {c.get('side','?')} {c.get('delta_type','?')})"

        check(f"{prefix} version = v114C",
              c.get("version") == "v114C",
              f"got: {c.get('version')}")
        check(f"{prefix} local_review_only = True",
              c.get("local_review_only") is True)
        check(f"{prefix} operator_action = review_only_no_send",
              c.get("operator_action") == "review_only_no_send",
              f"got: {c.get('operator_action')}")
        check(f"{prefix} eligible_for_real_send = False",
              c.get("eligible_for_real_send") is False,
              f"got: {c.get('eligible_for_real_send')}")
        check(f"{prefix} real_send_candidate = False",
              c.get("real_send_candidate") is False,
              f"got: {c.get('real_send_candidate')}")
        check(f"{prefix} tg_send_allowed = False",
              c.get("tg_send_allowed") is False,
              f"got: {c.get('tg_send_allowed')}")
        check(f"{prefix} prod_state_write = False",
              c.get("prod_state_write") is False,
              f"got: {c.get('prod_state_write')}")
        check(f"{prefix} has review_summary",
              bool(c.get("review_summary")),
              f"got: '{c.get('review_summary', '')[:60]}'")
        check(f"{prefix} has label_confidence",
              bool(c.get("label_confidence")),
              f"got: {c.get('label_confidence')}")
        check(f"{prefix} has position_identity_key",
              bool(c.get("position_identity_key")),
              f"got: {c.get('position_identity_key')}")
        check(f"{prefix} has source_delta_hash",
              bool(c.get("source_delta_hash")),
              f"got: {c.get('source_delta_hash', '')[:20]}")
        check(f"{prefix} has warnings list",
              isinstance(c.get("warnings"), list),
              f"got: {type(c.get('warnings'))}")

    # ==================================================================
    # 7. Attention level per delta type
    # ==================================================================
    print(f"\n[7] Attention Level Classification ({len(cards)} cards)")
    for i, c in enumerate(cards):
        prefix = f"card[{i}] ({c.get('asset','?')} {c.get('delta_type','?')})"
        dt = c.get("delta_type", "")
        al = c.get("operator_attention_level", "")

        check(f"{prefix} operator_attention_level is valid",
              al in VALID_ATTENTION_LEVELS,
              f"got: {al}")

        if dt == "closed_position":
            check(f"{prefix} closed_position must be high attention",
                  al == "high",
                  f"got: {al}")
        elif dt == "new_position":
            check(f"{prefix} new_position must be high attention",
                  al == "high",
                  f"got: {al}")
        elif dt == "unchanged":
            check(f"{prefix} unchanged must be low attention",
                  al == "low",
                  f"got: {al}")

    # ==================================================================
    # 8. Low-confidence cards must not masquerade as confident
    # ==================================================================
    print(f"\n[8] Low-Confidence Card Integrity ({len(cards)} cards)")
    for i, c in enumerate(cards):
        prefix = f"card[{i}]"
        lc = c.get("label_confidence", "")
        if lc == "low":
            # Low-confidence card must NOT present itself as a confident institution
            summary = c.get("review_summary", "").lower()
            label = c.get("label", "").lower()
            check(f"{prefix} low-confidence card label not falsely confident",
                  "confirmed" not in label and "verified" not in label)

    # ==================================================================
    # 9. Closed positions must not be written as errors
    # ==================================================================
    print(f"\n[9] Closed Position Integrity ({actual_closed} closed cards)")
    for i, c in enumerate(cards):
        if c.get("delta_type") == "closed_position":
            prefix = f"card[{i}] ({c.get('asset','?')})"
            summary = c.get("review_summary", "")
            check(f"{prefix} closed_position not written as error",
                  "error" not in summary.lower(),
                  f"summary: {summary[:80]}")
            check(f"{prefix} closed_position not written as fault",
                  "fault" not in summary.lower(),
                  f"summary: {summary[:80]}")

    # ==================================================================
    # 10. Unchanged must not be written as strong signal
    # ==================================================================
    print(f"\n[10] Unchanged Integrity ({actual_unchanged} unchanged cards)")
    for i, c in enumerate(cards):
        if c.get("delta_type") == "unchanged":
            prefix = f"card[{i}] ({c.get('asset','?')})"
            summary = c.get("review_summary", "")
            check(f"{prefix} unchanged not written as strong signal",
                  "strong" not in summary.lower()
                  and "significant" not in summary.lower()
                  and "important" not in summary.lower(),
                  f"summary: {summary[:80]}")
            check(f"{prefix} unchanged mentions low-priority or tolerance",
                  "low-priority" in summary.lower() or "tolerance" in summary.lower(),
                  f"summary: {summary[:80]}")

    # ==================================================================
    # 11. Review summary content rules
    # ==================================================================
    print(f"\n[11] Review Summary Rules ({len(cards)} cards)")
    for i, c in enumerate(cards):
        prefix = f"card[{i}] ({c.get('asset','?')} {c.get('delta_type','?')})"
        summary = c.get("review_summary", "")

        if c.get("delta_type") == "closed_position":
            check(f"{prefix} closed summary mentions 'disappeared' or 'closed'",
                  "disappeared" in summary.lower() or "closed" in summary.lower())
        elif c.get("delta_type") == "size_changed":
            check(f"{prefix} size_changed summary mentions 'delta' or 'size'",
                  "delta" in summary.lower() or "size" in summary.lower())
        elif c.get("delta_type") == "unchanged":
            check(f"{prefix} unchanged summary mentions 'low' or 'tolerance'",
                  "low" in summary.lower() or "tolerance" in summary.lower())
        elif c.get("delta_type") == "new_position":
            check(f"{prefix} new_position summary mentions 'new' or 'appeared'",
                  "new" in summary.lower() or "appeared" in summary.lower())

    # ==================================================================
    # 12. Sorting order verification
    # ==================================================================
    print("\n[12] Card Sorting Order")
    priority_order = {"closed_position": 0, "size_changed": 1, "new_position": 2, "unchanged": 3}
    for i in range(len(cards) - 1):
        p_i = priority_order.get(cards[i]["delta_type"], 99)
        p_next = priority_order.get(cards[i + 1]["delta_type"], 99)
        check(f"card[{i}] -> card[{i+1}] priority order correct",
              p_i <= p_next,
              f"{cards[i]['delta_type']} (p={p_i}) should come before {cards[i+1]['delta_type']} (p={p_next})")

    # Within same delta_type, size_delta_abs should be descending
    for dt in ["size_changed", "unchanged"]:
        same_type = [c for c in cards if c["delta_type"] == dt]
        for i in range(len(same_type) - 1):
            check(f"{dt}[{i}] -> {dt}[{i+1}] size_delta_abs descending",
                  same_type[i].get("size_delta_abs", 0) >= same_type[i + 1].get("size_delta_abs", 0),
                  f"{same_type[i].get('size_delta_abs')} >= {same_type[i+1].get('size_delta_abs')}")

    # ==================================================================
    # 13. Markdown report content checks
    # ==================================================================
    print("\n[13] Markdown Report Content")
    if file_exists(V114C_REPORT):
        with open(V114C_REPORT, "r", encoding="utf-8") as f:
            report_content = f.read()

        check("report mentions v114C",
              "v114C" in report_content)
        check("report mentions v114B delta",
              "v114b" in report_content.lower() and "delta" in report_content.lower())
        check("report mentions not_tg_send_ready",
              "not_tg_send_ready" in report_content)
        check("report mentions known data consistency note",
              "v113D" in report_content and "consistency" in report_content.lower())
        check("report mentions BTC closed_position",
              "closed_position" in report_content and "BTC" in report_content)
        check("report mentions local_operator_review_only",
              "local_operator_review_only" in report_content)
        check("report mentions not_prod_state_ready",
              "not_prod_state_ready" in report_content)
        check("report mentions not_real_send_candidate",
              "not_real_send_candidate" in report_content)
        check("report mentions v114D next step",
              "v114D" in report_content or "v114d" in report_content)

        # Must NOT contain send-ready language
        check("report does NOT say 'send ready'",
              "send ready" not in report_content.lower())
        check("report does NOT say 'ready to send'",
              "ready to send" not in report_content.lower())
        check("report does NOT say 'TG send ready'",
              "TG send ready" not in report_content.lower())
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 14. Handoff content checks
    # ==================================================================
    print("\n[14] Handoff Markdown Content")
    if file_exists(V114C_HANDOFF):
        with open(V114C_HANDOFF, "r", encoding="utf-8") as f:
            handoff_content = f.read()

        check("handoff mentions v114C",
              "v114C" in handoff_content)
        check("handoff mentions v114D next step",
              "v114D" in handoff_content or "v114d" in handoff_content)
        check("handoff mentions safety invariants",
              "safety" in handoff_content.lower() or "invariant" in handoff_content.lower())
        check("handoff mentions BTC closed_position",
              "closed_position" in handoff_content and "BTC" in handoff_content)
        check("handoff mentions known data consistency note",
              "v113D" in handoff_content)
        check("handoff mentions not TG send",
              "not_tg_send" in handoff_content.lower()
              or "not TG" in handoff_content
              or "TG-eligible" in handoff_content)
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 15. Label confidence summary
    # ==================================================================
    print("\n[15] Label Confidence Distribution")
    lc_counts = {"high": 0, "medium": 0, "low": 0}
    for c in cards:
        lc = c.get("label_confidence", "")
        if lc in lc_counts:
            lc_counts[lc] += 1

    check("label_confidence high = 0",
          lc_counts["high"] == 0,
          f"got: {lc_counts['high']}")
    check("label_confidence medium = 8",
          lc_counts["medium"] == 8,
          f"got: {lc_counts['medium']}")
    check("label_confidence low = 2",
          lc_counts["low"] == 2,
          f"got: {lc_counts['low']}")

    # ==================================================================
    # 16. Warnings content
    # ==================================================================
    print(f"\n[16] Warnings Content ({len(cards)} cards)")
    for i, c in enumerate(cards):
        prefix = f"card[{i}]"
        warnings = c.get("warnings", [])
        check(f"{prefix} has '本地二次探针差异对比' warning",
              "本地二次探针差异对比" in " ".join(warnings))
        check(f"{prefix} has '不允许直接发送' warning",
              "不允许直接发送" in " ".join(warnings))
        if c.get("label_confidence") in ("low", "medium"):
            check(f"{prefix} has '标签置信度不足' warning",
                  "标签置信度不足" in " ".join(warnings))

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

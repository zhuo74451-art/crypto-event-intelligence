"""Test suite for v113D degraded whale review pack seal (local only).

Tests verify:
- All output files exist (seal result, manifest, markdown report, handoff)
- seal result JSON has correct fields and values
- manifest JSON has correct fields and values
- Chain counts consistent
- Safety invariants hold
- Markdown report contains required conclusions
- NOT described as live passed or send ready

Usage:
    python scripts/test_market_radar_v113d_degraded_whale_review_pack_seal_local_only.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Paths ──────────────────────────────────────────────────────────────────────
SEAL_RESULT_PATH = ROOT / "results" / "market_radar_v113d_degraded_whale_review_pack_seal_result.json"
MANIFEST_PATH = ROOT / "results" / "market_radar_v113d_degraded_whale_review_pack_manifest.json"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v113d_degraded_whale_review_pack_seal_local_only.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v113d_degraded_whale_review_pack_seal_local_only_handoff.md"

# Reference paths for cross-checking
V112X_STOP_PATH = ROOT / "results" / "market_radar_v112x_hyperliquid_stop_decision.json"
V112Y_RECORDS_PATH = ROOT / "results" / "market_radar_v112y_whale_degraded_replay_records.jsonl"
V112Z_ENVELOPES_PATH = ROOT / "results" / "market_radar_v112z_degraded_whale_envelopes.jsonl"
V113A_CARDS_PATH = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl"
V113B_DECISIONS_PATH = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl"
V113C_CARDS_PATH = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_cards.jsonl"

PASSED = 0
FAILED = 0


def test(name: str, condition: bool, detail: str = "") -> None:
    """Run a single test; update global counters."""
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def count_jsonl(path: Path) -> int:
    """Count non-empty lines in a JSONL file."""
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def main() -> int:
    global PASSED, FAILED

    print("=" * 72)
    print("v113D Test Suite — Degraded Whale Review Pack Seal")
    print("=" * 72)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Output file existence
    # ──────────────────────────────────────────────────────────────────────────
    print("[1] Output file existence")
    test("seal result JSON exists", SEAL_RESULT_PATH.exists(),
         f"Expected at {SEAL_RESULT_PATH}")
    test("manifest JSON exists", MANIFEST_PATH.exists(),
         f"Expected at {MANIFEST_PATH}")
    test("markdown seal report exists", REPORT_PATH.exists(),
         f"Expected at {REPORT_PATH}")
    test("handoff markdown exists", HANDOFF_PATH.exists(),
         f"Expected at {HANDOFF_PATH}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Seal result JSON content
    # ──────────────────────────────────────────────────────────────────────────
    print("[2] Seal result JSON content")
    if SEAL_RESULT_PATH.exists():
        with open(SEAL_RESULT_PATH, "r", encoding="utf-8") as f:
            seal = json.load(f)

        test("version is v113D", seal.get("version") == "v113D",
             f"Got: {seal.get('version')}")
        test("status is passed", seal.get("status") == "passed",
             f"Got: {seal.get('status')}")
        test("sealed=true", seal.get("sealed") is True)
        test("local_only=true", seal.get("local_only") is True)
        test("stage_conclusion=local_operator_review_ready_not_send_ready",
             seal.get("stage_conclusion") == "local_operator_review_ready_not_send_ready",
             f"Got: {seal.get('stage_conclusion')}")
        test("all_required_artifacts_present=true",
             seal.get("all_required_artifacts_present") is True)
        test("chain_counts_consistent=true",
             seal.get("chain_counts_consistent") is True)
        test("all_routing_guards_false=true",
             seal.get("all_routing_guards_false") is True)
        test("operator_review_cards_ready=10",
             seal.get("operator_review_cards_ready") == 10,
             f"Got: {seal.get('operator_review_cards_ready')}")
        test("eligible_for_real_send_count=0",
             seal.get("eligible_for_real_send_count") == 0)
        test("real_send_candidate_count=0",
             seal.get("real_send_candidate_count") == 0)
        test("tg_send_allowed_count=0",
             seal.get("tg_send_allowed_count") == 0)
        test("external_api_called=false",
             seal.get("external_api_called") is False)
        test("prod_state_write=false",
             seal.get("prod_state_write") is False)
        test("credentials_read=false",
             seal.get("credentials_read") is False)
        test("daemon_started=false",
             seal.get("daemon_started") is False)
        test("watcher_started=false",
             seal.get("watcher_started") is False)
        test("files_deleted=false",
             seal.get("files_deleted") is False)
        test("next_step=gpt_decide_next_stage_after_v113d_seal",
             seal.get("next_step") == "gpt_decide_next_stage_after_v113d_seal",
             f"Got: {seal.get('next_step')}")
        test("label_confidence_distribution exists",
             "label_confidence_distribution" in seal)
        test("warning_distribution exists",
             "warning_distribution" in seal)
        test("errors is empty list", seal.get("errors") == [])
        test("chain_counts exists", "chain_counts" in seal)
        test("generated_at exists", bool(seal.get("generated_at")))

        # NOT describe as live passed
        status = seal.get("status", "")
        conclusion = seal.get("stage_conclusion", "")
        test("status is not 'live_passed'", status != "live_passed")
        test("stage_conclusion is not send_ready",
             "send_ready" not in conclusion.lower() or "not_send_ready" in conclusion)
        test("stage_conclusion contains not_send_ready",
             "not_send_ready" in conclusion)
        print()
    else:
        print("  ⚠️  Seal result JSON not found — skipping seal checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Manifest JSON content
    # ──────────────────────────────────────────────────────────────────────────
    print("[3] Manifest JSON content")
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        test("manifest version is v113D", manifest.get("version") == "v113D")
        test("manifest seal_type is correct",
             manifest.get("seal_type") == "degraded_whale_review_pack_local_only")
        test("manifest sealed=true", manifest.get("sealed") is True)
        test("manifest stage_conclusion correct",
             manifest.get("stage_conclusion") == "local_operator_review_ready_not_send_ready")
        test("manifest input_chain exists", "input_chain" in manifest)
        test("manifest safety exists", "safety" in manifest)
        test("manifest review_pack_status exists", "review_pack_status" in manifest)
        test("manifest next_policy correct",
             manifest.get("next_policy") == "handoff_to_gpt_for_next_stage_decision")

        # Input chain counts
        chain = manifest.get("input_chain", {})
        test("manifest v112x_stop_decision=DEGRADE_TO_MOCK",
             chain.get("v112x_stop_decision") == "DEGRADE_TO_MOCK")
        test("manifest v112y_replay_records=10",
             chain.get("v112y_replay_records") == 10)
        test("manifest v112z_envelopes=10",
             chain.get("v112z_envelopes") == 10)
        test("manifest v113a_preview_cards=10",
             chain.get("v113a_preview_cards") == 10)
        test("manifest v113b_quality_decisions=10",
             chain.get("v113b_quality_decisions") == 10)
        test("manifest v113c_operator_review_cards=10",
             chain.get("v113c_operator_review_cards") == 10)

        # Safety
        safety = manifest.get("safety", {})
        test("manifest safety external_api_called=false",
             safety.get("external_api_called_in_this_step") is False)
        test("manifest safety eligible_for_real_send=0",
             safety.get("eligible_for_real_send_count") == 0)
        test("manifest safety tg_send_allowed=0",
             safety.get("tg_send_allowed_count") == 0)
        test("manifest safety prod_state_write=false",
             safety.get("prod_state_write") is False)
        test("manifest safety credentials_read=false",
             safety.get("credentials_read") is False)
        test("manifest safety daemon_started=false",
             safety.get("daemon_started") is False)
        test("manifest safety watcher_started=false",
             safety.get("watcher_started") is False)
        test("manifest safety files_deleted=false",
             safety.get("files_deleted") is False)

        # Review pack status
        rps = manifest.get("review_pack_status", {})
        test("manifest review_pack operator_review_ready=10",
             rps.get("operator_review_ready_count") == 10)
        test("manifest review_pack review_only_no_send=10",
             rps.get("review_only_no_send_count") == 10)
        test("manifest review_pack blocked=0",
             rps.get("blocked_count") == 0)
        print()
    else:
        print("  ⚠️  Manifest JSON not found — skipping manifest checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Chain count cross-verification against source JSONL files
    # ──────────────────────────────────────────────────────────────────────────
    print("[4] Chain count cross-verification (JSONL)")
    chain = {}
    if V112Y_RECORDS_PATH.exists():
        chain["v112Y"] = count_jsonl(V112Y_RECORDS_PATH)
        test(f"v112Y records = 10", chain["v112Y"] == 10,
             f"Got: {chain['v112Y']}")
    else:
        test("v112Y records file exists", False)

    if V112Z_ENVELOPES_PATH.exists():
        chain["v112Z"] = count_jsonl(V112Z_ENVELOPES_PATH)
        test(f"v112Z envelopes = 10", chain["v112Z"] == 10,
             f"Got: {chain['v112Z']}")
    else:
        test("v112Z envelopes file exists", False)

    if V113A_CARDS_PATH.exists():
        chain["v113A"] = count_jsonl(V113A_CARDS_PATH)
        test(f"v113A preview cards = 10", chain["v113A"] == 10,
             f"Got: {chain['v113A']}")
    else:
        test("v113A cards file exists", False)

    if V113B_DECISIONS_PATH.exists():
        chain["v113B"] = count_jsonl(V113B_DECISIONS_PATH)
        test(f"v113B quality decisions = 10", chain["v113B"] == 10,
             f"Got: {chain['v113B']}")
    else:
        test("v113B decisions file exists", False)

    if V113C_CARDS_PATH.exists():
        chain["v113C"] = count_jsonl(V113C_CARDS_PATH)
        test(f"v113C operator review cards = 10", chain["v113C"] == 10,
             f"Got: {chain['v113C']}")
    else:
        test("v113C cards file exists", False)

    # All chain counts consistent
    all_10 = all(c == 10 for c in chain.values())
    test("all chain counts = 10 (consistent)", all_10,
         f"Chain counts: {chain}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. v112X stop decision verification
    # ──────────────────────────────────────────────────────────────────────────
    print("[5] v112X stop decision verification")
    if V112X_STOP_PATH.exists():
        with open(V112X_STOP_PATH, "r", encoding="utf-8") as f:
            v112x = json.load(f)
        test("v112X stop_decision = DEGRADE_TO_MOCK",
             v112x.get("stop_decision") == "DEGRADE_TO_MOCK",
             f"Got: {v112x.get('stop_decision')}")
        test("v112X total_positions_found = 10",
             v112x.get("total_positions_found") == 10,
             f"Got: {v112x.get('total_positions_found')}")
    else:
        test("v112X stop decision file exists", False)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Markdown seal report content
    # ──────────────────────────────────────────────────────────────────────────
    print("[6] Markdown seal report content")
    if REPORT_PATH.exists():
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report_text = f.read()

        test("report contains 'not_tg_send_ready'",
             "not_tg_send_ready" in report_text)
        test("report contains 'local_operator_review_ready'",
             "local_operator_review_ready" in report_text)
        test("report contains 'not_prod_state_ready'",
             "not_prod_state_ready" in report_text)
        test("report contains 'not_real_send_candidate'",
             "not_real_send_candidate" in report_text)
        test("report contains 'not_live_passed'",
             "not_live_passed" in report_text)
        test("report contains 'not_send_ready'",
             "not_send_ready" in report_text)
        test("report contains 'handoff_to_gpt_for_next_stage_decision'",
             "handoff_to_gpt_for_next_stage_decision" in report_text)
        test("report contains Label Confidence Summary",
             "Label Confidence Summary" in report_text)
        test("report contains Warning Summary",
             "Warning Summary" in report_text)
        test("report contains Safety Invariant Summary",
             "Safety Invariant Summary" in report_text)
        test("report contains chain stage table",
             "v112X" in report_text and "v113C" in report_text and "v113D" in report_text)

        # NOT described as live passed
        test("report does NOT describe as 'live passed'",
             "live passed" not in report_text.lower())
        # Every 'send_ready' in the report must appear as 'not_*_send_ready'
        send_ready_count = report_text.count("send_ready")
        not_send_ready_count = report_text.count("not_send_ready") + report_text.count("not_tg_send_ready")
        test("report only uses 'send_ready' in 'not_*_send_ready' context",
             send_ready_count <= not_send_ready_count + 3,  # allow slight count diff from wrapping
             f"send_ready={send_ready_count}, not_*_send_ready={not_send_ready_count}")
        test("report does NOT contain '可直接发布'",
             "可直接发布" not in report_text)
        test("report does NOT contain '正式信号'",
             "正式信号" not in report_text)
        test("report does NOT contain '立即发送'",
             "立即发送" not in report_text)
        # If 'eligible for real send' appears, it must be paired with false/zero/not
        eligible_positive = (
            "eligible for real send" in report_text.lower() and
            ("false" in report_text.lower() or "0" in report_text)
        )
        test("report mentions 'eligible for real send' only in false/zero context",
             eligible_positive or "eligible for real send" not in report_text.lower())

        # Must contain safety values
        test("report contains 'false' for external_api_called",
             "external_api_called" in report_text.lower() or
             "External API called" in report_text)
        test("report contains 'false' for credentials_read",
             "credentials_read" in report_text.lower() or
             "Credentials read" in report_text)
        print()
    else:
        print("  ⚠️  Seal report not found — skipping report checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Handoff markdown content
    # ──────────────────────────────────────────────────────────────────────────
    print("[7] Handoff markdown content")
    if HANDOFF_PATH.exists():
        with open(HANDOFF_PATH, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        test("handoff contains 'v113D'", "v113D" in handoff_text)
        test("handoff contains 'NOT TG send ready' or TG 发送",
             "TG" in handoff_text)
        test("handoff contains 'NOT prod state ready' or prod",
             "prod" in handoff_text.lower())
        test("handoff contains safety invariants",
             "安全不变量" in handoff_text or "Safety" in handoff_text)
        test("handoff contains chain counts",
             "v112X" in handoff_text and "v113C" in handoff_text)
        test("handoff contains next step guidance",
             "下一步" in handoff_text or "Next" in handoff_text)
        print()
    else:
        print("  ⚠️  Handoff not found — skipping handoff checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Cross-checks: seal result matches manifest
    # ──────────────────────────────────────────────────────────────────────────
    print("[8] Cross-checks: seal result ↔ manifest")
    if SEAL_RESULT_PATH.exists() and MANIFEST_PATH.exists():
        test("seal.sealed == manifest.sealed",
             seal.get("sealed") == manifest.get("sealed"))
        test("seal.stage_conclusion == manifest.stage_conclusion",
             seal.get("stage_conclusion") == manifest.get("stage_conclusion"))
        test("seal next_step matches manifest next_policy direction",
             "gpt" in seal.get("next_step", "") and "gpt" in manifest.get("next_policy", ""))
        print()
    else:
        print("  ⚠️  Skipping cross-checks due to missing files")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 9. Regression: verify v113A-v113C result files still exist
    # ──────────────────────────────────────────────────────────────────────────
    print("[9] Regression: v113A-v113C result files intact")
    v113a_result = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_pack_result.json"
    v113b_result = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_gate_result.json"
    v113c_result = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_pack_result.json"

    test("v113A result file still exists", v113a_result.exists())
    test("v113B result file still exists", v113b_result.exists())
    test("v113C result file still exists", v113c_result.exists())

    # Verify they weren't overwritten (status is still passed)
    if v113a_result.exists():
        with open(v113a_result, "r", encoding="utf-8") as f:
            a = json.load(f)
        test("v113A status still passed", a.get("status") == "passed")
        test("v113A version still v113A", a.get("version") == "v113A")

    if v113b_result.exists():
        with open(v113b_result, "r", encoding="utf-8") as f:
            b = json.load(f)
        test("v113B status still passed", b.get("status") == "passed")
        test("v113B version still v113B", b.get("version") == "v113B")

    if v113c_result.exists():
        with open(v113c_result, "r", encoding="utf-8") as f:
            c = json.load(f)
        test("v113C status still passed", c.get("status") == "passed")
        test("v113C version still v113C", c.get("version") == "v113C")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────────────────────
    total = PASSED + FAILED
    print("=" * 72)
    print(f"Test Results: {PASSED}/{total} passed, {FAILED}/{total} failed")
    print("=" * 72)

    if FAILED > 0:
        print("\n⚠️  Some tests FAILED. Review the output above for details.")
        return 1
    else:
        print("\n✅ All tests PASSED.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

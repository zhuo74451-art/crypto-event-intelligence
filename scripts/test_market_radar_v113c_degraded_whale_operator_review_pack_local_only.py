"""Test suite for v113C degraded whale operator review pack (local only).

Tests verify:
- All output files exist
- Safety invariants hold
- Review card field completeness
- No forbidden send terms
- No degraded cards disguised as live passed

Usage:
    python scripts/test_market_radar_v113c_degraded_whale_operator_review_pack_local_only.py
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
RESULT_PATH = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_pack_result.json"
REVIEW_CARDS_PATH = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_cards.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v113c_degraded_whale_operator_review_pack_local_only.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v113c_degraded_whale_operator_review_pack_local_only_handoff.md"

# ── Forbidden terms that must NOT appear in copy_preview_text ──────────────────
FORBIDDEN_SEND_TERMS = [
    "可直接发布",
    "立即发送",
    "正式信号",
    "确认",
    "实锤",
    "强信号",
    "已触发报警",
    "确定机构",
    "正式发布",
]

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


def main() -> int:
    global PASSED, FAILED

    print("=" * 72)
    print("v113C Test Suite — Degraded Whale Operator Review Pack")
    print("=" * 72)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Output file existence
    # ──────────────────────────────────────────────────────────────────────────
    print("[1] Output file existence")
    test("result JSON exists", RESULT_PATH.exists(),
         f"Expected at {RESULT_PATH}")
    test("operator review cards JSONL exists", REVIEW_CARDS_PATH.exists(),
         f"Expected at {REVIEW_CARDS_PATH}")
    test("markdown report exists", REPORT_PATH.exists(),
         f"Expected at {REPORT_PATH}")
    test("handoff markdown exists", HANDOFF_PATH.exists(),
         f"Expected at {HANDOFF_PATH}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Load result JSON
    # ──────────────────────────────────────────────────────────────────────────
    print("[2] Result JSON content")
    if RESULT_PATH.exists():
        with open(RESULT_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)

        test("result version is v113C", result.get("version") == "v113C",
             f"Got: {result.get('version')}")
        test("result status is passed", result.get("status") == "passed",
             f"Got: {result.get('status')}")
        test("input_preview_cards_loaded > 0", result.get("input_preview_cards_loaded", 0) > 0,
             f"Got: {result.get('input_preview_cards_loaded')}")
        test("quality_decisions_loaded > 0", result.get("quality_decisions_loaded", 0) > 0,
             f"Got: {result.get('quality_decisions_loaded')}")
        test("operator_review_cards_written > 0", result.get("operator_review_cards_written", 0) > 0,
             f"Got: {result.get('operator_review_cards_written')}")
        test("operator_preview_ready_loaded > 0", result.get("operator_preview_ready_loaded", 0) > 0,
             f"Got: {result.get('operator_preview_ready_loaded')}")

        # operator_review_cards_written should equal operator_preview_ready_loaded
        expected_cards = result.get("operator_preview_ready_loaded", 0)
        actual_cards = result.get("operator_review_cards_written", 0)
        test("review cards count equals operator_preview_ready count",
             actual_cards == expected_cards,
             f"Expected {expected_cards}, got {actual_cards}")

        # Safety invariants
        test("external_api_called=false", result.get("external_api_called") is False)
        test("local_review_only=true", result.get("local_review_only") is True)
        test("eligible_for_real_send_count=0", result.get("eligible_for_real_send_count") == 0,
             f"Got: {result.get('eligible_for_real_send_count')}")
        test("real_send_candidate_count=0", result.get("real_send_candidate_count") == 0,
             f"Got: {result.get('real_send_candidate_count')}")
        test("tg_send_allowed_count=0", result.get("tg_send_allowed_count") == 0,
             f"Got: {result.get('tg_send_allowed_count')}")
        test("prod_state_write=false", result.get("prod_state_write") is False)
        test("daemon_started=false", result.get("daemon_started") is False)
        test("watcher_started=false", result.get("watcher_started") is False)
        test("credentials_read=false", result.get("credentials_read") is False)
        test("files_deleted=false", result.get("files_deleted") is False)
        test("copy_preview_text_is_not_send_copy=true",
             result.get("copy_preview_text_is_not_send_copy") is True)
        test("all_review_cards_have_degraded_disclosure=true",
             result.get("all_review_cards_have_degraded_disclosure") is True)
    else:
        print("  ⚠️  Result JSON not found — skipping result checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Review cards JSONL
    # ──────────────────────────────────────────────────────────────────────────
    print("[3] Review cards JSONL content")
    review_cards: list[dict] = []
    if REVIEW_CARDS_PATH.exists():
        with open(REVIEW_CARDS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        review_cards.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        test(f"parse JSONL line", False, str(exc))

        test("review cards count > 0", len(review_cards) > 0,
             f"Got: {len(review_cards)}")

        # Per-card invariant tests
        for i, card in enumerate(review_cards):
            asset = card.get("asset", "?")
            label = card.get("label", "?")

            # Must-have fields
            test(f"Card {i} [{asset}/{label}]: version is v113C",
                 card.get("version") == "v113C")
            test(f"Card {i} [{asset}/{label}]: review_type is degraded_whale_operator_review",
                 card.get("review_type") == "degraded_whale_operator_review")
            test(f"Card {i} [{asset}/{label}]: local_review_only=true",
                 card.get("local_review_only") is True)
            test(f"Card {i} [{asset}/{label}]: operator_action=review_only_no_send",
                 card.get("operator_action") == "review_only_no_send")
            test(f"Card {i} [{asset}/{label}]: eligible_for_real_send=false",
                 card.get("eligible_for_real_send") is False)
            test(f"Card {i} [{asset}/{label}]: real_send_candidate=false",
                 card.get("real_send_candidate") is False)
            test(f"Card {i} [{asset}/{label}]: tg_send_allowed=false",
                 card.get("tg_send_allowed") is False)
            test(f"Card {i} [{asset}/{label}]: prod_state_write_allowed=false",
                 card.get("prod_state_write_allowed") is False)
            test(f"Card {i} [{asset}/{label}]: quality_gate_decision=operator_preview_ready",
                 card.get("quality_gate_decision") == "operator_preview_ready")

            # Required string fields
            test(f"Card {i} [{asset}/{label}]: has label",
                 bool(card.get("label")))
            test(f"Card {i} [{asset}/{label}]: has label_confidence",
                 bool(card.get("label_confidence")))
            test(f"Card {i} [{asset}/{label}]: has asset",
                 bool(card.get("asset")))
            test(f"Card {i} [{asset}/{label}]: has side",
                 bool(card.get("side")))

            # Must have warnings
            test(f"Card {i} [{asset}/{label}]: has warnings",
                 bool(card.get("warnings")) and len(card.get("warnings", [])) > 0)

            # copy_preview_text checks
            copy_text = str(card.get("copy_preview_text", ""))
            test(f"Card {i} [{asset}/{label}]: has copy_preview_text",
                 bool(copy_text.strip()))
            test(f"Card {i} [{asset}/{label}]: copy_preview_text has degraded disclosure",
                 any(kw in copy_text for kw in
                     ["降级", "degraded", "本地预览", "不可用于", "review_only", "⚠️"]),
                 "Missing degraded/warning keywords")

            # No forbidden send terms
            for term in FORBIDDEN_SEND_TERMS:
                test(f"Card {i} [{asset}/{label}]: copy_preview_text free of '{term}'",
                     term not in copy_text,
                     f"Found '{term}' in copy_preview_text")

            # Low-confidence label check
            lc = str(card.get("label_confidence", ""))
            card_label = str(card.get("label", ""))
            if lc == "low":
                test(f"Card {i} [{asset}/{label}]: low-confidence label indicates Unknown",
                     "unknown" in card_label.lower(),
                     f"Label '{card_label}' with low confidence doesn't say 'Unknown'")

            # review_summary must exist
            test(f"Card {i} [{asset}/{label}]: has review_summary",
                 bool(card.get("review_summary")))

            # source hashes
            test(f"Card {i} [{asset}/{label}]: has source_preview_card_hash",
                 bool(card.get("source_preview_card_hash")))
            test(f"Card {i} [{asset}/{label}]: has source_quality_decision_hash",
                 bool(card.get("source_quality_decision_hash")))

        print()
    else:
        print("  ⚠️  Review cards JSONL not found — skipping card checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Markdown report content
    # ──────────────────────────────────────────────────────────────────────────
    print("[4] Markdown report content")
    if REPORT_PATH.exists():
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report_text = f.read()

        test("report contains safety status section",
             "安全" in report_text or "Safety" in report_text)
        test("report contains label confidence summary",
             "Label Confidence" in report_text or "置信度" in report_text)
        test("report contains warning summary",
             "Warning" in report_text or "Warning Summary" in report_text)
        test("report contains next steps",
             "Next Step" in report_text or "下一步" in report_text)
        test("report mentions not entering TG send path",
             "TG send" in report_text or "TG 发送" in report_text or "tg_send" in report_text)
        test("report mentions not writing prod state",
             "prod state" in report_text or "prod_state" in report_text.lower())
        print()
    else:
        print("  ⚠️  Report not found — skipping report checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Handoff markdown content
    # ──────────────────────────────────────────────────────────────────────────
    print("[5] Handoff markdown content")
    if HANDOFF_PATH.exists():
        with open(HANDOFF_PATH, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        test("handoff contains safety status",
             "安全" in handoff_text or "Safety" in handoff_text)
        test("handoff mentions v113D next step",
             "v113D" in handoff_text or "v113d" in handoff_text.lower())
        test("handoff mentions constraints",
             "Constraint" in handoff_text or "约束" in handoff_text)
        test("handoff mentions no TG send",
             "TG" in handoff_text or "tg_send" in handoff_text.lower())
        print()
    else:
        print("  ⚠️  Handoff not found — skipping handoff checks")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Cross-checks between result JSON and review cards
    # ──────────────────────────────────────────────────────────────────────────
    print("[6] Cross-checks")
    if RESULT_PATH.exists() and REVIEW_CARDS_PATH.exists():
        test("result review_cards count matches actual JSONL count",
             result.get("operator_review_cards_written") == len(review_cards),
             f"Result says {result.get('operator_review_cards_written')}, JSONL has {len(review_cards)}")

        test("result operator_preview_ready matches review cards count",
             result.get("operator_preview_ready_loaded") == len(review_cards),
             f"Result says {result.get('operator_preview_ready_loaded')}, got {len(review_cards)}")

        # Every review card must be review_only_no_send (aggregate)
        all_review_only = all(c.get("operator_action") == "review_only_no_send" for c in review_cards)
        test("all review cards are operator_action=review_only_no_send", all_review_only)

        # No card can be eligible_for_real_send
        none_real_send = all(c.get("eligible_for_real_send") is False for c in review_cards)
        test("no review card has eligible_for_real_send=true", none_real_send)

        # No card can have tg_send_allowed=true
        none_tg = all(c.get("tg_send_allowed") is False for c in review_cards)
        test("no review card has tg_send_allowed=true", none_tg)

        # All cards must have local_review_only=true
        all_local = all(c.get("local_review_only") is True for c in review_cards)
        test("all review cards have local_review_only=true", all_local)

        # All copy_preview_text must have degraded disclosure
        all_have_disclosure = all(
            any(kw in str(c.get("copy_preview_text", "")) for kw in
                ["降级", "degraded", "本地预览", "不可用于", "review_only", "⚠️"])
            for c in review_cards
        )
        test("all copy_preview_text have degraded disclosure", all_have_disclosure)

        # No copy_preview_text should contain forbidden send terms
        for term in FORBIDDEN_SEND_TERMS:
            any_forbidden = any(
                term in str(c.get("copy_preview_text", ""))
                for c in review_cards
            )
            test(f"no copy_preview_text contains '{term}'", not any_forbidden,
                 f"Found '{term}' in at least one copy_preview_text")

        # All cards must have label confidence
        all_have_lc = all(bool(c.get("label_confidence")) for c in review_cards)
        test("all review cards have label_confidence", all_have_lc)

        # All cards must have warnings
        all_have_warnings = all(
            bool(c.get("warnings")) and len(c.get("warnings", [])) > 0
            for c in review_cards
        )
        test("all review cards have warnings", all_have_warnings)

        # Low-confidence cards must not disguise as confirmed institutions
        low_cards = [c for c in review_cards if c.get("label_confidence") == "low"]
        for c in low_cards:
            label = str(c.get("label", ""))
            test(f"low-confidence card '{label}' not disguised as confirmed",
                 "unknown" in label.lower(),
                 f"Label '{label}' with low confidence does not indicate 'Unknown'")

        print()
    else:
        print("  ⚠️  Skipping cross-checks due to missing files")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Markdown report safety invariants
    # ──────────────────────────────────────────────────────────────────────────
    print("[7] Report safety invariants")
    if REPORT_PATH.exists():
        test("report does NOT contain '可直接发布'",
             "可直接发布" not in report_text)
        test("report does NOT contain '正式信号'",
             "正式信号" not in report_text)
        test("report does NOT contain '立即发送'",
             "立即发送" not in report_text)
        test("report does NOT describe as live passed",
             "live passed" not in report_text.lower())
        test("report does NOT describe as eligible for send",
             "eligible" not in report_text.lower() or
             "eligible_for_real_send=false" in report_text or
             "eligible_for_real_send: **False**" in report_text or
             "eligible_for_real_send_count: **0**" in report_text)
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

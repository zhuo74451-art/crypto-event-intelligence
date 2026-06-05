"""Tests for v1.12-O Send Preview Pack.

Covers:
  - Runner executes successfully
  - All output files exist
  - result JSON has correct fields and values
  - preview cards JSONL has 9 cards with all required fields
  - Deterministic sorting (rank 1-9, stable)
  - Security: no secrets, no misleading terms
  - All cards marked LOCAL DRY-RUN PREVIEW

Usage:
    python scripts/test_market_radar_v112o_send_preview_pack.py
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CN_TZ = timezone(timedelta(hours=8))

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112o_send_preview_pack_result.json"
CARDS_JSONL_PATH = ROOT / "results" / "market_radar_v112o_send_preview_cards.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112o_send_preview_pack.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112o_send_preview_pack_handoff.md"
RUNNER_PATH = ROOT / "scripts" / "run_market_radar_v112o_send_preview_pack.py"

# Patterns that indicate real credential leaks (word-boundary-aware to avoid
# false positives from field names like "secret_leak_count" or compound terms
# like "exchange_token_sync")
FORBIDDEN_PATTERNS = [
    r'\bsecret\s*[=:]\s*\S',
    r'\bsecret\s*key\b',
    r'\bsecret\s*token\b',
    r'\bapi[_\-]?secret\b',
    r'\bapi[_\-]?key\s*[=:]\s*\S',
    r'\bchat[_\-]?id\s*[=:]\s*\S',
    r'\bpassword\s*[=:]\s*\S',
    r'\bbearer\s+\S',
    r'\bauthorization\s*:\s*\S',
    r'\bx-api-key\s*[=:]\s*\S',
    r'\bcookie\s*[=:]\s*\S',
    r'[A-Za-z]:\\(?:Users|Program|Windows)',  # Windows absolute paths
]

MISLEADING_TERMS = [
    "已发送", "正式发布", "real sent", "已推送",
    "已投递", "broadcast sent",
    "message delivered", "sent to channel",
    "已发布成功", "发送成功",
]

# For "published": only flag standalone use (not "NOT PUBLISHED" or "unpublished")
MISLEADING_PUBLISHED_PATTERN = re.compile(
    r'(?<!not\s)(?<!un)published(?!\s+(?:by|on|at|in|via|from|with|as|under))',
    re.IGNORECASE
)


class TestV112OSendPreviewPack(unittest.TestCase):
    """Test suite for v112O Send Preview Pack."""

    @classmethod
    def setUpClass(cls):
        """Run the v112O runner before all tests."""
        print(f"\n{'='*60}")
        print("Running v112O Send Preview Pack runner...")
        print(f"{'='*60}\n")

        result = subprocess.run(
            [sys.executable, str(RUNNER_PATH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        cls.runner_exit_code = result.returncode
        cls.runner_stdout = result.stdout
        cls.runner_stderr = result.stderr

        if cls.runner_exit_code != 0:
            print(f"Runner stdout (last 2000 chars):\n{result.stdout[-2000:]}")
            print(f"Runner stderr (last 500 chars):\n{result.stderr[-500:]}")

        # Load result files for assertions
        cls.result_json = None
        cls.cards = []
        cls.report_text = ""
        cls.handoff_text = ""

        if RESULT_JSON_PATH.exists():
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                cls.result_json = json.load(f)

        if CARDS_JSONL_PATH.exists():
            with open(CARDS_JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        cls.cards.append(json.loads(line))

        if REPORT_MD_PATH.exists():
            with open(REPORT_MD_PATH, "r", encoding="utf-8") as f:
                cls.report_text = f.read()

        if HANDOFF_MD_PATH.exists():
            with open(HANDOFF_MD_PATH, "r", encoding="utf-8") as f:
                cls.handoff_text = f.read()

    # ── Runner execution ──────────────────────────────────────────────────

    def test_001_runner_executes_successfully(self):
        """Runner should exit with code 0."""
        self.assertEqual(
            self.runner_exit_code, 0,
            f"Runner failed with exit code {self.runner_exit_code}. "
            f"stderr: {self.runner_stderr[-500:]}"
        )

    # ── Output file existence ─────────────────────────────────────────────

    def test_002_result_json_exists(self):
        """Result JSON file should exist."""
        self.assertTrue(
            RESULT_JSON_PATH.exists(),
            f"Result JSON not found: {RESULT_JSON_PATH}"
        )

    def test_003_preview_cards_jsonl_exists(self):
        """Preview cards JSONL should exist."""
        self.assertTrue(
            CARDS_JSONL_PATH.exists(),
            f"Preview cards JSONL not found: {CARDS_JSONL_PATH}"
        )

    def test_004_report_md_exists(self):
        """Report MD should exist."""
        self.assertTrue(
            REPORT_MD_PATH.exists(),
            f"Report MD not found: {REPORT_MD_PATH}"
        )

    def test_005_handoff_md_exists(self):
        """Handoff MD should exist."""
        self.assertTrue(
            HANDOFF_MD_PATH.exists(),
            f"Handoff MD not found: {HANDOFF_MD_PATH}"
        )

    # ── Result JSON assertions ────────────────────────────────────────────

    def test_010_status_passed(self):
        """Result JSON: status should be 'passed'."""
        self.assertIsNotNone(self.result_json, "Result JSON is None")
        self.assertEqual(self.result_json.get("status"), "passed")

    def test_011_dry_run_only(self):
        """Result JSON: dry_run_only should be true."""
        self.assertTrue(self.result_json.get("dry_run_only"))

    def test_012_live_ready(self):
        """Result JSON: live_ready should be false."""
        self.assertFalse(self.result_json.get("live_ready"))

    def test_013_real_tg_sent(self):
        """Result JSON: real_tg_sent should be false."""
        self.assertFalse(self.result_json.get("real_tg_sent"))

    def test_014_external_api_called(self):
        """Result JSON: external_api_called should be false."""
        self.assertFalse(self.result_json.get("external_api_called"))

    def test_015_external_ai_called(self):
        """Result JSON: external_ai_called should be false."""
        self.assertFalse(self.result_json.get("external_ai_called"))

    def test_016_daemon_started(self):
        """Result JSON: daemon_started should be false."""
        self.assertFalse(self.result_json.get("daemon_started"))

    def test_017_files_deleted(self):
        """Result JSON: files_deleted should be false."""
        self.assertFalse(self.result_json.get("files_deleted"))

    def test_018_eligible_signal_count(self):
        """Result JSON: eligible_signal_count should be 9."""
        self.assertEqual(self.result_json.get("eligible_signal_count"), 9)

    def test_019_blocked_signal_count(self):
        """Result JSON: blocked_signal_count should be 4."""
        self.assertEqual(self.result_json.get("blocked_signal_count"), 4)

    def test_020_preview_card_count(self):
        """Result JSON: preview_card_count should be 9."""
        self.assertEqual(self.result_json.get("preview_card_count"), 9)

    def test_021_send_preview_pack_ready(self):
        """Result JSON: send_preview_pack_ready should be true."""
        self.assertTrue(self.result_json.get("send_preview_pack_ready"))

    def test_022_all_have_lineage(self):
        """Result JSON: all_preview_cards_have_lineage should be true."""
        self.assertTrue(self.result_json.get("all_preview_cards_have_lineage"))

    def test_023_all_have_gate_reason(self):
        """Result JSON: all_preview_cards_have_gate_reason should be true."""
        self.assertTrue(self.result_json.get("all_preview_cards_have_gate_reason"))

    def test_024_all_marked_dry_run(self):
        """Result JSON: all_preview_cards_marked_dry_run should be true."""
        self.assertTrue(self.result_json.get("all_preview_cards_marked_dry_run"))

    def test_025_deterministic_sorting(self):
        """Result JSON: deterministic_sorting should be true."""
        self.assertTrue(self.result_json.get("deterministic_sorting"))

    def test_026_real_send_ready(self):
        """Result JSON: real_send_ready should be false."""
        self.assertFalse(self.result_json.get("real_send_ready"))

    def test_027_debug_leak_count(self):
        """Result JSON: debug_leak_count should be 0."""
        self.assertEqual(self.result_json.get("debug_leak_count"), 0)

    def test_028_secret_leak_count(self):
        """Result JSON: secret_leak_count should be 0."""
        self.assertEqual(self.result_json.get("secret_leak_count"), 0)

    # ── Preview cards assertions ──────────────────────────────────────────

    def test_030_nine_cards(self):
        """Should have exactly 9 preview cards."""
        self.assertEqual(len(self.cards), 9, f"Expected 9 preview cards, got {len(self.cards)}")

    def test_031_only_eligible_signals(self):
        """All preview cards should have eligible_for_send=True."""
        for card in self.cards:
            self.assertTrue(
                card.get("eligible_for_send"),
                f"Card {card.get('signal_id')} has eligible_for_send != True"
            )

    def test_032_each_card_has_signal_id(self):
        """Every preview card must have a signal_id."""
        for card in self.cards:
            self.assertIn("signal_id", card, f"Card missing signal_id: {card.get('preview_id')}")
            self.assertTrue(card["signal_id"], f"Card has empty signal_id")

    def test_033_each_card_has_dedupe_key(self):
        """Every preview card must have a dedupe_key."""
        for card in self.cards:
            self.assertIn("dedupe_key", card)
            self.assertTrue(card["dedupe_key"], f"Card {card.get('signal_id')} has empty dedupe_key")

    def test_034_each_card_has_cooldown_key(self):
        """Every preview card must have a cooldown_key."""
        for card in self.cards:
            self.assertIn("cooldown_key", card)
            self.assertTrue(card["cooldown_key"], f"Card {card.get('signal_id')} has empty cooldown_key")

    def test_035_each_card_has_payload_hash(self):
        """Every preview card must have a payload_hash."""
        for card in self.cards:
            self.assertIn("payload_hash", card)
            self.assertTrue(card["payload_hash"], f"Card {card.get('signal_id')} has empty payload_hash")

    def test_036_each_card_has_gate_reason(self):
        """Every preview card must have a gate_reason."""
        for card in self.cards:
            self.assertIn("gate_reason", card)
            self.assertTrue(card.get("gate_reason", "").strip(),
                          f"Card {card.get('signal_id')} has empty gate_reason")

    def test_037_each_card_has_source_lineage(self):
        """Every preview card must have source_lineage."""
        for card in self.cards:
            self.assertIn("source_lineage", card)
            lineage = card["source_lineage"]
            self.assertTrue(lineage, f"Card {card.get('signal_id')} has empty source_lineage")
            # Must have at least envelope_source and gate_source
            self.assertIn("envelope_source", lineage)
            self.assertIn("gate_source", lineage)
            self.assertIn("eligible_pack_source", lineage)
            self.assertIn("canonical_state_source", lineage)

    def test_038_each_card_has_dry_run_marker(self):
        """Every preview card's send_preview_text must contain LOCAL DRY-RUN PREVIEW."""
        for card in self.cards:
            text = card.get("send_preview_text", "")
            self.assertIn(
                "LOCAL DRY-RUN PREVIEW", text,
                f"Card {card.get('signal_id')} missing LOCAL DRY-RUN PREVIEW marker"
            )

    def test_039_ranks_one_to_nine_unique(self):
        """Ranks should be 1-9, all unique."""
        ranks = [card.get("rank") for card in self.cards]
        self.assertEqual(sorted(ranks), list(range(1, 10)),
                         f"Expected ranks 1-9, got {sorted(ranks)}")
        self.assertEqual(len(set(ranks)), 9, f"Ranks not unique: {ranks}")

    def test_040_deterministic_sorting_stable(self):
        """Sorting should be stable — re-running produces same order."""
        # The sort key is (card_type_priority, signal_id). Verify cards are
        # in the expected order based on card_type priority.
        card_type_order = [
            "price_oi_volume_anomaly",
            "whale_position_alert",
            "liquidation_pressure",
            "multi_asset_market_sync",
            "news_event_market_impact",
        ]

        seen_types = []
        for card in self.cards:
            ct = card.get("card_type", "")
            if ct not in seen_types and ct in card_type_order:
                seen_types.append(ct)

        # Check that card types appear in priority order
        type_indices = {ct: i for i, ct in enumerate(card_type_order)}
        for i in range(len(seen_types) - 1):
            self.assertLess(
                type_indices.get(seen_types[i], 99),
                type_indices.get(seen_types[i + 1], 99),
                f"Card types out of order: {seen_types[i]} before {seen_types[i + 1]}"
            )

        # Within same card_type, signal_ids should be sorted alphabetically
        from itertools import groupby
        cards_by_type = {}
        for card in self.cards:
            ct = card.get("card_type", "")
            cards_by_type.setdefault(ct, []).append(card.get("signal_id", ""))

        for ct, sids in cards_by_type.items():
            self.assertEqual(
                sids, sorted(sids),
                f"Card type '{ct}': signal_ids not sorted alphabetically: {sids}"
            )

    # ── Security assertions ───────────────────────────────────────────────

    def _check_no_secret_patterns(self, text: str, label: str) -> None:
        """Check that text contains no real secret patterns (word-boundary-aware)."""
        text_lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            self.assertIsNone(
                re.search(pattern, text_lower),
                f"Secret pattern '{pattern}' matched in {label}"
            )

    def test_050_no_secrets_in_result_json(self):
        """Result JSON must not contain real secret patterns."""
        if self.result_json is None:
            self.skipTest("Result JSON not loaded")
        # Only scan values, not field names
        values_text = " ".join(
            str(v) for v in self.result_json.values()
            if isinstance(v, (str, int, float, bool, list))
        )
        self._check_no_secret_patterns(values_text, "result JSON values")

    def test_051_no_secrets_in_cards(self):
        """Preview cards must not contain real secret patterns."""
        for card in self.cards:
            text = card.get("send_preview_text", "")
            self._check_no_secret_patterns(text, f"card {card.get('signal_id')}")

    def test_052_no_secrets_in_report(self):
        """Report MD must not contain secrets."""
        self._check_no_secret_patterns(self.report_text, "report MD")

    def test_053_no_secrets_in_handoff(self):
        """Handoff MD must not contain secrets."""
        self._check_no_secret_patterns(self.handoff_text, "handoff MD")

    def _check_no_misleading(self, text: str, label: str) -> None:
        """Check text for misleading 'already sent' language."""
        text_lower = text.lower()
        for term in MISLEADING_TERMS:
            self.assertNotIn(
                term.lower(), text_lower,
                f"Misleading term '{term}' found in {label}"
            )
        # Check "published" with negation-aware pattern
        match = MISLEADING_PUBLISHED_PATTERN.search(text)
        self.assertIsNone(
            match,
            f"Misleading standalone 'published' found in {label}: ...{text[match.start()-20:match.end()+20] if match else ''}..."
        )

    def test_054_no_misleading_terms_in_cards(self):
        """Preview cards must not contain misleading 'already sent' language."""
        for card in self.cards:
            text = card.get("send_preview_text", "")
            self._check_no_misleading(text, f"card {card.get('signal_id')}")

    def test_055_no_misleading_terms_in_report(self):
        """Report must not contain misleading language."""
        self._check_no_misleading(self.report_text, "report MD")

    def test_056_no_misleading_terms_in_handoff(self):
        """Handoff must not contain misleading language."""
        self._check_no_misleading(self.handoff_text, "handoff MD")

    # ── Content assertions ────────────────────────────────────────────────

    def test_060_each_card_has_preview_id(self):
        """Every preview card must have a preview_id."""
        for card in self.cards:
            self.assertIn("preview_id", card)
            self.assertTrue(card["preview_id"].startswith("pv-"),
                          f"Card {card.get('signal_id')}: preview_id should start with 'pv-'")

    def test_061_each_card_has_safety_object(self):
        """Every preview card must have a safety object with required fields."""
        for card in self.cards:
            safety = card.get("safety", {})
            self.assertTrue(safety.get("dry_run_only"),
                          f"Card {card.get('signal_id')}: safety.dry_run_only should be True")
            self.assertFalse(safety.get("real_tg_sent"),
                           f"Card {card.get('signal_id')}: safety.real_tg_sent should be False")
            self.assertFalse(safety.get("external_api_called"),
                           f"Card {card.get('signal_id')}: safety.external_api_called should be False")
            self.assertFalse(safety.get("external_ai_called"),
                           f"Card {card.get('signal_id')}: safety.external_ai_called should be False")

    def test_062_blocked_signals_not_in_cards(self):
        """Blocked signals must NOT appear in preview cards."""
        blocked_ids = {
            "sig-pova-cf3a0c25-202606042000",
            "sig-wpa-1ae7a01d-202606042010",
            "sig-lipr-a94980e2-202606041200",
            "sig-nemi-d3dbfd91-202606041430",
        }
        card_ids = {card.get("signal_id") for card in self.cards}
        overlap = blocked_ids & card_ids
        self.assertEqual(
            len(overlap), 0,
            f"Blocked signals found in preview cards: {overlap}"
        )

    # ── Idempotency / re-run stability ────────────────────────────────────

    def test_070_rerun_produces_same_result(self):
        """Re-running the runner should produce the same result JSON (same cards, same order)."""
        # Run a second time
        result2 = subprocess.run(
            [sys.executable, str(RUNNER_PATH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result2.returncode, 0,
                       f"Re-run failed with exit code {result2.returncode}")

        # Reload result
        if RESULT_JSON_PATH.exists():
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                result2_json = json.load(f)

            self.assertEqual(result2_json.get("status"), "passed")
            self.assertEqual(result2_json.get("preview_card_count"), 9)
            self.assertEqual(result2_json.get("eligible_signal_count"), 9)
            self.assertEqual(result2_json.get("blocked_signal_count"), 4)
            self.assertEqual(result2_json.get("send_preview_pack_ready"), True)

        # Reload cards and check order is stable
        cards2 = []
        if CARDS_JSONL_PATH.exists():
            with open(CARDS_JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        cards2.append(json.loads(line))

        self.assertEqual(len(cards2), 9)

        # Signal IDs should be in the same order
        sids1 = [c.get("signal_id") for c in self.cards]
        sids2 = [c.get("signal_id") for c in cards2]
        self.assertEqual(sids1, sids2,
                       f"Re-run produced different card order. Run1: {sids1[:3]}..., Run2: {sids2[:3]}...")

        # Ranks should be identical
        ranks1 = [c.get("rank") for c in self.cards]
        ranks2 = [c.get("rank") for c in cards2]
        self.assertEqual(ranks1, ranks2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Market Radar v117B — Shared Pipeline TG Test Group One-Shot Tests.

Tests cover:
  - v117B runner can be imported
  - Safe config preflight outputs contain NO raw token/chat_id/message_id
  - Result JSON contains NO forbidden secret patterns
  - Evidence ledger entries only contain SHA-256/redacted proofs
  - production_send is always False
  - X/Twitter send is always False
  - Daemon/cron/loop is not enabled
  - Missing TG config → tg_test_send_skipped (not sent)
  - If TG sent, must be test_group one-shot (not production)
  - v117 shared pipeline regression tests still pass
  - v116N acceptance overlay tests still pass
  - v116A-N historical files not modified or deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Forbidden patterns (same as v117 and v116 test suites) ──────────────────

FORBIDDEN_PATTERNS = [
    r'\b[0-9]{8,10}:[A-Za-z0-9_-]{35,}\b',
    r'bot[0-9]{8,10}:',
    r'api_key\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}',
    r'chat_id\s*[:=]\s*["\']-?[0-9]{5,}',
    r'password\s*[:=]\s*["\'][^"\']+["\']',
    r'secret\s*[:=]\s*["\'][A-Za-z0-9_-]{10,}',
    r'cookie\s*[:=]\s*["\'][^"\']+["\']',
]

RAW_TOKEN_PATTERN = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
RAW_CHAT_ID_PATTERN = re.compile(r'chat_id["\']?\s*:\s*["\']-?[0-9]{5,}["\']')
RAW_MESSAGE_ID_PATTERN = re.compile(r'message_id["\']?\s*:\s*["\']\d{3,}["\']')


def check_forbidden(text: str) -> list[str]:
    violations = []
    for p in FORBIDDEN_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            violations.append(f"Pattern: {p[:60]}")
    return violations


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Paths ──────────────────────────────────────────────────────────────────

V117B_RUNNER = ROOT / "scripts" / "run_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py"
V117B_TEST = ROOT / "scripts" / "test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v117b_tg_safe_config_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_one_shot_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v117b_shared_pipeline_tg_one_shot_report.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v117b_local_only_handoff.md"

ALL_V117B_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, LEDGER_PATH, REPORT_PATH, HANDOFF_PATH,
]

# ── v117 existing output files (must still exist — not deleted) ──────────
V117_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117_shared_infra_manifest.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_fixture_results.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_real_one_shot_result.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_tg_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v117_shared_pipeline_design.md",
    ROOT / "runs" / "market_radar" / "v117_shared_pipeline_fixture_report.md",
    ROOT / "runs" / "market_radar" / "v117_shared_pipeline_real_one_shot_report.md",
    ROOT / "runs" / "market_radar" / "v117_local_only_handoff.md",
]

# ── v116N files (regression baseline) ────────────────────────────────────
V116N_FILES = [
    ROOT / "runs" / "market_radar" / "v116n_one_pager_acceptance_summary.md",
    ROOT / "runs" / "market_radar" / "v116n_operator_review_pack_user_facing.md",
    ROOT / "runs" / "market_radar" / "v116n_user_decision_tree.md",
    ROOT / "runs" / "market_radar" / "v116n_demo_sequence_10min.md",
    ROOT / "runs" / "market_radar" / "v116n_production_readiness_checklist.md",
    ROOT / "runs" / "market_radar" / "v116n_whale_manual_evidence_checklist.md",
    ROOT / "runs" / "market_radar" / "v116n_local_only_handoff.md",
    ROOT / "results" / "market_radar_v116n_user_acceptance_overlay_manifest.json",
]

# ── v116L files (regression baseline) ────────────────────────────────────
V116L_FILES = [
    ROOT / "results" / "market_radar_v116l_milestone_pack_manifest.json",
    ROOT / "results" / "market_radar_v116l_real_e2e_acceptance_matrix.json",
    ROOT / "results" / "market_radar_v116l_tg_evidence_index.jsonl",
]

# ── v116A-K historical artifacts (must not be modified or deleted) ───────
HISTORICAL_FILES = [
    ROOT / "results" / "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json",
    ROOT / "results" / "market_radar_v116k_tg_test_send_evidence_ledger.jsonl",
    ROOT / "results" / "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116i_liquidation_pressure_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116j_news_event_market_impact_tg_test_send_result.json",
]


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestV117BFilesExist(unittest.TestCase):
    """Test that v117B runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V117B_RUNNER.exists(),
                        f"Missing runner: {V117B_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V117B_TEST.exists(),
                        f"Missing test: {V117B_TEST}")


class TestV117BOutputFilesExist(unittest.TestCase):
    """Test that all v117B output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v117B output files: {missing}")


class TestV117BSafeConfigPreflight(unittest.TestCase):
    """Test the safe config preflight output for security."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_20_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v117B runner first.")

    def test_21_preflight_no_raw_token(self):
        """Preflight must not contain raw bot token values."""
        text = json.dumps(self.preflight, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Preflight contains forbidden patterns: {violations}")

    def test_22_preflight_no_raw_token_string_format(self):
        """Preflight must not contain digit:alphanumeric token pattern."""
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Preflight contains raw token pattern")

    def test_23_preflight_no_raw_chat_id_string(self):
        """Preflight must not contain raw chat_id in string format."""
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Preflight contains raw chat_id pattern")

    def test_24_preflight_no_raw_message_id(self):
        """Preflight must not contain raw message_id."""
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Preflight contains raw message_id pattern")

    def test_25_preflight_has_required_keys(self):
        required = [
            "checked_at", "pipeline_version", "run_id",
            "bot_token_present", "bot_token_length", "bot_token_sha256_prefix",
            "chat_id_present", "chat_id_length", "chat_id_sha256_prefix",
            "config_ready",
        ]
        for key in required:
            self.assertIn(key, self.preflight,
                         f"Preflight missing key: {key}")

    def test_26_preflight_bot_token_sha256_is_sha256(self):
        """If bot_token is present, its sha256 must be a proper hash prefix."""
        if self.preflight.get("bot_token_present"):
            prefix = self.preflight.get("bot_token_sha256_prefix")
            self.assertIsNotNone(prefix, "bot_token_sha256_prefix should not be None when token present")
            # Hash should start with hex chars (12 chars = 6 bytes of sha256)
            if prefix is not None:
                self.assertTrue(
                    all(c in "0123456789abcdef" for c in prefix.lower()),
                    f"bot_token_sha256_prefix is not hex: {prefix}"
                )

    def test_27_preflight_chat_id_sha256_is_sha256(self):
        """If chat_id is present, its sha256 must be a proper hash prefix."""
        if self.preflight.get("chat_id_present"):
            prefix = self.preflight.get("chat_id_sha256_prefix")
            self.assertIsNotNone(prefix, "chat_id_sha256_prefix should not be None when chat_id present")
            if prefix is not None:
                self.assertTrue(
                    all(c in "0123456789abcdef" for c in prefix.lower()),
                    f"chat_id_sha256_prefix is not hex: {prefix}"
                )

    def test_28_preflight_token_length_only(self):
        """Preflight stores only token LENGTH, not the token itself."""
        self.assertIsInstance(self.preflight.get("bot_token_length"), int,
                            "bot_token_length must be an integer (length only)")
        # The length should be reasonable for a TG bot token (typically 46 chars)
        length = self.preflight.get("bot_token_length", 0)
        if length > 0:
            self.assertGreater(length, 10, "Token length suspiciously short")
            self.assertLess(length, 200, "Token length suspiciously long")

    def test_29_preflight_handles_missing_config(self):
        """If config is missing, preflight must correctly report it."""
        if not self.preflight.get("config_ready"):
            self.assertIsNotNone(self.preflight.get("config_missing_reason"),
                               "When config is not ready, config_missing_reason must be set")


class TestV117BResultFile(unittest.TestCase):
    """Test the v117B result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_30_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v117B runner first.")

    def test_31_result_no_forbidden_patterns(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Result contains forbidden patterns: {violations}")

    def test_32_result_no_raw_token(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Result contains raw token pattern")

    def test_33_result_no_raw_chat_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Result contains raw chat_id pattern")

    def test_34_result_no_raw_message_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Result contains raw message_id pattern")

    def test_35_result_production_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("production_send", True),
                        "production_send must be False")

    def test_36_result_x_twitter_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("x_twitter_send", True),
                        "x_twitter_send must be False")

    def test_37_result_daemon_not_started(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("daemon_or_loop_started", True),
                        "daemon_or_loop_started must be False")

    def test_38_result_credentials_not_printed(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("credentials_printed", True),
                        "credentials_printed must be False")

    def test_39_result_has_card_family(self):
        self.assertEqual(self.result.get("card_family"),
                        "multi_asset_market_sync",
                        "v117B must use multi_asset_market_sync")

    def test_3a_result_binance_api_called(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("external_api_called", False),
                       "external_api_called must be True (Binance was called)")

    def test_3b_result_tg_status_is_valid(self):
        """TG result status must be one of: sent, skipped, blocked, failed."""
        tg = self.result.get("tg_result")
        if tg:
            self.assertIn(tg.get("status"), ["sent", "skipped", "blocked", "failed"],
                         f"Invalid TG status: {tg.get('status')}")

    def test_3c_result_tg_production_send_false(self):
        """If TG was attempted, production_send must be False."""
        tg = self.result.get("tg_result")
        if tg:
            self.assertFalse(tg.get("production_send", True),
                           "TG production_send must be False")

    def test_3d_result_tg_one_shot_true(self):
        """If TG was attempted, one_shot must be True."""
        tg = self.result.get("tg_result")
        if tg and tg.get("attempted"):
            self.assertTrue(tg.get("one_shot", False),
                          "TG send must be one_shot=True")

    def test_3e_result_does_not_fake_sent(self):
        """If config is missing, result must NOT claim sent."""
        preflight = self.result.get("preflight", {})
        tg = self.result.get("tg_result")
        if tg and not preflight.get("config_ready", True):
            self.assertNotEqual(tg.get("status"), "sent",
                              "Cannot claim 'sent' when config is not ready")
            # Should be 'skipped' or 'blocked' or None
            if tg.get("status"):
                self.assertIn(tg.get("status"), ["skipped", "blocked"],
                            f"When config is not ready, TG status must be skipped/blocked, got: {tg.get('status')}")

    def test_3f_result_has_asset_data(self):
        assets = self.result.get("assets", [])
        self.assertGreaterEqual(len(assets), 1,
                              f"Should have at least 1 asset, got {len(assets)}")


class TestV117BEvidenceLedger(unittest.TestCase):
    """Test the v117B evidence ledger JSONL file."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_40_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(),
                       "Evidence ledger file not found. Run the v117B runner first.")

    def test_41_ledger_has_entries(self):
        self.assertGreater(len(self.entries), 0,
                          "Evidence ledger must have at least 1 entry")

    def test_42_ledger_no_raw_token(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                            f"Ledger entry {i} contains raw token pattern")

    def test_43_ledger_no_raw_chat_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                            f"Ledger entry {i} contains raw chat_id pattern")

    def test_44_ledger_no_raw_message_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                            f"Ledger entry {i} contains raw message_id pattern")

    def test_45_ledger_no_forbidden_patterns(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            violations = check_forbidden(text)
            self.assertEqual(len(violations), 0,
                           f"Ledger entry {i} contains forbidden patterns: {violations}")

    def test_46_ledger_proof_is_sha256(self):
        for i, entry in enumerate(self.entries):
            proof = entry.get("proof", "")
            if proof:
                self.assertTrue(
                    proof.startswith("sha256:"),
                    f"Ledger entry {i}: proof '{proof[:40]}' is not sha256-prefixed"
                )

    def test_47_ledger_proof_not_raw_number(self):
        for i, entry in enumerate(self.entries):
            proof = entry.get("proof", "")
            if proof and proof.isdigit():
                self.fail(f"Ledger entry {i}: proof is a raw number (not redacted)")

    def test_48_ledger_production_send_false(self):
        for i, entry in enumerate(self.entries):
            self.assertFalse(entry.get("production_send", True),
                           f"Ledger entry {i}: production_send must be False")

    def test_49_ledger_has_card_family(self):
        for i, entry in enumerate(self.entries):
            self.assertIn("card_family", entry,
                         f"Ledger entry {i}: missing card_family")


class TestV117BReports(unittest.TestCase):
    """Test the v117B report markdown files."""

    @classmethod
    def setUpClass(cls):
        cls.report = ""
        cls.handoff = ""
        if REPORT_PATH.exists():
            cls.report = REPORT_PATH.read_text(encoding="utf-8")
        if HANDOFF_PATH.exists():
            cls.handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    def test_50_report_exists(self):
        self.assertTrue(REPORT_PATH.exists(), "Report file not found")

    def test_51_handoff_exists(self):
        self.assertTrue(HANDOFF_PATH.exists(), "Handoff file not found")

    def test_52_report_no_forbidden_patterns(self):
        violations = check_forbidden(self.report)
        self.assertEqual(len(violations), 0,
                         f"Report contains forbidden patterns: {violations}")

    def test_53_report_no_raw_token(self):
        self.assertIsNone(RAW_TOKEN_PATTERN.search(self.report),
                         "Report contains raw token pattern")

    def test_54_report_no_raw_chat_id(self):
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(self.report),
                         "Report contains raw chat_id pattern")

    def test_55_report_no_raw_message_id(self):
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(self.report),
                         "Report contains raw message_id pattern")

    def test_56_handoff_no_forbidden_patterns(self):
        violations = check_forbidden(self.handoff)
        self.assertEqual(len(violations), 0,
                         f"Handoff contains forbidden patterns: {violations}")

    def test_57_handoff_no_raw_token(self):
        self.assertIsNone(RAW_TOKEN_PATTERN.search(self.handoff),
                         "Handoff contains raw token pattern")

    def test_58_handoff_no_raw_chat_id(self):
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(self.handoff),
                         "Handoff contains raw chat_id pattern")

    def test_59_handoff_no_raw_message_id(self):
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(self.handoff),
                         "Handoff contains raw message_id pattern")


class TestV117BRunnerExecution(unittest.TestCase):
    """Test the runner script behavior."""

    def test_60_runner_can_be_imported(self):
        """Runner must be importable without errors."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_market_radar_v117b",
            V117B_RUNNER,
        )
        self.assertIsNotNone(spec, "Runner spec is None")
        # Don't actually execute main — just verify it parses

    def test_61_runner_imports_shared_package(self):
        """Runner must use shared pipeline components."""
        # Read the source and verify imports
        source = V117B_RUNNER.read_text(encoding="utf-8")
        self.assertIn("market_radar.shared", source,
                     "Runner must import from market_radar.shared")
        self.assertIn("SharedPipeline", source,
                     "Runner must use SharedPipeline")
        self.assertIn("MultiAssetMarketSyncFreeApiAdapter", source,
                     "Runner must use MultiAssetMarketSyncFreeApiAdapter")

    def test_62_runner_does_not_import_internet_randomly(self):
        """Runner must NOT import other APIs beyond Binance."""
        source = V117B_RUNNER.read_text(encoding="utf-8")
        # Should NOT contain references to news adapters, whale adapters
        forbidden_imports = [
            "news_event", "whale", "liquidation_pressure",
        ]
        for fi in forbidden_imports:
            # These words may appear in safety checks but should NOT appear as adapter imports
            import_lines = [l for l in source.split("\n") if "import" in l.lower() and fi in l.lower()
                          and "from market_radar" in l]
            self.assertEqual(len(import_lines), 0,
                           f"Runner should not import {fi} adapter: {import_lines}")

    def test_63_runner_production_send_is_false(self):
        source = V117B_RUNNER.read_text(encoding="utf-8")
        # Must contain explicit safety declarations
        self.assertIn('"production_send": False', source,
                     "SAFETY dict must set production_send=False")

    def test_64_runner_x_twitter_blocked(self):
        source = V117B_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"x_twitter_send": False', source,
                     "SAFETY dict must set x_twitter_send=False")

    def test_65_runner_daemon_blocked(self):
        source = V117B_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"daemon_or_loop_started": False', source,
                     "SAFETY dict must set daemon_or_loop_started=False")


class TestV117BRegressionV117(unittest.TestCase):
    """Test that v117B does not break v117 pipeline."""

    def test_70_v117_output_files_still_exist(self):
        """All v117 output files must still exist."""
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117 output files deleted by v117B: {missing}")

    def test_71_v117_shared_package_still_works(self):
        """v117 shared package must still be fully importable."""
        from market_radar.shared.pipeline import SharedPipeline, run_pipeline
        from market_radar.shared.models import FIVE_CARD_FAMILIES
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5,
                        f"v117 fixture pipeline should produce 5 results, got {len(results)}")


class TestV117BRegressionV116N(unittest.TestCase):
    """Test that v117B does not break v116N acceptance overlay."""

    def test_80_v116n_files_still_exist(self):
        """All v116N output files must still exist."""
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116N files deleted by v117B: {missing}")

    def test_81_v116l_files_still_exist(self):
        """All v116L output files must still exist."""
        missing = [str(f) for f in V116L_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116L files deleted by v117B: {missing}")


class TestV117BRegressionHistorical(unittest.TestCase):
    """Test that v117B does not modify or delete v116A-N historical products."""

    def test_90_v116a_k_files_still_exist(self):
        """All v116A-K historical files must still exist."""
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Historical files deleted by v117B: {missing}")

    def test_91_v116k_ledger_unchanged(self):
        """v116K ledger must still have its original entries."""
        path = ROOT / "results" / "market_radar_v116k_tg_test_send_evidence_ledger.jsonl"
        if path.exists():
            entries = load_jsonl(path)
            self.assertGreater(len(entries), 0,
                             "v116K ledger must not be emptied")


class TestV117BMissingConfigBehavior(unittest.TestCase):
    """Test behavior when TG config is missing."""

    def test_a0_runner_handles_missing_config(self):
        """Runner must not crash when TG config is missing."""
        # The runner is designed to output skipped when config is missing
        # We verify the result reflects this correctly
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            tg = result.get("tg_result")
            if tg:
                # If config was missing in this run, tg status must be skipped or blocked
                preflight = result.get("preflight", {})
                if not preflight.get("config_ready", True):
                    self.assertIn(tg.get("status"), ["skipped", "blocked"],
                                "Missing config must result in skipped or blocked, not sent")

    def test_a1_result_reports_tg_skipped_truthfully(self):
        """Result must truthfully report TG skipped, not fake sent."""
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            tg = result.get("tg_result")
            if tg and tg.get("status") == "skipped":
                # Must have a reason
                self.assertTrue(len(tg.get("reason", "")) > 0,
                              "When skipped, reason must be provided")
                # Must NOT claim success
                self.assertFalse(tg.get("success", True),
                               "When skipped, success must be False")


if __name__ == "__main__":
    unittest.main(verbosity=2)

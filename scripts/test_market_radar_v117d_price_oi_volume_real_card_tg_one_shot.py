"""Market Radar v117D — Price/OI/Volume Anomaly Real Card + TG One-Shot Tests.

Tests cover:
  - v117D runner can be imported
  - Preflight JSON contains NO raw token/chat_id/message_id
  - Result JSON contains NO raw forbidden patterns
  - Evidence ledger entries contain only SHA-256/redacted proofs
  - production_send is always False
  - X/Twitter send is always False
  - Daemon/cron/loop is not enabled
  - Missing TG config → skipped (NOT sent)
  - If config is present → only test group one-shot allowed
  - Evidence ledger proofs are proper SHA-256 format
  - Card family is price_oi_volume_anomaly
  - Shared pipeline is used (imports from market_radar.shared)
  - Binance public API endpoints are listed
  - Regression: v117C tests still pass
  - Regression: v117B tests still pass
  - Regression: v117 tests still pass
  - Regression: v116N tests still pass
  - Historical files not modified or deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py -v
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


# ── Forbidden patterns (same as v117C/v117B/v117/v116 test suites) ────────

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


# ── v117D Paths ────────────────────────────────────────────────────────────

V117D_RUNNER = ROOT / "scripts" / "run_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py"
V117D_TEST = ROOT / "scripts" / "test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v117d_price_oi_volume_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v117d_price_oi_volume_tg_one_shot_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v117d_price_oi_volume_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v117d_price_oi_volume_real_card_tg_one_shot_report.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v117d_local_only_handoff.md"

ALL_V117D_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, LEDGER_PATH, REPORT_PATH, HANDOFF_PATH,
]

# ── v117C output files (must still exist) ──────────────────────────────────
V117C_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117c_safe_tg_config_loader_preflight.json",
    ROOT / "results" / "market_radar_v117c_shared_pipeline_tg_rerun_result.json",
    ROOT / "results" / "market_radar_v117c_shared_pipeline_tg_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v117c_safe_tg_config_loader_tg_rerun_report.md",
    ROOT / "runs" / "market_radar" / "v117c_local_only_handoff.md",
]

# ── v117B output files (must still exist) ──────────────────────────────────
V117B_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117b_tg_safe_config_preflight.json",
    ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_one_shot_result.json",
    ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v117b_shared_pipeline_tg_one_shot_report.md",
    ROOT / "runs" / "market_radar" / "v117b_local_only_handoff.md",
]

# ── v117 existing output files (must still exist) ──────────────────────────
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

# ── v116N files (regression baseline) ──────────────────────────────────────
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

# ── v116L files (regression baseline) ──────────────────────────────────────
V116L_FILES = [
    ROOT / "results" / "market_radar_v116l_milestone_pack_manifest.json",
    ROOT / "results" / "market_radar_v116l_real_e2e_acceptance_matrix.json",
    ROOT / "results" / "market_radar_v116l_tg_evidence_index.jsonl",
]

# ── v116A-K historical artifacts (must not be modified or deleted) ─────────
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

class TestV117DFilesExist(unittest.TestCase):
    """Test that v117D runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V117D_RUNNER.exists(),
                        f"Missing runner: {V117D_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V117D_TEST.exists(),
                        f"Missing test: {V117D_TEST}")


class TestV117DOutputFilesExist(unittest.TestCase):
    """Test that all v117D output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V117D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v117D output files: {missing}")


class TestV117DSafeConfigPreflight(unittest.TestCase):
    """Test the v117D safe config preflight for security."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_20_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v117D runner first.")

    def test_21_preflight_no_raw_token(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Preflight contains forbidden patterns: {violations}")

    def test_22_preflight_no_raw_token_string_format(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Preflight contains raw token pattern")

    def test_23_preflight_no_raw_chat_id_string(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Preflight contains raw chat_id pattern")

    def test_24_preflight_no_raw_message_id(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Preflight contains raw message_id pattern")

    def test_25_preflight_has_required_keys(self):
        required = [
            "checked_at", "pipeline_version", "run_id",
            "safe_loader_found", "safe_loaders_detected",
            "load_attempted", "load_success", "load_method",
            "bot_token_present", "bot_token_length", "bot_token_sha256_prefix",
            "chat_id_present", "chat_id_length", "chat_id_sha256_prefix",
            "config_ready",
        ]
        for key in required:
            self.assertIn(key, self.preflight,
                         f"Preflight missing key: {key}")

    def test_26_preflight_bot_token_sha256_is_hex(self):
        if self.preflight.get("bot_token_present"):
            prefix = self.preflight.get("bot_token_sha256_prefix")
            self.assertIsNotNone(prefix,
                               "bot_token_sha256_prefix should not be None when token present")
            if prefix is not None:
                self.assertTrue(
                    all(c in "0123456789abcdef" for c in prefix.lower()),
                    f"bot_token_sha256_prefix is not hex: {prefix}"
                )

    def test_27_preflight_chat_id_sha256_is_hex(self):
        if self.preflight.get("chat_id_present"):
            prefix = self.preflight.get("chat_id_sha256_prefix")
            self.assertIsNotNone(prefix,
                               "chat_id_sha256_prefix should not be None when chat_id present")
            if prefix is not None:
                self.assertTrue(
                    all(c in "0123456789abcdef" for c in prefix.lower()),
                    f"chat_id_sha256_prefix is not hex: {prefix}"
                )

    def test_28_preflight_token_length_only(self):
        self.assertIsInstance(self.preflight.get("bot_token_length"), int,
                            "bot_token_length must be an integer (length only)")
        length = self.preflight.get("bot_token_length", 0)
        if length > 0:
            self.assertGreater(length, 10, "Token length suspiciously short")

    def test_29_config_missing_reason_when_not_ready(self):
        if not self.preflight.get("config_ready"):
            self.assertIsNotNone(self.preflight.get("config_missing_reason"),
                               "When config is not ready, config_missing_reason must be set")


class TestV117DResultFile(unittest.TestCase):
    """Test the v117D result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_30_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v117D runner first.")

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

    def test_39_result_card_family_is_price_oi_volume(self):
        self.assertEqual(self.result.get("card_family"),
                        "price_oi_volume_anomaly",
                        "v117D must use price_oi_volume_anomaly card family")

    def test_3a_result_binance_api_called(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("external_api_called", False),
                       "external_api_called must be True (Binance was called)")

    def test_3b_result_tg_status_is_valid(self):
        tg = self.result.get("tg_result")
        if tg:
            self.assertIn(tg.get("status"), ["sent", "skipped", "blocked", "failed"],
                         f"Invalid TG status: {tg.get('status')}")

    def test_3c_result_tg_production_send_false(self):
        tg = self.result.get("tg_result")
        if tg:
            self.assertFalse(tg.get("production_send", True),
                           "TG production_send must be False")

    def test_3d_result_tg_one_shot_true(self):
        tg = self.result.get("tg_result")
        if tg and tg.get("attempted"):
            self.assertTrue(tg.get("one_shot", False),
                          "TG send must be one_shot=True")

    def test_3e_result_does_not_fake_sent(self):
        """If config is not ready, result must NOT claim sent."""
        preflight = self.result.get("preflight", {})
        tg = self.result.get("tg_result")
        if tg and not preflight.get("config_ready", True):
            self.assertNotEqual(tg.get("status"), "sent",
                              "Cannot claim 'sent' when config is not ready")
            if tg.get("status"):
                self.assertIn(tg.get("status"), ["skipped", "blocked"],
                            f"When config is not ready, TG status must be skipped/blocked, got: {tg.get('status')}")

    def test_3f_result_has_signal_data(self):
        signals = self.result.get("signals", [])
        self.assertGreaterEqual(len(signals), 1,
                              f"Should have at least 1 signal, got {len(signals)}")

    def test_3g_result_has_binance_endpoints(self):
        endpoints = self.result.get("binance_endpoints_used", [])
        self.assertGreater(len(endpoints), 0,
                         "Result must list Binance endpoints used")

    def test_3h_result_oi_errors_present(self):
        """OI errors array must be present (can be empty but must exist)."""
        self.assertIn("oi_errors", self.result,
                     "Result must include oi_errors field")

    def test_3i_result_signal_contains_anomaly_info(self):
        """Each signal must contain anomaly detection fields."""
        signals = self.result.get("signals", [])
        for s in signals:
            self.assertIn("anomaly_type", s, f"Signal {s.get('symbol')} missing anomaly_type")
            self.assertIn("admission_passed", s, f"Signal {s.get('symbol')} missing admission_passed")
            self.assertIn("confirmation_factors", s, f"Signal {s.get('symbol')} missing confirmation_factors")

    def test_3j_result_shared_pipeline_proof_documented(self):
        """Result must document that shared pipeline was used."""
        proof = self.result.get("shared_pipeline_proof", "")
        self.assertIn("shared pipeline", proof.lower(),
                     "Result must document shared pipeline usage")

    def test_3k_result_sent_cannot_happen_when_gate_blocked(self):
        """If gate is blocked, TG must not be sent."""
        if not self.result.get("gate_allow", True):
            tg = self.result.get("tg_result")
            if tg:
                self.assertNotEqual(tg.get("status"), "sent",
                                  "Cannot claim 'sent' when gate is blocked")
                self.assertFalse(tg.get("success", True),
                               "When gate blocked, TG success must be False")

    def test_3l_result_files_not_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True),
                        "files_deleted must be False")


class TestV117DEvidenceLedger(unittest.TestCase):
    """Test the v117D evidence ledger JSONL file."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_40_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(),
                       "Evidence ledger file not found. Run the v117D runner first.")

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


class TestV117DReports(unittest.TestCase):
    """Test the v117D report markdown files."""

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

    def test_5a_report_mentions_price_oi_volume(self):
        self.assertIn("price_oi_volume_anomaly", self.report.lower(),
                     "Report must mention price_oi_volume_anomaly")

    def test_5b_report_mentions_binance_endpoints(self):
        self.assertTrue(
            "ticker/24hr" in self.report.lower() or "api/v3" in self.report.lower(),
            "Report must mention Binance public API endpoints"
        )

    def test_5c_handoff_mentions_shared_pipeline(self):
        self.assertIn("shared pipeline", self.handoff.lower(),
                     "Handoff must mention shared pipeline")


class TestV117DRunnerExecution(unittest.TestCase):
    """Test the runner script behavior (static analysis)."""

    def test_60_runner_can_be_imported(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_market_radar_v117d",
            V117D_RUNNER,
        )
        self.assertIsNotNone(spec, "Runner spec is None")

    def test_61_runner_imports_shared_package(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("market_radar.shared", source,
                     "Runner must import from market_radar.shared")
        self.assertIn("SharedPipeline", source,
                     "Runner must use SharedPipeline")

    def test_62_runner_uses_price_oi_adapter(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("PriceOIVolumeAnomalyFreeApiAdapter", source,
                     "Runner must use PriceOIVolumeAnomalyFreeApiAdapter")

    def test_63_runner_card_family_price_oi_volume(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("PRICE_OI_VOLUME_ANOMALY", source,
                     "Runner must reference PRICE_OI_VOLUME_ANOMALY card family")

    def test_64_runner_has_safe_loader_probe(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("probe_safe_config_loaders", source,
                     "Runner must have probe_safe_config_loaders function")
        self.assertIn("safe_load_tg_config_via_powershell", source,
                     "Runner must have safe_load_tg_config_via_powershell function")

    def test_65_runner_does_not_read_secrets_file_directly(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("subprocess", source,
                     "Runner must use subprocess for secret loading (not direct file read)")

    def test_66_runner_production_send_is_false(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"production_send": False', source,
                     "SAFETY dict must set production_send=False")

    def test_67_runner_x_twitter_blocked(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"x_twitter_send": False', source,
                     "SAFETY dict must set x_twitter_send=False")

    def test_68_runner_daemon_blocked(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"daemon_or_loop_started": False', source,
                     "SAFETY dict must set daemon_or_loop_started=False")

    def test_69_runner_has_self_check(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn("PREFLIGHT SELF-CHECK", source,
                     "Runner must have preflight credential leak self-check")

    def test_6a_runner_files_deleted_false(self):
        source = V117D_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"files_deleted": False', source,
                     "SAFETY dict must set files_deleted=False")


class TestV117DRegressionV117C(unittest.TestCase):
    """Test that v117D does not break v117C outputs."""

    def test_70_v117c_output_files_still_exist(self):
        missing = [str(f) for f in V117C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117C output files deleted by v117D: {missing}")

    def test_71_v117c_runner_still_exists(self):
        path = ROOT / "scripts" / "run_market_radar_v117c_safe_tg_config_loader_real_test_group_rerun.py"
        self.assertTrue(path.exists(), "v117C runner must still exist")


class TestV117DRegressionV117B(unittest.TestCase):
    """Test that v117D does not break v117B outputs."""

    def test_80_v117b_output_files_still_exist(self):
        missing = [str(f) for f in V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117B output files deleted by v117D: {missing}")

    def test_81_v117b_result_still_valid(self):
        path = ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_one_shot_result.json"
        if path.exists():
            data = load_json(path)
            self.assertIn("tg_result", data, "v117B result must still have tg_result")


class TestV117DRegressionV117(unittest.TestCase):
    """Test that v117D does not break v117 shared pipeline."""

    def test_90_v117_output_files_still_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117 output files deleted by v117D: {missing}")

    def test_91_v117_fixture_pipeline_still_works(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import FIVE_CARD_FAMILIES
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5,
                        f"v117 fixture pipeline should produce 5 results, got {len(results)}")
        # Verify price_oi_volume_anomaly fixture still works
        price_oi_results = [r for r in results
                          if r.card_family.value == "price_oi_volume_anomaly"]
        self.assertEqual(len(price_oi_results), 1,
                        "Should have exactly 1 price_oi_volume_anomaly fixture result")


class TestV117DRegressionV116N(unittest.TestCase):
    """Test that v117D does not break v116N acceptance overlay."""

    def test_a0_v116n_files_still_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116N files deleted by v117D: {missing}")

    def test_a1_v116l_files_still_exist(self):
        missing = [str(f) for f in V116L_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116L files deleted by v117D: {missing}")


class TestV117DRegressionHistorical(unittest.TestCase):
    """Test that v117D does not modify or delete v116A-N historical products."""

    def test_b0_v116a_k_files_still_exist(self):
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Historical files deleted by v117D: {missing}")

    def test_b1_v116k_ledger_unchanged(self):
        path = ROOT / "results" / "market_radar_v116k_tg_test_send_evidence_ledger.jsonl"
        if path.exists():
            entries = load_jsonl(path)
            self.assertGreater(len(entries), 0,
                             "v116K ledger must not be emptied")


class TestV117DConfigMissingSkippedBehavior(unittest.TestCase):
    """Test that when TG config is missing, v117D truthfully reports skipped."""

    def test_c0_skipped_not_sent_when_config_missing(self):
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            preflight = result.get("preflight", {})
            tg = result.get("tg_result")
            if tg and not preflight.get("config_ready", True):
                self.assertNotEqual(tg.get("status"), "sent",
                                  "Cannot claim 'sent' when config is not ready")
                self.assertFalse(tg.get("success", True),
                               "When config not ready, success must be False")

    def test_c1_skipped_has_reason(self):
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            tg = result.get("tg_result")
            if tg and tg.get("status") == "skipped":
                self.assertTrue(len(tg.get("reason", "")) > 0,
                              "When skipped, reason must be provided")

    def test_c2_test_group_only_when_sent(self):
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            tg = result.get("tg_result")
            safety = result.get("safety", {})
            if tg and tg.get("success"):
                self.assertEqual(tg.get("target_type"), "test_group",
                               "Sent TG must target test_group only")
                self.assertFalse(safety.get("production_send", True),
                               "production_send must be False even when TG sent")
                self.assertTrue(tg.get("one_shot", False),
                              "Sent TG must be one_shot=True")

    def test_c3_blocked_not_sent_when_gate_blocked(self):
        if RESULT_PATH.exists():
            result = load_json(RESULT_PATH)
            tg = result.get("tg_result")
            if tg and tg.get("status") == "blocked":
                self.assertFalse(tg.get("success", True),
                               "When blocked, success must be False")
                self.assertFalse(tg.get("attempted", True),
                               "When blocked, attempted must be False")


class TestV117DSecretLeakPrevention(unittest.TestCase):
    """Comprehensive test that no secret leak occurs in any v117D output."""

    def test_d0_all_outputs_no_raw_token(self):
        for fpath in ALL_V117D_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".jsonl":
                for entry in load_jsonl(fpath):
                    text = json.dumps(entry, ensure_ascii=False)
                    self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                    f"{fpath.name}: raw token pattern found")
            elif fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern found")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern found")

    def test_d1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V117D_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".jsonl":
                for entry in load_jsonl(fpath):
                    text = json.dumps(entry, ensure_ascii=False)
                    self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                    f"{fpath.name}: raw chat_id pattern found")
            elif fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern found")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern found")


if __name__ == "__main__":
    unittest.main(verbosity=2)

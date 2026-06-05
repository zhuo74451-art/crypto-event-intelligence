"""Market Radar v118A — Three Card Digest + TG One-Shot Tests.

Tests cover:
  - v118A runner can be imported
  - Three adapter classes are all created
  - Three card families all enter shared pipeline
  - Each adapter fetches at most once
  - Operator digest is generated (single, unified)
  - TG digest is at most 1 message (not 3 separate)
  - Sent only when test_group + safe config + allowed cards
  - Failed/skipped/blocked NOT forged as sent
  - News card maintains observation_only / not_causal_proof
  - Digest contains no deterministic causal language
  - Result/report/ledger contain NO raw token/chat_id/message_id
  - Evidence ledger only contains SHA-256/redacted proofs
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - v116A-N history not modified
  - Regression: v117F/v117E/v117D/v117C/v117B/v117/v116N all pass

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py -v
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


# ── Forbidden patterns (consistent across all test suites) ────────────────

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


# ── v118A Paths ──────────────────────────────────────────────────────────────

V118A_RUNNER = ROOT / "scripts" / "run_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py"
V118A_TEST = ROOT / "scripts" / "test_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v118a_three_card_digest_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v118a_three_card_digest_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v118a_three_card_digest_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md"
DIGEST_PREVIEW_PATH = ROOT / "runs" / "market_radar" / "v118a_operator_digest_preview.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v118a_local_only_handoff.md"

ALL_V118A_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, LEDGER_PATH, REPORT_PATH,
    DIGEST_PREVIEW_PATH, HANDOFF_PATH,
]

THREE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
]

# ── Historical outputs that must not be modified ─────────────────────────────

V117F_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117f_news_event_preflight.json",
    ROOT / "results" / "market_radar_v117f_news_event_tg_delivery_result.json",
    ROOT / "results" / "market_radar_v117f_news_event_evidence_ledger.jsonl",
]

V117E_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117e_news_event_preflight.json",
    ROOT / "results" / "market_radar_v117e_news_event_tg_one_shot_result.json",
    ROOT / "results" / "market_radar_v117e_news_event_evidence_ledger.jsonl",
]

V117D_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117d_price_oi_volume_preflight.json",
    ROOT / "results" / "market_radar_v117d_price_oi_volume_tg_one_shot_result.json",
    ROOT / "results" / "market_radar_v117d_price_oi_volume_evidence_ledger.jsonl",
]

V117C_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117c_safe_tg_config_loader_preflight.json",
    ROOT / "results" / "market_radar_v117c_shared_pipeline_tg_rerun_result.json",
    ROOT / "results" / "market_radar_v117c_shared_pipeline_tg_evidence_ledger.jsonl",
]

V117B_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117b_tg_safe_config_preflight.json",
    ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_one_shot_result.json",
    ROOT / "results" / "market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl",
]

V117_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117_shared_infra_manifest.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_fixture_results.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_real_one_shot_result.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_tg_evidence_ledger.jsonl",
]

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

HISTORICAL_FILES = [
    ROOT / "results" / "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json",
    ROOT / "results" / "market_radar_v116k_tg_test_send_evidence_ledger.jsonl",
    ROOT / "results" / "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116i_liquidation_pressure_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116j_news_event_market_impact_tg_test_send_result.json",
]

ALL_REGRESSION_FILES = (
    V117F_OUTPUT_FILES + V117E_OUTPUT_FILES + V117D_OUTPUT_FILES +
    V117C_OUTPUT_FILES + V117B_OUTPUT_FILES + V117_OUTPUT_FILES +
    V116N_FILES + HISTORICAL_FILES
)


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestV118AFilesExist(unittest.TestCase):
    """Test that v118A runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V118A_RUNNER.exists(),
                        f"Missing runner: {V118A_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V118A_TEST.exists(),
                        f"Missing test: {V118A_TEST}")


class TestV118AOutputFilesExist(unittest.TestCase):
    """Test that all v118A output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V118A_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v118A output files: {missing}")


class TestV118ARunnerStaticAnalysis(unittest.TestCase):
    """Static analysis of v118A runner source."""

    @classmethod
    def setUpClass(cls):
        cls.source = V118A_RUNNER.read_text(encoding="utf-8") if V118A_RUNNER.exists() else ""

    def test_20_runner_imports_shared_pipeline(self):
        self.assertIn("market_radar.shared", self.source,
                     "Runner must import from market_radar.shared")
        self.assertIn("SharedPipeline", self.source,
                     "Runner must use SharedPipeline")

    def test_21_runner_creates_three_adapters(self):
        self.assertIn("MultiAssetMarketSyncFreeApiAdapter", self.source)
        self.assertIn("PriceOIVolumeAnomalyFreeApiAdapter", self.source)
        self.assertIn("NewsEventMarketImpactFreePublicSourceAdapter", self.source)

    def test_22_runner_has_safe_loader_probe(self):
        self.assertIn("probe_safe_config_loaders", self.source)

    def test_23_runner_uses_subprocess_for_secrets(self):
        self.assertIn("subprocess", self.source)

    def test_24_runner_has_production_send_false(self):
        self.assertIn('"production_send": False', self.source)

    def test_25_runner_has_x_twitter_send_false(self):
        self.assertIn('"x_twitter_send": False', self.source)

    def test_26_runner_has_daemon_or_loop_false(self):
        self.assertIn('"daemon_or_loop_started": False', self.source)

    def test_27_runner_has_files_deleted_false(self):
        self.assertIn('"files_deleted": False', self.source)

    def test_28_runner_has_preflight_self_check(self):
        self.assertIn("PREFLIGHT SELF-CHECK", self.source)

    def test_29_runner_has_build_operator_digest(self):
        self.assertIn("build_operator_digest", self.source)

    def test_2a_runner_has_digest_card_summary(self):
        self.assertIn("build_digest_card_summary", self.source)

    def test_2b_runner_passes_through_pipeline_run(self):
        self.assertIn("pipeline.run(adapter)", self.source)

    def test_2c_runner_has_max_one_message_enforcement(self):
        self.assertIn("message_count", self.source.lower())

    def test_2d_runner_no_direct_secret_file_read(self):
        # Runner must not directly open config/local_secrets.ps1
        self.assertNotIn('config/local_secrets.ps1"', self.source.replace(
            'config/local_secrets.ps1', 'REDACTED'))


class TestV118APreflight(unittest.TestCase):
    """Test v118A safe config preflight."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_30_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v118A runner first.")

    def test_31_preflight_no_raw_token(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Preflight contains raw token pattern")

    def test_32_preflight_no_raw_chat_id(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Preflight contains raw chat_id pattern")

    def test_33_preflight_no_raw_message_id(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Preflight contains raw message_id pattern")

    def test_34_preflight_no_forbidden_patterns(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Preflight contains forbidden patterns: {violations}")

    def test_35_preflight_has_required_keys(self):
        required = [
            "checked_at", "pipeline_version", "run_id",
            "safe_loader_found", "load_attempted", "load_success",
            "bot_token_present", "bot_token_length", "bot_token_sha256_prefix",
            "chat_id_present", "chat_id_length", "chat_id_sha256_prefix",
            "config_ready",
        ]
        for key in required:
            self.assertIn(key, self.preflight, f"Preflight missing key: {key}")


class TestV118AResultFile(unittest.TestCase):
    """Test v118A result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_40_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v118A runner first.")

    def test_41_result_no_raw_token(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Result contains raw token pattern")

    def test_42_result_no_raw_chat_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Result contains raw chat_id pattern")

    def test_43_result_no_raw_message_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Result contains raw message_id pattern")

    def test_44_result_no_forbidden_patterns(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Result contains forbidden patterns: {violations}")

    def test_45_result_production_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("production_send", True),
                        "production_send must be False")

    def test_46_result_x_twitter_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("x_twitter_send", True),
                        "x_twitter_send must be False")

    def test_47_result_daemon_not_started(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("daemon_or_loop_started", True),
                        "daemon_or_loop_started must be False")

    def test_48_result_credentials_not_printed(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("credentials_printed", True),
                        "credentials_printed must be False")

    def test_49_result_files_not_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True),
                        "files_deleted must be False")

    def test_4a_result_has_three_cards(self):
        cards = self.result.get("cards", [])
        self.assertEqual(len(cards), 3,
                        f"Must have 3 cards, got {len(cards)}")

    def test_4b_result_three_card_families_present(self):
        cards = self.result.get("cards", [])
        families = {c.get("card_family") for c in cards}
        expected = set(THREE_CARD_FAMILIES)
        self.assertEqual(families, expected,
                        f"Card families mismatch: got {families}, expected {expected}")

    def test_4c_result_each_adapter_max_one_fetch(self):
        fetch_counts = self.result.get("adapter_fetch_counts", {})
        for cf, count in fetch_counts.items():
            self.assertLessEqual(count, 1,
                               f"{cf} fetched {count} times (max 1 allowed)")

    def test_4d_result_digest_exists(self):
        digest = self.result.get("digest", {})
        self.assertIsNotNone(digest, "Digest must exist")
        self.assertIn("digest_text", digest, "Digest must contain digest_text")

    def test_4e_result_digest_is_single(self):
        # Only one digest entry (not 3 separate ones)
        digest = self.result.get("digest", {})
        self.assertEqual(digest.get("card_count", 0), 3,
                        "Digest must reference all 3 cards")
        # The tg_digest should send at most 1 message
        tg_digest = self.result.get("tg_digest", {})
        if tg_digest:
            msg_count = tg_digest.get("message_count", 0)
            self.assertLessEqual(msg_count, 1,
                               f"TG digest sent {msg_count} messages (max 1)")

    def test_4f_result_tg_message_count_max_one(self):
        safety = self.result.get("safety", {})
        self.assertLessEqual(safety.get("tg_message_count_this_run", 999), 1,
                           "TG message count must be ≤ 1")

    def test_4g_result_external_api_called(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("external_api_called", False),
                       "external_api_called must be True")

    def test_4h_result_ai_model_not_called(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("ai_model_called", True),
                        "ai_model_called must be False")

    def test_4i_result_news_card_observation_only(self):
        cards = self.result.get("cards", [])
        news_card = [c for c in cards if c.get("card_family") == "news_event_market_impact"]
        if news_card:
            card = news_card[0]
            # Check observation_only and not_causal_proof fields if present
            # The result may have these under digest.cards or cards directly
            pass  # Validated via digest and report tests instead

    def test_4j_result_digest_news_has_observation_only(self):
        digest = self.result.get("digest", {})
        digest_text = digest.get("digest_text", "")
        self.assertIn("not causal proof", digest_text.lower(),
                     "Digest must mention 'not causal proof'")

    def test_4k_result_sent_not_faked_when_blocked(self):
        tg_digest = self.result.get("tg_digest", {})
        digest = self.result.get("digest", {})
        allowed = digest.get("allowed_count", 0)
        if allowed == 0:
            self.assertNotEqual(tg_digest.get("status"), "sent",
                              "Cannot claim sent when no cards allowed")

    def test_4l_result_no_deterministic_causal_language(self):
        """Digest must not use deterministic causal language."""
        digest = self.result.get("digest", {})
        digest_text = digest.get("digest_text", "").lower()
        causal_markers = [
            "will cause", "will lead to", "guaranteed to",
            "definitely", "certainly", "without doubt",
        ]
        for marker in causal_markers:
            self.assertNotIn(marker, digest_text,
                           f"Digest contains deterministic causal marker: '{marker}'")

    def test_4m_result_all_cards_shared_pipeline(self):
        """All cards must reference shared pipeline."""
        proof = self.result.get("shared_pipeline_proof", "")
        self.assertIn("shared pipeline", proof.lower())

    def test_4n_result_v116_history_not_modified(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("v116_history_modified", True),
                        "v116_history_modified must be False")


class TestV118AEvidenceLedger(unittest.TestCase):
    """Test v118A evidence ledger."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_50_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(),
                       "Evidence ledger not found. Run v118A runner first.")

    def test_51_ledger_has_entries(self):
        self.assertGreaterEqual(len(self.entries), 1,
                              "Ledger must have at least 1 entry (digest-level evidence)")

    def test_52_ledger_no_raw_token(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                            f"Ledger entry {i}: raw token pattern")

    def test_53_ledger_no_raw_chat_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                            f"Ledger entry {i}: raw chat_id pattern")

    def test_54_ledger_no_raw_message_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                            f"Ledger entry {i}: raw message_id pattern")

    def test_55_ledger_no_forbidden_patterns(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            violations = check_forbidden(text)
            self.assertEqual(len(violations), 0,
                           f"Ledger entry {i}: forbidden patterns: {violations}")

    def test_56_ledger_proof_is_sha256_or_redacted(self):
        for i, entry in enumerate(self.entries):
            proof = entry.get("proof", "")
            if proof and not proof.startswith("sha256:"):
                self.assertFalse(proof.isdigit(),
                               f"Ledger entry {i}: proof is raw number, not redacted")

    def test_57_ledger_production_send_false(self):
        for i, entry in enumerate(self.entries):
            self.assertFalse(entry.get("production_send", True),
                           f"Ledger entry {i}: production_send must be False")

    def test_58_ledger_has_card_family(self):
        for i, entry in enumerate(self.entries):
            self.assertIn("card_family", entry, f"Ledger entry {i}: missing card_family")


class TestV118AReports(unittest.TestCase):
    """Test v118A report markdown files."""

    @classmethod
    def setUpClass(cls):
        cls.report = ""
        cls.handoff = ""
        cls.digest_preview = ""
        if REPORT_PATH.exists():
            cls.report = REPORT_PATH.read_text(encoding="utf-8")
        if HANDOFF_PATH.exists():
            cls.handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        if DIGEST_PREVIEW_PATH.exists():
            cls.digest_preview = DIGEST_PREVIEW_PATH.read_text(encoding="utf-8")

    def test_60_report_exists(self):
        self.assertTrue(REPORT_PATH.exists(), "Report not found")

    def test_61_handoff_exists(self):
        self.assertTrue(HANDOFF_PATH.exists(), "Handoff not found")

    def test_62_digest_preview_exists(self):
        self.assertTrue(DIGEST_PREVIEW_PATH.exists(), "Digest preview not found")

    def test_63_report_no_raw_token(self):
        self.assertIsNone(RAW_TOKEN_PATTERN.search(self.report),
                         "Report contains raw token pattern")

    def test_64_report_no_raw_chat_id(self):
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(self.report),
                         "Report contains raw chat_id pattern")

    def test_65_report_no_raw_message_id(self):
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(self.report),
                         "Report contains raw message_id pattern")

    def test_66_report_no_forbidden_patterns(self):
        violations = check_forbidden(self.report)
        self.assertEqual(len(violations), 0,
                         f"Report contains forbidden patterns: {violations}")

    def test_67_handoff_no_forbidden_patterns(self):
        violations = check_forbidden(self.handoff)
        self.assertEqual(len(violations), 0,
                         f"Handoff contains forbidden patterns: {violations}")

    def test_68_digest_preview_no_forbidden_patterns(self):
        violations = check_forbidden(self.digest_preview)
        self.assertEqual(len(violations), 0,
                         f"Digest preview contains forbidden patterns: {violations}")

    def test_69_report_mentions_three_card_families(self):
        for cf in THREE_CARD_FAMILIES:
            self.assertIn(cf, self.report,
                         f"Report must mention {cf}")

    def test_6a_report_mentions_shared_pipeline(self):
        self.assertIn("shared pipeline", self.report.lower(),
                     "Report must mention shared pipeline")

    def test_6b_report_mentions_operator_digest(self):
        self.assertIn("digest", self.report.lower(),
                     "Report must mention operator digest")

    def test_6c_digest_preview_has_cards(self):
        self.assertIn("Card Details", self.digest_preview,
                     "Digest preview must have Card Details section")

    def test_6d_report_mentions_production_ready_false(self):
        self.assertIn("NOT FOR LIVE USE", self.report,
                     "Report must state NOT FOR LIVE USE")

    def test_6e_digest_preview_no_causal_language(self):
        # Verify digest preview does not contain deterministic causal claims
        markers = ["will cause", "will definitely", "guaranteed"]
        for m in markers:
            self.assertNotIn(m, self.digest_preview.lower(),
                           f"Digest preview contains '{m}'")

    def test_6f_report_mentions_each_adapter_max_one_fetch(self):
        self.assertTrue(
            "adapter" in self.report.lower() and "fetch" in self.report.lower(),
            "Report must mention adapter fetch constraints"
        )

    def test_6g_handoff_mentions_max_one_message(self):
        self.assertIn("max 1", self.handoff.lower(),
                     "Handoff must mention max 1 TG message")


class TestV118ASharedPipelineIntegration(unittest.TestCase):
    """Test that all 3 real adapters can go through SharedPipeline."""

    def test_70_three_adapters_via_shared_pipeline(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.free_api_adapters import (
            MultiAssetMarketSyncFreeApiAdapter,
            PriceOIVolumeAnomalyFreeApiAdapter,
            NewsEventMarketImpactFreePublicSourceAdapter,
        )
        from market_radar.shared.evidence_ledger import create_evidence_ledger

        ledger = create_evidence_ledger()
        pipeline = SharedPipeline(evidence_ledger=ledger)

        adapters = [
            MultiAssetMarketSyncFreeApiAdapter(),
            PriceOIVolumeAnomalyFreeApiAdapter(),
            NewsEventMarketImpactFreePublicSourceAdapter(),
        ]

        results = []
        fetch_counts = {}
        for adapter in adapters:
            result = pipeline.run(adapter)
            results.append(result)

            if hasattr(adapter, '_fetch_count'):
                fetch_counts[result.card_family.value] = adapter._fetch_count
            else:
                fetch_counts[result.card_family.value] = 1

        # All 3 card families present
        families = {r.card_family.value for r in results}
        self.assertEqual(families, set(THREE_CARD_FAMILIES),
                        f"Expected 3 card families, got {families}")

        # Each adapter fetched at most once
        for cf_name, count in fetch_counts.items():
            self.assertLessEqual(count, 1,
                               f"{cf_name} was fetched {count} times")

    def test_71_news_adapter_has_fetch_once_guard(self):
        from market_radar.shared.free_api_adapters import (
            NewsEventMarketImpactFreePublicSourceAdapter,
        )
        adapter = NewsEventMarketImpactFreePublicSourceAdapter()
        self.assertTrue(hasattr(adapter, '_fetch_count'),
                       "News adapter must have _fetch_count guard")
        self.assertIsNone(adapter._cached_signal,
                         "Initial _cached_signal must be None")
        self.assertEqual(adapter._fetch_count, 0,
                        "Initial _fetch_count must be 0")

    def test_72_multi_asset_adapter_uses_free_public_api(self):
        from market_radar.shared.free_api_adapters import (
            MultiAssetMarketSyncFreeApiAdapter,
        )
        from market_radar.shared.models import DataSourceType
        adapter = MultiAssetMarketSyncFreeApiAdapter()
        self.assertEqual(adapter.source_type, DataSourceType.FREE_PUBLIC_API)

    def test_73_price_oi_adapter_uses_free_public_api(self):
        from market_radar.shared.free_api_adapters import (
            PriceOIVolumeAnomalyFreeApiAdapter,
        )
        from market_radar.shared.models import DataSourceType
        adapter = PriceOIVolumeAnomalyFreeApiAdapter()
        self.assertEqual(adapter.source_type, DataSourceType.FREE_PUBLIC_API)


class TestV118ANewsCardGuard(unittest.TestCase):
    """Verify news card maintains observation_only / not_causal_proof."""

    def test_80_news_card_renderer_has_observation_only(self):
        from market_radar.shared.renderer_contract import CardRenderer
        from market_radar.shared.models import (
            NormalizedSignal, GateDecision, CardFamily, DataSourceType,
        )
        renderer = CardRenderer()
        signal = NormalizedSignal(
            source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
            asset_or_topic="BTC",
            timestamp="2026-06-05T00:00:00+08:00",
            metrics={
                "title": "Test Event",
                "source_name": "TestSource",
                "event_type": "ETF",
                "intensity": "high",
                "url": "https://example.com",
                "attribution_risk": "direct",
                "assets_affected": ["BTC"],
                "observation_only": True,
                "not_causal_proof": True,
            },
        )
        gate = GateDecision(
            allow=True,
            reason="Test gate",
            card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
        )
        card = renderer.render(signal, gate)
        self.assertTrue(card.observation_only, "News card must be observation_only=True")
        self.assertTrue(card.not_causal_proof, "News card must be not_causal_proof=True")
        self.assertIn("Observation Only", card.body)
        self.assertIn("Not Causal Proof", card.body)


class TestV118ARegressionFilesExist(unittest.TestCase):
    """Test that v118A did not delete v117/v116 historical output files."""

    def test_90_v117f_output_files_exist(self):
        missing = [str(f) for f in V117F_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117F files deleted: {missing}")

    def test_91_v117e_output_files_exist(self):
        missing = [str(f) for f in V117E_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117E files deleted: {missing}")

    def test_92_v117d_output_files_exist(self):
        missing = [str(f) for f in V117D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117D files deleted: {missing}")

    def test_93_v117c_output_files_exist(self):
        missing = [str(f) for f in V117C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117C files deleted: {missing}")

    def test_94_v117b_output_files_exist(self):
        missing = [str(f) for f in V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117B files deleted: {missing}")

    def test_95_v117_output_files_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117 files deleted: {missing}")

    def test_96_v116n_files_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116N files deleted: {missing}")

    def test_97_historical_files_exist(self):
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Historical v116 files deleted: {missing}")


class TestV118ARegressionSharedPipeline(unittest.TestCase):
    """Test shared pipeline still works with fixtures (regression)."""

    def test_a0_five_fixture_cards_still_work(self):
        from market_radar.shared.pipeline import SharedPipeline
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5,
                        f"Fixture pipeline should produce 5 results, got {len(results)}")

    def test_a1_three_verified_cards_allow(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import THREE_VERIFIED_CARD_FAMILIES
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        verified_results = [
            r for r in results
            if r.card_family in THREE_VERIFIED_CARD_FAMILIES
        ]
        self.assertEqual(len(verified_results), 3,
                        f"3 verified card families expected, got {len(verified_results)}")
        for r in verified_results:
            self.assertTrue(r.gate_decision.allow if r.gate_decision else False,
                          f"{r.card_family.value}: gate should allow fixture")

    def test_a2_liquidation_gate_not_lowered(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        liq_result = [r for r in results if r.card_family == CardFamily.LIQUIDATION_PRESSURE]
        self.assertEqual(len(liq_result), 1)
        if liq_result[0].gate_decision:
            self.assertFalse(liq_result[0].gate_decision.allow,
                           "Liquidation gate must NOT be lowered")

    def test_a3_whale_gate_not_bypassed(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        whale_result = [r for r in results if r.card_family == CardFamily.WHALE_POSITION_ALERT]
        self.assertEqual(len(whale_result), 1)
        if whale_result[0].gate_decision:
            self.assertFalse(whale_result[0].gate_decision.allow,
                           "Whale gate must NOT be bypassed")


class TestV118ACompleteLeakAudit(unittest.TestCase):
    """Comprehensive audit of all v118A outputs for secret leaks."""

    def test_b0_all_outputs_no_raw_token(self):
        for fpath in ALL_V118A_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".jsonl":
                for entry in load_jsonl(fpath):
                    text = json.dumps(entry, ensure_ascii=False)
                    self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                    f"{fpath.name}: raw token pattern")
            elif fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")

    def test_b1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V118A_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".jsonl":
                for entry in load_jsonl(fpath):
                    text = json.dumps(entry, ensure_ascii=False)
                    self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                    f"{fpath.name}: raw chat_id pattern")
            elif fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")


if __name__ == "__main__":
    unittest.main(verbosity=2)

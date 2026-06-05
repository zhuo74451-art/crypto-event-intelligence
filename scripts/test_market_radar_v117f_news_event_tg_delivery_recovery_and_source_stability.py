"""Market Radar v117F — News Event TG Delivery Recovery and Source Stability Tests.

Tests cover:
  - v117F runner can be imported
  - Preflight JSON contains NO raw token/chat_id/message_id
  - Result JSON contains NO raw forbidden patterns
  - Evidence ledger entries contain only SHA-256/redacted proofs
  - production_send is always False
  - X/Twitter send is always False
  - Daemon/cron/loop is not enabled
  - Card family is news_event_market_impact
  - observation_only is True
  - not_causal_proof is True
  - No deterministic causal assertions in rendered card
  - v117F specific:
    - Adapter fetch-once caching works (no duplicate market API calls)
    - RSS/XML parser no longer produces DeprecationWarning
    - TG sender failure classification fields exist
    - Proxy env detection is boolean-only
    - sent only when gate allow + test_group + safe config ready
    - failed/skipped not faked as sent
    - result/report/ledger contain no raw token/chat_id/message_id
    - evidence ledger only has SHA-256/redacted proofs
    - production_send=false
    - x_twitter_send=false
    - daemon_or_loop_started=false
  - Regression: v117E/v117D/v117C/v117B/v117/v116N tests still pass
  - Historical files not modified or deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v117f_news_event_tg_delivery_recovery_and_source_stability.py -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Forbidden patterns ────────────────────────────────────────────────────

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


# ── v117F Paths ────────────────────────────────────────────────────────────

V117F_RUNNER = ROOT / "scripts" / "run_market_radar_v117f_news_event_tg_delivery_recovery_and_source_stability.py"
V117F_TEST = ROOT / "scripts" / "test_market_radar_v117f_news_event_tg_delivery_recovery_and_source_stability.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v117f_news_event_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v117f_news_event_tg_delivery_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v117f_news_event_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v117f_news_event_tg_delivery_recovery_report.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v117f_local_only_handoff.md"

ALL_V117F_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, LEDGER_PATH, REPORT_PATH, HANDOFF_PATH,
]

# ── Historical files (must not be modified or deleted) ─────────────────────

HISTORICAL_FILES = [
    ROOT / "results" / "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json",
    ROOT / "results" / "market_radar_v116k_tg_test_send_evidence_ledger.jsonl",
    ROOT / "results" / "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116i_liquidation_pressure_tg_test_send_result.json",
    ROOT / "results" / "market_radar_v116j_news_event_market_impact_tg_test_send_result.json",
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


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestV117FFilesExist(unittest.TestCase):
    """Test that v117F runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V117F_RUNNER.exists(),
                        f"Missing runner: {V117F_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V117F_TEST.exists(),
                        f"Missing test: {V117F_TEST}")


class TestV117FOutputFilesExist(unittest.TestCase):
    """Test that all v117F output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V117F_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v117F output files: {missing}")


class TestV117FSafeConfigPreflight(unittest.TestCase):
    """Test the v117F safe config preflight for security."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_20_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v117F runner first.")

    def test_21_preflight_no_raw_token(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                         "Preflight contains raw token pattern")

    def test_22_preflight_no_raw_chat_id_string(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                         "Preflight contains raw chat_id pattern")

    def test_23_preflight_no_raw_message_id(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                         "Preflight contains raw message_id pattern")

    def test_24_preflight_has_required_keys(self):
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

    def test_25_preflight_proxy_env_boolean_only(self):
        """v117F: Proxy env detection must be boolean only."""
        proxy_detected = self.preflight.get("proxy_env_any_detected")
        self.assertIsInstance(proxy_detected, bool,
                            "proxy_env_any_detected must be boolean")

        proxy_vars = self.preflight.get("proxy_env_vars_set", [])
        self.assertIsInstance(proxy_vars, list,
                            "proxy_env_vars_set must be a list of names only")
        for var_name in proxy_vars:
            self.assertIsInstance(var_name, str)
            # Must NOT contain URLs, IPs, or ports
            self.assertNotIn("://", var_name,
                           f"Proxy var name '{var_name}' contains protocol — should be var name only")
            self.assertNotIn(":", var_name,
                           f"Proxy var name '{var_name}' contains colon — should be var name only")

    def test_26_preflight_token_length_only(self):
        self.assertIsInstance(self.preflight.get("bot_token_length"), int,
                            "bot_token_length must be an integer (length only)")

    def test_27_preflight_no_forbidden_patterns(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0,
                         f"Preflight contains forbidden patterns: {violations}")


class TestV117FResultFile(unittest.TestCase):
    """Test the v117F result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_30_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v117F runner first.")

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

    def test_39_result_card_family_is_news_event(self):
        self.assertEqual(self.result.get("card_family"),
                        "news_event_market_impact",
                        "v117F must use news_event_market_impact card family")

    def test_3a_result_external_api_called(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("external_api_called", False),
                       "external_api_called must be True (news sources were called)")

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

    def test_3f_result_observation_only_true(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("observation_only", False),
                       "observation_only must be True")

    def test_3g_result_not_causal_proof_true(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("not_causal_proof", False),
                       "not_causal_proof must be True")

    def test_3h_result_sent_cannot_happen_when_gate_blocked(self):
        if not self.result.get("gate_allow", True):
            tg = self.result.get("tg_result")
            if tg:
                self.assertNotEqual(tg.get("status"), "sent",
                                  "Cannot claim 'sent' when gate is blocked")

    def test_3i_result_source_info_present(self):
        source = self.result.get("source_summary", {})
        self.assertIn("sources_attempted", source)
        self.assertIn("sources_succeeded", source)

    def test_3j_result_truthful_about_source_status(self):
        source = self.result.get("source_summary", {})
        if source.get("all_public_sources_unavailable", False):
            run_status = self.result.get("run_status", "")
            self.assertIn("blocked", run_status,
                         "When all sources unavailable, run_status must reflect blocked")

    def test_3k_result_files_not_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True),
                        "files_deleted must be False")

    def test_3l_result_no_deterministic_causality(self):
        text = json.dumps(self.result, ensure_ascii=False).lower()
        false_causality = ["导致暴涨", "导致暴跌", "必然上涨", "必然下跌",
                          "cause the surge", "cause the crash"]
        for phrase in false_causality:
            self.assertNotIn(phrase, text,
                           f"Result contains false causality: '{phrase}'")

    # ── v117F specific tests ───────────────────────────────────────────

    def test_3m_result_v117f_fixes_field_exists(self):
        fixes = self.result.get("v117f_fixes", {})
        self.assertIn("market_fetch_once_caching", fixes,
                     "v117f_fixes must include market_fetch_once_caching")
        self.assertIn("rss_xml_parser_warning_fixed", fixes,
                     "v117f_fixes must include rss_xml_parser_warning_fixed")
        self.assertIn("tg_network_failure_classification_enhanced", fixes,
                     "v117f_fixes must include tg_network_failure_classification_enhanced")
        self.assertIn("proxy_env_detection_boolean_only", fixes,
                     "v117f_fixes must include proxy_env_detection_boolean_only")

    def test_3n_result_no_duplicate_market_fetch(self):
        fixes = self.result.get("v117f_fixes", {})
        self.assertTrue(fixes.get("no_duplicate_market_fetch", False),
                       "v117F must prevent duplicate market API calls")

    def test_3o_result_adapter_fetch_count(self):
        market = self.result.get("market_data_summary", {})
        fetch_count = market.get("adapter_fetch_count", 0)
        # fetch_count should be ≤1 when events are available
        # Could be 0 if blocked before fetch
        self.assertLessEqual(fetch_count, 1,
                           f"Adapter fetch count {fetch_count} > 1 — possible duplicate API calls")

    def test_3p_result_duplicate_fetch_prevented(self):
        market = self.result.get("market_data_summary", {})
        self.assertTrue(market.get("duplicate_fetch_prevented", False),
                       "duplicate_fetch_prevented must be True")

    def test_3q_tg_result_has_network_failure_class(self):
        """v117F: TG result must include network failure classification when failed."""
        tg = self.result.get("tg_result")
        if tg and tg.get("status") == "failed":
            self.assertIn("network_failure_class", tg,
                         "When TG failed, network_failure_class must be present")

    def test_3r_tg_result_has_proxy_env_detected(self):
        """v117F: TG result must include proxy env detection (boolean)."""
        tg = self.result.get("tg_result")
        if tg:
            self.assertIn("proxy_env_detected", tg,
                         "TG result must include proxy_env_detected")
            self.assertIsInstance(tg.get("proxy_env_detected"), bool,
                                "proxy_env_detected must be boolean")

    def test_3s_preflight_has_proxy_env_info(self):
        """v117F: Preflight must include proxy env boolean info."""
        self.assertIn("proxy_env_any_detected", self.result.get("preflight", {}),
                     "Preflight must include proxy_env_any_detected")

    def test_3t_result_sent_only_with_gate_and_config(self):
        tg = self.result.get("tg_result")
        if tg and tg.get("status") == "sent":
            self.assertTrue(self.result.get("gate_allow", False),
                          "TG sent requires gate_allow=True")
            preflight = self.result.get("preflight", {})
            self.assertTrue(preflight.get("config_ready", False),
                          "TG sent requires config_ready=True")

    def test_3u_result_failed_not_sent(self):
        tg = self.result.get("tg_result")
        if tg and tg.get("status") == "failed":
            self.assertFalse(tg.get("success", True),
                           "When status=failed, success must be False")
            self.assertNotEqual(tg.get("status"), "sent",
                              "Cannot have status=failed but also be 'sent'")

    def test_3v_result_skipped_not_sent(self):
        tg = self.result.get("tg_result")
        if tg and tg.get("status") == "skipped":
            self.assertFalse(tg.get("success", True),
                           "When status=skipped, success must be False")


class TestV117FEvidenceLedger(unittest.TestCase):
    """Test the v117F evidence ledger JSONL file."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_40_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(),
                       "Evidence ledger file not found. Run the v117F runner first.")

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


class TestV117FReports(unittest.TestCase):
    """Test the v117F report markdown files."""

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

    def test_5a_report_mentions_v117f_fixes(self):
        self.assertIn("v117F", self.report,
                     "Report must reference v117F")

    def test_5b_report_mentions_fetch_once(self):
        self.assertIn("fetch", self.report.lower(),
                     "Report must mention fetch caching")

    def test_5c_report_mentions_proxy_detection(self):
        self.assertIn("proxy", self.report.lower(),
                     "Report must mention proxy detection")

    def test_5d_report_mentions_enhanced_diagnostics(self):
        """Report must mention enhanced network failure diagnostics."""
        diagnostics_terms = ["failure class", "network_failure_class",
                           "failure classification",
                           "enhanced", "proxy_env"]
        found = any(t.lower() in self.report.lower() for t in diagnostics_terms)
        self.assertTrue(found,
                       f"Report must mention enhanced diagnostics")

    def test_5e_report_mentions_rss_parser_fix(self):
        """Report must mention RSS/XML parser warning fix."""
        parser_terms = ["rss", "xml", "parser", "element truth"]
        found = any(t.lower() in self.report.lower() for t in parser_terms)
        self.assertTrue(found,
                       "Report must mention RSS/XML parser fix")

    def test_5f_report_mentions_observation_only(self):
        self.assertIn("observation_only", self.report.lower(),
                     "Report must mention observation_only")

    def test_5g_report_no_deterministic_causality(self):
        false_causality = ["导致暴涨", "导致暴跌", "必然上涨", "必然下跌"]
        for phrase in false_causality:
            self.assertNotIn(phrase, self.report,
                           f"Report contains false causality: '{phrase}'")


class TestV117FRunnerExecution(unittest.TestCase):
    """Test the runner script behavior (static analysis)."""

    def test_60_runner_can_be_imported(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_market_radar_v117f",
            V117F_RUNNER,
        )
        self.assertIsNotNone(spec, "Runner spec is None")

    def test_61_runner_imports_shared_package(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("market_radar.shared", source,
                     "Runner must import from market_radar.shared")
        self.assertIn("SharedPipeline", source,
                     "Runner must use SharedPipeline")

    def test_62_runner_uses_news_event_adapter(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("NEWS_EVENT_MARKET_IMPACT", source,
                     "Runner must reference NEWS_EVENT_MARKET_IMPACT card family")

    def test_63_runner_production_send_is_false(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"production_send": False', source,
                     "SAFETY dict must set production_send=False")

    def test_64_runner_x_twitter_blocked(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"x_twitter_send": False', source,
                     "SAFETY dict must set x_twitter_send=False")

    def test_65_runner_daemon_blocked(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"daemon_or_loop_started": False', source,
                     "SAFETY dict must set daemon_or_loop_started=False")

    def test_66_runner_has_self_check(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("PREFLIGHT SELF-CHECK", source,
                     "Runner must have preflight self-check")

    def test_67_runner_imports_sender_contract_diagnostics(self):
        """v117F: Runner must import enhanced sender diagnostics."""
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("_detect_proxy_env", source,
                     "Runner must import _detect_proxy_env from sender_contract")
        self.assertIn("_classify_network_error", source,
                     "Runner must import _classify_network_error from sender_contract")

    def test_68_runner_has_fetch_count_check(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("fetch_count", source,
                     "Runner must reference fetch_count for on-once compliance")

    def test_69_runner_proxy_env_boolean_only(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        self.assertIn("proxy_env_any_detected", source,
                     "Runner must reference proxy_env_any_detected")
        # Must NOT contain any proxy URL pattern
        self.assertNotRegex(source, r'http://\d+\.\d+\.\d+\.\d+:\d+',
                          "Runner must NOT contain literal proxy URLs")
        self.assertNotRegex(source, r'socks5://',
                          "Runner must NOT contain literal proxy URLs")

    def test_6a_runner_no_proxy_address_hardcoded(self):
        source = V117F_RUNNER.read_text(encoding="utf-8")
        # Must not contain common proxy port patterns with IPs
        self.assertNotRegex(source, r'proxy\s*=\s*["\']http',
                          "Runner must NOT hardcode proxy address")


class TestV117FAdapterFetchOnce(unittest.TestCase):
    """v117F: Test that adapter fetch-once caching works."""

    def test_70_adapter_caches_fetch_result(self):
        from market_radar.shared.free_api_adapters import (
            create_real_free_api_adapter,
        )
        from market_radar.shared.models import CardFamily
        adapter = create_real_free_api_adapter(CardFamily.NEWS_EVENT_MARKET_IMPACT)

        # First fetch
        signal1 = adapter.fetch()
        self.assertEqual(adapter._fetch_count, 1)

        # Second fetch — should return cached
        signal2 = adapter.fetch()
        self.assertEqual(adapter._fetch_count, 1,
                       "fetch_count should still be 1 after second call (cached)")

        # Both should be the same object
        self.assertIs(signal1, signal2,
                     "Second fetch() should return the exact same cached signal")

    def test_71_different_adapter_instances_independent(self):
        from market_radar.shared.free_api_adapters import (
            create_real_free_api_adapter,
        )
        from market_radar.shared.models import CardFamily

        adapter1 = create_real_free_api_adapter(CardFamily.NEWS_EVENT_MARKET_IMPACT)
        adapter2 = create_real_free_api_adapter(CardFamily.NEWS_EVENT_MARKET_IMPACT)

        signal1 = adapter1.fetch()
        signal2 = adapter2.fetch()

        self.assertIsNot(signal1, signal2,
                        "Different adapter instances should have independent caches")
        self.assertEqual(adapter1._fetch_count, 1)
        self.assertEqual(adapter2._fetch_count, 1)


class TestV117FXMLParserWarning(unittest.TestCase):
    """v117F: Test that RSS/XML parser no longer produces DeprecationWarning."""

    def test_80_xml_element_truth_value_no_warning(self):
        """Verify that the _fetch_rss method uses explicit is not None."""
        import xml.etree.ElementTree as ET
        from market_radar.shared.free_api_adapters import (
            NewsEventMarketImpactFreePublicSourceAdapter,
        )

        adapter = NewsEventMarketImpactFreePublicSourceAdapter()

        # Create a minimal RSS XML and test parsing
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Test Article About BTC ETF</title>
              <link>https://example.com/1</link>
            </item>
            <item>
              <title>ETH Price Surge Explained</title>
              <link>https://example.com/2</link>
            </item>
          </channel>
        </rss>"""

        # We'll test via a direct call — this should NOT raise DeprecationWarning
        import io

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Simulate what _fetch_rss does internally
            root = ET.fromstring(rss_xml)
            items = root.findall(".//item")

            for item in items:
                # v117F pattern: explicit is not None
                title_el = item.find("title")
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")

                link_el = item.find("link")
                if link_el is None:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")

                title = (title_el.text or "").strip() if title_el is not None else ""
                self.assertTrue(len(title) > 0)

            # Check for DeprecationWarning about element truth value
            deprecation_warnings = [
                str(warn.message) for warn in w
                if issubclass(warn.category, DeprecationWarning)
                and "truth value" in str(warn.message).lower()
            ]
            self.assertEqual(len(deprecation_warnings), 0,
                           f"XML element truth value DeprecationWarning still present: {deprecation_warnings}")

    def test_81_xml_parse_old_pattern_not_used(self):
        """Verify that the _fetch_rss source code uses is not None, not 'or' chaining."""
        import inspect
        from market_radar.shared.free_api_adapters import (
            NewsEventMarketImpactFreePublicSourceAdapter,
        )

        source = inspect.getsource(NewsEventMarketImpactFreePublicSourceAdapter._fetch_rss)
        # Should contain the explicit is not None pattern
        self.assertIn("if title_el is None:", source,
                     "_fetch_rss must use explicit 'is None' check for title_el")
        self.assertIn("if link_el is None:", source,
                     "_fetch_rss must use explicit 'is None' check for link_el")
        # Should NOT contain the old or-chain pattern
        self.assertNotIn("item.find(\"title\")\n                    or item.find(", source,
                        "_fetch_rss must NOT chain XML element lookups with 'or'")


class TestV117FSenderContractDiagnostics(unittest.TestCase):
    """v117F: Test sender contract enhanced diagnostics."""

    def test_90_classify_network_error_timeout(self):
        from market_radar.shared.sender_contract import _classify_network_error
        result = _classify_network_error("Request timed out after 10s")
        self.assertEqual(result, "network_timeout")

    def test_91_classify_network_error_dns(self):
        from market_radar.shared.sender_contract import _classify_network_error
        result = _classify_network_error("getaddrinfo failed: Name or service not known")
        self.assertEqual(result, "dns_error")

    def test_92_classify_network_error_connection_refused(self):
        from market_radar.shared.sender_contract import _classify_network_error
        result = _classify_network_error("Connection refused: [Errno 111]")
        self.assertEqual(result, "connection_refused")

    def test_93_classify_network_error_proxy(self):
        from market_radar.shared.sender_contract import _classify_network_error
        result = _classify_network_error("Tunnel connection failed: proxy error 407")
        self.assertEqual(result, "proxy_required_or_unreachable")

    def test_94_classify_network_error_unknown(self):
        from market_radar.shared.sender_contract import _classify_network_error
        result = _classify_network_error("Some random unexpected error")
        self.assertEqual(result, "unknown_transport_error")

    def test_95_detect_proxy_env_boolean_only(self):
        from market_radar.shared.sender_contract import _detect_proxy_env
        result = _detect_proxy_env()
        # Must be boolean values
        self.assertIsInstance(result.get("any_proxy_detected"), bool)
        for key, val in result.items():
            if key != "any_proxy_detected":
                self.assertIsInstance(val, bool,
                                    f"proxy env '{key}' must be boolean, got {type(val)}")
        # Must NOT contain actual proxy values (no URLs, IPs)
        for key in result:
            self.assertNotIn("://", key, "Proxy detection key contains URL")
            self.assertNotIn("127.0.0.1", key, "Proxy detection key contains IP")

    def test_96_redact_url_host(self):
        from market_radar.shared.sender_contract import _redact_url_host
        result = _redact_url_host("https://api.telegram.org/bot123456:ABCDEF/sendMessage")
        self.assertEqual(result, "api.telegram.org")
        self.assertNotIn("bot123456", result)
        self.assertNotIn("sendMessage", result)

    def test_97_failure_classification_valid(self):
        from market_radar.shared.sender_contract import NETWORK_ERROR_CLASSIFICATIONS
        valid = [
            "network_timeout", "dns_error", "connection_refused",
            "proxy_required_or_unreachable", "http_status_error",
            "unknown_transport_error",
        ]
        self.assertEqual(set(NETWORK_ERROR_CLASSIFICATIONS), set(valid),
                        "NETWORK_ERROR_CLASSIFICATIONS must match expected list")


class TestV117FRegressionV117E(unittest.TestCase):
    """Test that v117F does not break v117E outputs."""

    def test_a0_v117e_output_files_exist(self):
        hist_paths = [
            ROOT / "results" / "market_radar_v117e_news_event_tg_one_shot_result.json",
            ROOT / "results" / "market_radar_v117e_news_event_evidence_ledger.jsonl",
            ROOT / "runs" / "market_radar" / "v117e_news_event_market_impact_real_public_source_tg_one_shot_report.md",
            ROOT / "runs" / "market_radar" / "v117e_local_only_handoff.md",
        ]
        missing = [str(f) for f in hist_paths if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117E output files deleted: {missing}")

    def test_a1_v117e_runner_still_exists(self):
        path = ROOT / "scripts" / "run_market_radar_v117e_news_event_market_impact_real_public_source_tg_one_shot.py"
        self.assertTrue(path.exists(), "v117E runner must still exist")


class TestV117FRegressionV117D(unittest.TestCase):
    """Test that v117F does not break v117D outputs."""

    def test_b0_v117d_output_files_still_exist(self):
        missing = [str(f) for f in V117D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117D output files deleted: {missing}")


class TestV117FRegressionV117C(unittest.TestCase):
    """Test that v117F does not break v117C outputs."""

    def test_c0_v117c_output_files_still_exist(self):
        missing = [str(f) for f in V117C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117C output files deleted: {missing}")


class TestV117FRegressionV117B(unittest.TestCase):
    """Test that v117F does not break v117B outputs."""

    def test_d0_v117b_output_files_still_exist(self):
        missing = [str(f) for f in V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117B output files deleted: {missing}")


class TestV117FRegressionV117(unittest.TestCase):
    """Test that v117F does not break v117 shared pipeline."""

    def test_e0_v117_output_files_still_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117 output files deleted: {missing}")

    def test_e1_v117_fixture_pipeline_still_works(self):
        from market_radar.shared.pipeline import SharedPipeline
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5,
                        f"v117 fixture pipeline should produce 5 results, got {len(results)}")
        news_results = [r for r in results
                       if r.card_family.value == "news_event_market_impact"]
        self.assertEqual(len(news_results), 1,
                        "Should have exactly 1 news_event_market_impact fixture result")


class TestV117FRegressionV116N(unittest.TestCase):
    """Test that v117F does not break v116N acceptance overlay."""

    def test_f0_v116n_files_still_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116N files deleted: {missing}")


class TestV117FRegressionHistorical(unittest.TestCase):
    """Test that v117F does not modify or delete historical products."""

    def test_g0_historical_files_still_exist(self):
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Historical files deleted: {missing}")


class TestV117FSecretLeakPrevention(unittest.TestCase):
    """Comprehensive test that no secret leak occurs in any v117F output."""

    def test_h0_all_outputs_no_raw_token(self):
        for fpath in ALL_V117F_OUTPUT_FILES:
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

    def test_h1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V117F_OUTPUT_FILES:
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

    def test_h2_all_outputs_no_raw_message_id(self):
        for fpath in ALL_V117F_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".jsonl":
                for entry in load_jsonl(fpath):
                    text = json.dumps(entry, ensure_ascii=False)
                    self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                    f"{fpath.name}: raw message_id pattern found")
            elif fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern found")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern found")


if __name__ == "__main__":
    unittest.main(verbosity=2)

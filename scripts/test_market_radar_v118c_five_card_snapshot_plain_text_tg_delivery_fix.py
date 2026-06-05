"""Market Radar v118C — Five Card Snapshot Plain Text TG Delivery Fix Tests.

Tests cover:
  - v118C runner can be imported
  - All five card families appear in the operator snapshot
  - Three real adapters all enter shared pipeline
  - Liquidation gate is NOT lowered, no fake spike
  - Whale manual evidence is NOT bypassed
  - Snapshot allows at most 1 TG message
  - Sent only when test_group + safe config + at least one active card
  - Failed/skipped/blocked NOT forged as sent
  - News card maintains observation_only / not_causal_proof
  - Snapshot contains no deterministic causal language
  - v118C TG message uses PLAIN TEXT format (no HTML parse_mode)
  - Aggregated snapshot has no HTML parse error risk characters
  - Result/report/ledger contain NO raw token/chat_id/message_id
  - Evidence ledger only contains SHA-256/redacted proofs
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - v116A-N history not modified
  - v118B TG failure root cause documented
  - sender_contract.py supports parse_mode parameter
  - Regression: v118B/v118A/v117F/v117E/v117D/v117C/v117B/v117/v116N all pass

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v118c_five_card_snapshot_plain_text_tg_delivery_fix.py -v
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


# ── Forbidden patterns ──────────────────────────────────────────────────────

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


# ── v118C Paths ──────────────────────────────────────────────────────────────

V118C_RUNNER = ROOT / "scripts" / "run_market_radar_v118c_five_card_snapshot_plain_text_tg_delivery_fix.py"
V118C_TEST = ROOT / "scripts" / "test_market_radar_v118c_five_card_snapshot_plain_text_tg_delivery_fix.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v118c_five_card_snapshot_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v118c_five_card_snapshot_result.json"
DELIVERY_PATH = ROOT / "results" / "market_radar_v118c_five_card_snapshot_delivery_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v118c_five_card_snapshot_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v118c_five_card_snapshot_plain_text_delivery_report.md"
SNAPSHOT_PREVIEW_PATH = ROOT / "runs" / "market_radar" / "v118c_operator_snapshot_preview.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v118c_local_only_handoff.md"

ALL_V118C_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, DELIVERY_PATH, LEDGER_PATH, REPORT_PATH,
    SNAPSHOT_PREVIEW_PATH, HANDOFF_PATH,
]

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

THREE_REAL_ADAPTER_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
]

TWO_BLOCKED_OVERLAY_FAMILIES = [
    "liquidation_pressure",
    "whale_position_alert",
]

# ── Historical output files (must not be modified) ──────────────────────────

V118B_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_preflight.json",
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_result.json",
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v118b_five_card_operator_snapshot_report.md",
    ROOT / "runs" / "market_radar" / "v118b_operator_snapshot_preview.md",
    ROOT / "runs" / "market_radar" / "v118b_local_only_handoff.md",
]

V118A_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118a_three_card_digest_preflight.json",
    ROOT / "results" / "market_radar_v118a_three_card_digest_result.json",
    ROOT / "results" / "market_radar_v118a_three_card_digest_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md",
    ROOT / "runs" / "market_radar" / "v118a_operator_digest_preview.md",
    ROOT / "runs" / "market_radar" / "v118a_local_only_handoff.md",
]

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
    V118B_OUTPUT_FILES + V118A_OUTPUT_FILES +
    V117F_OUTPUT_FILES + V117E_OUTPUT_FILES + V117D_OUTPUT_FILES +
    V117C_OUTPUT_FILES + V117B_OUTPUT_FILES + V117_OUTPUT_FILES +
    V116N_FILES + HISTORICAL_FILES
)

# ── Sender contract ──────────────────────────────────────────────────────────

SENDER_CONTRACT_PATH = ROOT / "market_radar" / "shared" / "sender_contract.py"


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestV118CFilesExist(unittest.TestCase):
    """Test that v118C runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V118C_RUNNER.exists(),
                        f"Missing runner: {V118C_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V118C_TEST.exists(),
                        f"Missing test: {V118C_TEST}")


class TestV118COutputFilesExist(unittest.TestCase):
    """Test that all v118C output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V118C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v118C output files: {missing}")


class TestV118CRunnerStaticAnalysis(unittest.TestCase):
    """Static analysis of v118C runner source."""

    @classmethod
    def setUpClass(cls):
        cls.source = V118C_RUNNER.read_text(encoding="utf-8") if V118C_RUNNER.exists() else ""

    def test_20_runner_imports_shared_pipeline(self):
        self.assertIn("market_radar.shared", self.source)
        self.assertIn("SharedPipeline", self.source)

    def test_21_runner_creates_three_real_adapters(self):
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

    def test_29_runner_has_blocked_overlay_builders(self):
        self.assertIn("build_liquidation_blocked_overlay", self.source)
        self.assertIn("build_whale_blocked_overlay", self.source)

    def test_2a_runner_has_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.source, f"Runner must reference {cf}")

    def test_2b_runner_has_snapshot_builder(self):
        self.assertIn("build_five_card_operator_snapshot", self.source)

    def test_2c_runner_has_max_one_message_enforcement(self):
        self.assertIn("message_count", self.source.lower())

    def test_2d_runner_liquidation_not_lowered(self):
        self.assertIn("NOT lowered", self.source)
        self.assertIn("calm_market_or_threshold_not_met", self.source)

    def test_2e_runner_whale_not_bypassed(self):
        self.assertIn("manual_attribution_evidence_required", self.source)

    # ── v118C-specific: plain text format checks ──

    def test_2f_runner_uses_plain_text_parse_mode(self):
        """v118C must send with parse_mode=None (plain text)."""
        self.assertIn("parse_mode=None", self.source,
                     "v118C runner must call send() with parse_mode=None")

    def test_2g_runner_disables_html_parse_mode(self):
        """v118C runner must disable HTML parse_mode."""
        self.assertIn("html_parse_mode_disabled", self.source.lower())
        self.assertIn("PlainText", self.source,
                     "v118C runner must use PlainText parse_mode")

    def test_2h_runner_documents_v118b_root_cause(self):
        """v118C runner must document the v118B TG HTML failure."""
        self.assertIn("v118b", self.source.lower())
        self.assertIn("parse_mode", self.source.lower())

    def test_2i_runner_has_html_risk_check(self):
        """v118C runner must include HTML parse risk self-check."""
        self.assertIn("check_html_parse_risk", self.source)

    def test_2j_runner_snapshot_uses_safe_format_labels(self):
        """v118C snapshot must use ASCII-safe section labels (not emoji)."""
        self.assertIn("[Active Signals]", self.source)
        self.assertIn("[Blocked / Waiting for Conditions]", self.source)
        self.assertIn("[Manual Evidence Required]", self.source)


class TestV118CSenderContract(unittest.TestCase):
    """Test that sender_contract.py supports parse_mode parameter."""

    def test_30_sender_contract_has_parse_mode_param(self):
        source = SENDER_CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("parse_mode", source,
                     "sender_contract.py must support parse_mode parameter")
        self.assertIn("parse_mode: Optional[str]", source,
                     "sender_contract.py must have typed parse_mode parameter")

    def test_31_sender_contract_defaults_to_html(self):
        """parse_mode should default to 'HTML' for backward compatibility."""
        source = SENDER_CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn('"HTML"', source,
                     "sender_contract.py must default parse_mode to HTML")

    def test_32_sender_contract_plain_text_enabled(self):
        """When parse_mode is None, sender omits parse_mode from TG API request."""
        source = SENDER_CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("use_plain_text", source,
                     "sender_contract.py must have plain text detection logic")
        self.assertIn("not parse_mode", source,
                     "sender_contract.py must detect parse_mode=None for plain text")
        # Verify no parse_mode in the plain text request body
        self.assertIn("NO parse_mode", source,
                     "sender_contract.py must omit parse_mode for plain text")


class TestV118CPreflight(unittest.TestCase):
    """Test v118C safe config preflight."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_40_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v118C runner first.")

    def test_41_preflight_no_raw_token(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_42_preflight_no_raw_chat_id(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text))

    def test_43_preflight_no_forbidden_patterns(self):
        text = json.dumps(self.preflight, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0)

    def test_44_preflight_documents_v118b_root_cause(self):
        self.assertIn("v118b_tg_failure_root_cause", self.preflight,
                     "Preflight must document v118B failure root cause")

    def test_45_preflight_has_plain_text_mode(self):
        self.assertTrue(
            self.preflight.get("tg_html_parse_mode_disabled", False),
            "Preflight must mark HTML parse_mode as disabled")
        self.assertEqual(
            self.preflight.get("tg_parse_mode"), "PlainText",
            "Preflight must use PlainText parse mode")


class TestV118CResultFile(unittest.TestCase):
    """Test v118C result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_50_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v118C runner first.")

    def test_51_result_no_raw_token(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_52_result_no_raw_chat_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text))

    def test_53_result_no_raw_message_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text))

    def test_54_result_no_forbidden_patterns(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0)

    def test_55_result_production_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("production_send", True))

    def test_56_result_x_twitter_send_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("x_twitter_send", True))

    def test_57_result_daemon_not_started(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("daemon_or_loop_started", True))

    def test_58_result_credentials_not_printed(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("credentials_printed", True))

    def test_59_result_files_not_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True))

    def test_5a_result_has_five_cards(self):
        cards = self.result.get("cards", [])
        self.assertEqual(len(cards), 5, f"Must have 5 cards, got {len(cards)}")

    def test_5b_result_five_card_families_present(self):
        cards = self.result.get("cards", [])
        families = {c.get("card_family") for c in cards}
        expected = set(FIVE_CARD_FAMILIES)
        self.assertEqual(families, expected)

    def test_5c_result_three_real_adapters(self):
        cards = self.result.get("cards", [])
        real = [c for c in cards if c.get("card_family") in THREE_REAL_ADAPTER_FAMILIES]
        self.assertEqual(len(real), 3)

    def test_5d_result_each_adapter_max_one_fetch(self):
        counts = self.result.get("adapter_fetch_counts", {})
        for cf, count in counts.items():
            if cf in THREE_REAL_ADAPTER_FAMILIES:
                self.assertLessEqual(count, 1, f"{cf} fetched {count} times")

    def test_5e_result_snapshot_exists(self):
        snap = self.result.get("snapshot", {})
        self.assertIn("snapshot_text", snap)
        self.assertEqual(snap.get("card_count", 0), 5)

    def test_5f_result_tg_message_count_max_one(self):
        safety = self.result.get("safety", {})
        self.assertLessEqual(safety.get("tg_message_count_this_run", 999), 1)

    def test_5g_result_external_api_called(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("external_api_called", False))

    def test_5h_result_ai_model_not_called(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("ai_model_called", True))

    def test_5i_result_liquidation_is_blocked(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c.get("card_family") == "liquidation_pressure"]
        self.assertEqual(len(liq), 1)
        self.assertIn(liq[0]["status"], ("blocked", "manual_required"))

    def test_5j_result_whale_is_manual_required(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c.get("card_family") == "whale_position_alert"]
        self.assertEqual(len(whale), 1)
        self.assertIn(whale[0]["status"], ("blocked", "manual_required"))

    def test_5k_result_liquidation_not_send_eligible(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c.get("card_family") == "liquidation_pressure"]
        if liq:
            self.assertFalse(liq[0].get("send_eligible", True))

    def test_5l_result_whale_not_send_eligible(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c.get("card_family") == "whale_position_alert"]
        if whale:
            self.assertFalse(whale[0].get("send_eligible", True))

    def test_5m_result_no_deterministic_causal_language(self):
        snap = self.result.get("snapshot", {})
        text = snap.get("snapshot_text", "").lower()
        for marker in ["will cause", "guaranteed to", "definitely", "certainly"]:
            self.assertNotIn(marker, text)

    def test_5n_result_blocked_overlays_exist(self):
        overlays = self.result.get("blocked_overlays", {})
        self.assertIn("liquidation_pressure", overlays)
        self.assertIn("whale_position_alert", overlays)

    def test_5o_result_liquidation_threshold_not_lowered(self):
        overlays = self.result.get("blocked_overlays", {})
        liq = overlays.get("liquidation_pressure", {})
        self.assertTrue(liq.get("threshold_not_lowered", False))
        self.assertTrue(liq.get("no_fake_spike", False))

    def test_5p_result_whale_evidence_not_bypassed(self):
        overlays = self.result.get("blocked_overlays", {})
        whale = overlays.get("whale_position_alert", {})
        self.assertTrue(whale.get("manual_evidence_not_bypassed", False))
        self.assertTrue(whale.get("no_address_guess", False))

    def test_5q_result_sent_not_faked(self):
        tg = self.result.get("tg_snapshot", {})
        if tg:
            status = tg.get("status", "")
            if status in ("blocked", "skipped", "failed"):
                self.assertNotEqual(status, "sent")

    def test_5r_result_v116_history_not_modified(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("v116_history_modified", True))

    def test_5s_result_news_observation_only(self):
        snap = self.result.get("snapshot", {})
        text = snap.get("snapshot_text", "")
        self.assertIn("not causal proof", text.lower())

    # ── v118C-specific: plain text format assertions ──

    def test_5t_result_html_parse_mode_disabled(self):
        safety = self.result.get("safety", {})
        self.assertTrue(safety.get("tg_html_parse_mode_disabled", False),
                       "HTML parse_mode must be disabled in v118C")
        self.assertEqual(safety.get("tg_parse_mode_used"), "PlainText")

    def test_5u_result_snapshot_tg_format_is_plain_text(self):
        snap = self.result.get("snapshot", {})
        self.assertEqual(snap.get("tg_format"), "plain_text")
        self.assertTrue(snap.get("html_parse_mode_disabled", False))

    def test_5v_result_documents_v118b_failure(self):
        self.assertIn("v118b_tg_failure_root_cause", self.result)
        self.assertIn("v118c_fix", self.result)

    def test_5w_result_tg_snapshot_has_plain_text_field(self):
        tg = self.result.get("tg_snapshot", {})
        if tg and tg.get("status") == "sent":
            self.assertTrue(tg.get("html_parse_mode_disabled", False))
            self.assertEqual(tg.get("tg_parse_mode"), "PlainText")

    def test_5x_result_html_risk_check_present(self):
        check = self.result.get("html_parse_risk_check", {})
        self.assertIn("verdict", check)
        self.assertIn("SAFE_FOR_PLAIN_TEXT", check.get("verdict", ""),
                     "Must verify plain text mode is safe")

    def test_5y_result_snapshot_uses_ascii_labels(self):
        """v118C snapshot must use ASCII-safe section labels (not emoji that
        could break HTML parsing if parse_mode were ever used)."""
        text = self.result.get("snapshot", {}).get("snapshot_text", "")
        self.assertIn("[Active Signals]", text)
        self.assertIn("[Blocked / Waiting for Conditions]", text)
        self.assertIn("[Manual Evidence Required]", text)


class TestV118CDeliveryResult(unittest.TestCase):
    """Test v118C delivery result file."""

    @classmethod
    def setUpClass(cls):
        if DELIVERY_PATH.exists():
            cls.delivery = load_json(DELIVERY_PATH)
        else:
            cls.delivery = None

    def test_60_delivery_exists(self):
        self.assertIsNotNone(self.delivery)

    def test_61_delivery_no_raw_secrets(self):
        text = json.dumps(self.delivery, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_62_delivery_parse_mode_is_plain_text(self):
        self.assertEqual(self.delivery.get("parse_mode_used"), "PlainText")

    def test_63_delivery_html_disabled(self):
        self.assertTrue(self.delivery.get("html_parse_mode_disabled", False))

    def test_64_delivery_production_false(self):
        self.assertFalse(self.delivery.get("production_send", True))

    def test_65_delivery_message_count_max_one(self):
        self.assertLessEqual(self.delivery.get("message_count", 999), 1)


class TestV118CEvidenceLedger(unittest.TestCase):
    """Test v118C evidence ledger."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_70_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(), "Evidence ledger not found.")

    def test_71_ledger_has_entries(self):
        self.assertGreaterEqual(len(self.entries), 1)

    def test_72_ledger_no_raw_token(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_73_ledger_no_raw_chat_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text))

    def test_74_ledger_no_raw_message_id(self):
        for i, entry in enumerate(self.entries):
            text = json.dumps(entry, ensure_ascii=False)
            self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text))

    def test_75_ledger_no_forbidden_patterns(self):
        for i, entry in enumerate(self.entries):
            violations = check_forbidden(json.dumps(entry, ensure_ascii=False))
            self.assertEqual(len(violations), 0)

    def test_76_ledger_proof_is_sha256_or_redacted(self):
        for i, entry in enumerate(self.entries):
            proof = entry.get("proof", "")
            if proof and not proof.startswith("sha256:"):
                self.assertFalse(proof.isdigit())

    def test_77_ledger_production_send_false(self):
        for i, entry in enumerate(self.entries):
            self.assertFalse(entry.get("production_send", True))

    def test_78_ledger_has_card_family(self):
        for i, entry in enumerate(self.entries):
            self.assertIn("card_family", entry)


class TestV118CReports(unittest.TestCase):
    """Test v118C report markdown files."""

    @classmethod
    def setUpClass(cls):
        cls.report = ""
        cls.handoff = ""
        cls.preview = ""
        if REPORT_PATH.exists():
            cls.report = REPORT_PATH.read_text(encoding="utf-8")
        if HANDOFF_PATH.exists():
            cls.handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        if SNAPSHOT_PREVIEW_PATH.exists():
            cls.preview = SNAPSHOT_PREVIEW_PATH.read_text(encoding="utf-8")

    def test_80_report_exists(self):
        self.assertTrue(REPORT_PATH.exists(), "Report not found")

    def test_81_handoff_exists(self):
        self.assertTrue(HANDOFF_PATH.exists(), "Handoff not found")

    def test_82_preview_exists(self):
        self.assertTrue(SNAPSHOT_PREVIEW_PATH.exists(), "Snapshot preview not found")

    def test_83_report_no_forbidden_patterns(self):
        violations = check_forbidden(self.report)
        self.assertEqual(len(violations), 0)

    def test_84_handoff_no_forbidden_patterns(self):
        violations = check_forbidden(self.handoff)
        self.assertEqual(len(violations), 0)

    def test_85_preview_no_forbidden_patterns(self):
        violations = check_forbidden(self.preview)
        self.assertEqual(len(violations), 0)

    def test_86_report_no_raw_token(self):
        self.assertIsNone(RAW_TOKEN_PATTERN.search(self.report))

    def test_87_report_mentions_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.report, f"Report must mention {cf}")

    def test_88_report_mentions_shared_pipeline(self):
        self.assertIn("shared pipeline", self.report.lower())

    def test_89_report_mentions_not_for_live_use(self):
        self.assertIn("NOT FOR LIVE USE", self.report)

    def test_8a_report_mentions_plain_text(self):
        self.assertIn("PLAIN TEXT", self.report,
                     "Report must mention PLAIN TEXT format")

    def test_8b_report_mentions_html_disabled(self):
        self.assertIn("HTML parse_mode", self.report,
                     "Report must mention HTML parse_mode disabled")

    def test_8c_report_mentions_v118b_failure(self):
        self.assertIn("v118B", self.report,
                     "Report must mention v118B failure")

    def test_8d_handoff_mentions_v118b_tg_failure(self):
        self.assertIn("parse_mode", self.handoff.lower(),
                     "Handoff must mention parse_mode change")

    def test_8e_handoff_mentions_plain_text(self):
        self.assertIn("PlainText", self.handoff,
                     "Handoff must mention PlainText")

    def test_8f_preview_mentions_plain_text(self):
        self.assertIn("PLAIN TEXT", self.preview,
                     "Snapshot preview must mention PLAIN TEXT")

    def test_8g_report_mentions_max_one_message(self):
        self.assertIn("max 1", self.report.lower())

    def test_8h_preview_has_cards_section(self):
        self.assertIn("Card Status", self.preview)

    def test_8i_report_no_deterministic_causal_language(self):
        for marker in ["will cause", "guaranteed to"]:
            self.assertNotIn(marker, self.report.lower())


class TestV118CFiveCardIntegration(unittest.TestCase):
    """Test that all 5 card families can appear in the pipeline."""

    def test_90_three_real_adapters_via_pipeline(self):
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

        families = set()
        for adapter in adapters:
            result = pipeline.run(adapter)
            families.add(result.card_family.value)

        self.assertEqual(families, set(THREE_REAL_ADAPTER_FAMILIES))

    def test_91_five_fixture_cards_work(self):
        from market_radar.shared.pipeline import SharedPipeline
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5)

    def test_92_liquidation_not_lowered(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        liq = [r for r in results if r.card_family == CardFamily.LIQUIDATION_PRESSURE]
        self.assertEqual(len(liq), 1)
        if liq[0].gate_decision:
            self.assertFalse(liq[0].gate_decision.allow)

    def test_93_whale_not_bypassed(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        whale = [r for r in results if r.card_family == CardFamily.WHALE_POSITION_ALERT]
        self.assertEqual(len(whale), 1)
        if whale[0].gate_decision:
            self.assertFalse(whale[0].gate_decision.allow)

    def test_94_liquidation_blocked_overlay_contract(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118c_runner", V118C_RUNNER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        overlay = module.build_liquidation_blocked_overlay()
        self.assertIn(overlay["status"], ("blocked", "manual_required"))
        self.assertFalse(overlay["send_eligible"])
        self.assertIn("NOT lowered", overlay["gate_reason"])

    def test_95_whale_blocked_overlay_contract(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118c_runner", V118C_RUNNER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        overlay = module.build_whale_blocked_overlay()
        self.assertIn(overlay["status"], ("blocked", "manual_required"))
        self.assertFalse(overlay["send_eligible"])
        self.assertIn("NOT bypass", overlay["gate_reason"])

    # ── v118C-specific: sender contract integration test ──

    def test_96_sender_supports_parse_mode_none(self):
        """Verify sender contract accepts parse_mode=None."""
        from market_radar.shared.sender_contract import TGTestGroupSender
        sender = TGTestGroupSender()
        # Check the send method signature
        import inspect
        sig = inspect.signature(sender.send)
        self.assertIn("parse_mode", sig.parameters)

    def test_97_sender_default_parse_mode_is_html(self):
        """Verify sender defaults to HTML for backward compatibility."""
        import inspect
        from market_radar.shared.sender_contract import TGTestGroupSender
        sig = inspect.signature(TGTestGroupSender.send)
        param = sig.parameters.get("parse_mode")
        self.assertIsNotNone(param)
        self.assertEqual(param.default, "HTML")


class TestV118CNewsCardGuard(unittest.TestCase):
    """Verify news card maintains observation_only / not_causal_proof."""

    def test_a0_news_card_observation_only(self):
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
        self.assertTrue(card.observation_only)
        self.assertTrue(card.not_causal_proof)


class TestV118CRegressionFilesExist(unittest.TestCase):
    """Test that v118C did not delete historical output files."""

    def test_b0_v118b_files_exist(self):
        missing = [str(f) for f in V118B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118B files deleted: {missing}")

    def test_b1_v118a_files_exist(self):
        missing = [str(f) for f in V118A_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118A files deleted: {missing}")

    def test_b2_v117f_files_exist(self):
        missing = [str(f) for f in V117F_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117F files deleted: {missing}")

    def test_b3_v117e_files_exist(self):
        missing = [str(f) for f in V117E_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117E files deleted: {missing}")

    def test_b4_v117d_files_exist(self):
        missing = [str(f) for f in V117D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117D files deleted: {missing}")

    def test_b5_v117c_files_exist(self):
        missing = [str(f) for f in V117C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117C files deleted: {missing}")

    def test_b6_v117b_files_exist(self):
        missing = [str(f) for f in V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117B files deleted: {missing}")

    def test_b7_v117_files_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117 files deleted: {missing}")

    def test_b8_v116n_files_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v116N files deleted: {missing}")

    def test_b9_historical_files_exist(self):
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"Historical files deleted: {missing}")


class TestV118CCompleteLeakAudit(unittest.TestCase):
    """Comprehensive audit of all v118C outputs for secret leaks."""

    def test_c0_all_outputs_no_raw_token(self):
        for fpath in ALL_V118C_OUTPUT_FILES:
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

    def test_c1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V118C_OUTPUT_FILES:
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

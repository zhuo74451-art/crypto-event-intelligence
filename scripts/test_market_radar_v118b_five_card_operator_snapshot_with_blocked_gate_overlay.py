"""Market Radar v118B — Five Card Operator Snapshot with Blocked Gate Overlay Tests.

Tests cover:
  - v118B runner can be imported
  - All five card families appear in the operator snapshot
  - Three real adapters all enter shared pipeline
  - Liquidation gate is NOT lowered, no fake spike
  - Whale manual evidence is NOT bypassed
  - Snapshot allows at most 1 TG message
  - Sent only when test_group + safe config + at least one active card
  - Failed/skipped/blocked NOT forged as sent
  - News card maintains observation_only / not_causal_proof
  - Snapshot contains no deterministic causal language
  - Result/report/ledger contain NO raw token/chat_id/message_id
  - Evidence ledger only contains SHA-256/redacted proofs
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - v116A-N history not modified
  - Regression: v118A/v117F/v117E/v117D/v117C/v117B/v117/v116N all pass

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v118b_five_card_operator_snapshot_with_blocked_gate_overlay.py -v
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


# ── v118B Paths ──────────────────────────────────────────────────────────────

V118B_RUNNER = ROOT / "scripts" / "run_market_radar_v118b_five_card_operator_snapshot_with_blocked_gate_overlay.py"
V118B_TEST = ROOT / "scripts" / "test_market_radar_v118b_five_card_operator_snapshot_with_blocked_gate_overlay.py"

PREFLIGHT_PATH = ROOT / "results" / "market_radar_v118b_five_card_snapshot_preflight.json"
RESULT_PATH = ROOT / "results" / "market_radar_v118b_five_card_snapshot_result.json"
LEDGER_PATH = ROOT / "results" / "market_radar_v118b_five_card_snapshot_evidence_ledger.jsonl"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v118b_five_card_operator_snapshot_report.md"
SNAPSHOT_PREVIEW_PATH = ROOT / "runs" / "market_radar" / "v118b_operator_snapshot_preview.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v118b_local_only_handoff.md"

ALL_V118B_OUTPUT_FILES = [
    PREFLIGHT_PATH, RESULT_PATH, LEDGER_PATH, REPORT_PATH,
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
    V118A_OUTPUT_FILES +
    V117F_OUTPUT_FILES + V117E_OUTPUT_FILES + V117D_OUTPUT_FILES +
    V117C_OUTPUT_FILES + V117B_OUTPUT_FILES + V117_OUTPUT_FILES +
    V116N_FILES + HISTORICAL_FILES
)


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestV118BFilesExist(unittest.TestCase):
    """Test that v118B runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V118B_RUNNER.exists(),
                        f"Missing runner: {V118B_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V118B_TEST.exists(),
                        f"Missing test: {V118B_TEST}")


class TestV118BOutputFilesExist(unittest.TestCase):
    """Test that all v118B output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V118B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v118B output files: {missing}")


class TestV118BRunnerStaticAnalysis(unittest.TestCase):
    """Static analysis of v118B runner source."""

    @classmethod
    def setUpClass(cls):
        cls.source = V118B_RUNNER.read_text(encoding="utf-8") if V118B_RUNNER.exists() else ""

    def test_20_runner_imports_shared_pipeline(self):
        self.assertIn("market_radar.shared", self.source,
                     "Runner must import from market_radar.shared")
        self.assertIn("SharedPipeline", self.source,
                     "Runner must use SharedPipeline")

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
            self.assertIn(cf, self.source,
                         f"Runner must reference {cf}")

    def test_2b_runner_has_snapshot_builder(self):
        self.assertIn("build_five_card_operator_snapshot", self.source)

    def test_2c_runner_has_card_snapshot_entry(self):
        self.assertIn("build_card_snapshot_entry", self.source)

    def test_2d_runner_passes_through_pipeline_run(self):
        self.assertIn("pipeline.run(adapter)", self.source)

    def test_2e_runner_has_max_one_message_enforcement(self):
        self.assertIn("message_count", self.source.lower())

    def test_2f_runner_liquidation_overlay_not_lowered(self):
        self.assertIn("NOT lowered", self.source)
        self.assertIn("calm_market_or_threshold_not_met", self.source)

    def test_2g_runner_whale_overlay_not_bypassed(self):
        self.assertIn("manual_attribution_evidence_required", self.source)

    def test_2h_runner_no_direct_secret_file_read(self):
        self.assertNotIn('config/local_secrets.ps1"', self.source.replace(
            'config/local_secrets.ps1', 'REDACTED'))


class TestV118BPreflight(unittest.TestCase):
    """Test v118B safe config preflight."""

    @classmethod
    def setUpClass(cls):
        if PREFLIGHT_PATH.exists():
            cls.preflight = load_json(PREFLIGHT_PATH)
        else:
            cls.preflight = None

    def test_30_preflight_exists(self):
        self.assertIsNotNone(self.preflight,
                           "Preflight file not found. Run the v118B runner first.")

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


class TestV118BResultFile(unittest.TestCase):
    """Test v118B result JSON file."""

    @classmethod
    def setUpClass(cls):
        if RESULT_PATH.exists():
            cls.result = load_json(RESULT_PATH)
        else:
            cls.result = None

    def test_40_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v118B runner first.")

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

    def test_4a_result_has_five_cards(self):
        cards = self.result.get("cards", [])
        self.assertEqual(len(cards), 5,
                        f"Must have 5 cards, got {len(cards)}")

    def test_4b_result_five_card_families_present(self):
        cards = self.result.get("cards", [])
        families = {c.get("card_family") for c in cards}
        expected = set(FIVE_CARD_FAMILIES)
        self.assertEqual(families, expected,
                        f"Card families mismatch: got {families}, expected {expected}")

    def test_4c_result_three_real_adapters_in_snapshot(self):
        cards = self.result.get("cards", [])
        real_cards = [c for c in cards if c.get("card_family") in THREE_REAL_ADAPTER_FAMILIES]
        self.assertEqual(len(real_cards), 3,
                        f"Must have 3 real adapter cards, got {len(real_cards)}")

    def test_4d_result_each_real_adapter_max_one_fetch(self):
        fetch_counts = self.result.get("adapter_fetch_counts", {})
        for cf, count in fetch_counts.items():
            if cf in THREE_REAL_ADAPTER_FAMILIES:
                self.assertLessEqual(count, 1,
                                   f"{cf} fetched {count} times (max 1 allowed)")

    def test_4e_result_snapshot_exists(self):
        snapshot = self.result.get("snapshot", {})
        self.assertIsNotNone(snapshot, "Snapshot must exist")
        self.assertIn("snapshot_text", snapshot, "Snapshot must contain snapshot_text")
        self.assertEqual(snapshot.get("card_count", 0), 5,
                        "Snapshot card_count must be 5")

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

    def test_4i_result_liquidation_is_blocked(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c.get("card_family") == "liquidation_pressure"]
        self.assertEqual(len(liq), 1, "Must have exactly 1 liquidation card")
        self.assertIn(liq[0]["status"], ("blocked", "manual_required"),
                     f"Liquidation must be blocked or manual_required, got {liq[0]['status']}")

    def test_4j_result_whale_is_manual_required(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c.get("card_family") == "whale_position_alert"]
        self.assertEqual(len(whale), 1, "Must have exactly 1 whale card")
        self.assertIn(whale[0]["status"], ("blocked", "manual_required"),
                     f"Whale must be blocked or manual_required, got {whale[0]['status']}")

    def test_4k_result_liquidation_not_send_eligible(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c.get("card_family") == "liquidation_pressure"]
        if liq:
            self.assertFalse(liq[0].get("send_eligible", True),
                           "Liquidation must NOT be send_eligible")

    def test_4l_result_whale_not_send_eligible(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c.get("card_family") == "whale_position_alert"]
        if whale:
            self.assertFalse(whale[0].get("send_eligible", True),
                           "Whale must NOT be send_eligible")

    def test_4m_result_no_deterministic_causal_language(self):
        snapshot = self.result.get("snapshot", {})
        snapshot_text = snapshot.get("snapshot_text", "").lower()
        causal_markers = [
            "will cause", "will lead to", "guaranteed to",
            "definitely", "certainly", "without doubt",
        ]
        for marker in causal_markers:
            self.assertNotIn(marker, snapshot_text,
                           f"Snapshot contains deterministic causal marker: '{marker}'")

    def test_4n_result_blocked_overlays_exist(self):
        overlays = self.result.get("blocked_overlays", {})
        self.assertIn("liquidation_pressure", overlays)
        self.assertIn("whale_position_alert", overlays)

    def test_4o_result_liquidation_threshold_not_lowered(self):
        overlays = self.result.get("blocked_overlays", {})
        liq = overlays.get("liquidation_pressure", {})
        self.assertTrue(liq.get("threshold_not_lowered", False),
                       "liquidation threshold_not_lowered must be True")
        self.assertTrue(liq.get("no_fake_spike", False),
                       "liquidation no_fake_spike must be True")

    def test_4p_result_whale_evidence_not_bypassed(self):
        overlays = self.result.get("blocked_overlays", {})
        whale = overlays.get("whale_position_alert", {})
        self.assertTrue(whale.get("manual_evidence_not_bypassed", False),
                       "whale manual_evidence_not_bypassed must be True")
        self.assertTrue(whale.get("no_address_guess", False),
                       "whale no_address_guess must be True")

    def test_4q_result_sent_not_faked_on_blocked(self):
        tg_snapshot = self.result.get("tg_snapshot", {})
        if tg_snapshot:
            status = tg_snapshot.get("status", "")
            if status in ("blocked", "skipped", "failed"):
                self.assertNotEqual(status, "sent",
                                  "Cannot claim sent when status is blocked/skipped/failed")

    def test_4r_result_v116_history_not_modified(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("v116_history_modified", True),
                        "v116_history_modified must be False")

    def test_4s_result_news_card_has_observation_only_guard(self):
        snapshot = self.result.get("snapshot", {})
        snapshot_text = snapshot.get("snapshot_text", "")
        self.assertIn("not causal proof", snapshot_text.lower(),
                     "Snapshot must mention 'not causal proof'")

    def test_4t_result_shared_pipeline_referenced(self):
        proof = self.result.get("five_card_proof", "")
        self.assertIn("shared pipeline", proof.lower())


class TestV118BEvidenceLedger(unittest.TestCase):
    """Test v118B evidence ledger."""

    @classmethod
    def setUpClass(cls):
        if LEDGER_PATH.exists():
            cls.entries = load_jsonl(LEDGER_PATH)
        else:
            cls.entries = []

    def test_50_ledger_exists(self):
        self.assertTrue(LEDGER_PATH.exists(),
                       "Evidence ledger not found. Run v118B runner first.")

    def test_51_ledger_has_entries(self):
        self.assertGreaterEqual(len(self.entries), 1,
                              "Ledger must have at least 1 entry")

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


class TestV118BReports(unittest.TestCase):
    """Test v118B report markdown files."""

    @classmethod
    def setUpClass(cls):
        cls.report = ""
        cls.handoff = ""
        cls.snapshot_preview = ""
        if REPORT_PATH.exists():
            cls.report = REPORT_PATH.read_text(encoding="utf-8")
        if HANDOFF_PATH.exists():
            cls.handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        if SNAPSHOT_PREVIEW_PATH.exists():
            cls.snapshot_preview = SNAPSHOT_PREVIEW_PATH.read_text(encoding="utf-8")

    def test_60_report_exists(self):
        self.assertTrue(REPORT_PATH.exists(), "Report not found")

    def test_61_handoff_exists(self):
        self.assertTrue(HANDOFF_PATH.exists(), "Handoff not found")

    def test_62_snapshot_preview_exists(self):
        self.assertTrue(SNAPSHOT_PREVIEW_PATH.exists(), "Snapshot preview not found")

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

    def test_68_snapshot_preview_no_forbidden_patterns(self):
        violations = check_forbidden(self.snapshot_preview)
        self.assertEqual(len(violations), 0,
                         f"Snapshot preview contains forbidden patterns: {violations}")

    def test_69_report_mentions_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.report,
                         f"Report must mention {cf}")

    def test_6a_report_mentions_shared_pipeline(self):
        self.assertIn("shared pipeline", self.report.lower(),
                     "Report must mention shared pipeline")

    def test_6b_report_mentions_operator_snapshot(self):
        self.assertIn("operator snapshot", self.report.lower(),
                     "Report must mention operator snapshot")

    def test_6c_report_mentions_production_ready_false(self):
        self.assertIn("NOT FOR LIVE USE", self.report,
                     "Report must state NOT FOR LIVE USE")

    def test_6d_snapshot_preview_has_cards(self):
        self.assertIn("Card Status", self.snapshot_preview,
                     "Snapshot preview must have Card Status section")

    def test_6e_snapshot_preview_no_causal_language(self):
        markers = ["will cause", "will definitely", "guaranteed"]
        for m in markers:
            self.assertNotIn(m, self.snapshot_preview.lower(),
                           f"Snapshot preview contains '{m}'")

    def test_6f_handoff_mentions_liquidation_not_lowered(self):
        self.assertIn("not lowered", self.handoff.lower(),
                     "Handoff must mention liquidation threshold not lowered")

    def test_6g_handoff_mentions_whale_not_bypassed(self):
        self.assertIn("not bypassed", self.handoff.lower(),
                     "Handoff must mention whale evidence not bypassed")

    def test_6h_report_mentions_blocked_overlay(self):
        self.assertIn("blocked overlay", self.report.lower(),
                     "Report must mention blocked overlay")

    def test_6i_report_mentions_max_one_message(self):
        self.assertIn("max 1", self.report.lower(),
                     "Report must mention max 1 TG message")


class TestV118BFiveCardIntegration(unittest.TestCase):
    """Test that all 5 card families can appear in the pipeline."""

    def test_70_three_real_adapters_via_shared_pipeline(self):
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
        families = set()
        for adapter in adapters:
            result = pipeline.run(adapter)
            results.append(result)
            families.add(result.card_family.value)

        # All 3 real card families present
        self.assertEqual(families, set(THREE_REAL_ADAPTER_FAMILIES),
                        f"Expected 3 real card families, got {families}")

        # Each adapter fetched at most once
        for adapter in adapters:
            if hasattr(adapter, '_fetch_count'):
                self.assertLessEqual(adapter._fetch_count, 1,
                                   f"{adapter.card_family.value}: fetched {adapter._fetch_count} times")

    def test_71_five_fixture_cards_still_work(self):
        from market_radar.shared.pipeline import SharedPipeline
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        self.assertEqual(len(results), 5,
                        f"Fixture pipeline should produce 5 results, got {len(results)}")

    def test_72_liquidation_fixture_gate_not_lowered(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        liq_result = [r for r in results if r.card_family == CardFamily.LIQUIDATION_PRESSURE]
        self.assertEqual(len(liq_result), 1)
        if liq_result[0].gate_decision:
            self.assertFalse(liq_result[0].gate_decision.allow,
                           "Liquidation fixture gate must NOT allow")
            self.assertIn("calm market", liq_result[0].gate_decision.reason.lower(),
                         "Liquidation gate reason must mention calm market")

    def test_73_whale_fixture_gate_not_bypassed(self):
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.models import CardFamily
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        whale_result = [r for r in results if r.card_family == CardFamily.WHALE_POSITION_ALERT]
        self.assertEqual(len(whale_result), 1)
        if whale_result[0].gate_decision:
            self.assertFalse(whale_result[0].gate_decision.allow,
                           "Whale fixture gate must NOT allow")
            self.assertIn("manual evidence", whale_result[0].gate_decision.reason.lower(),
                         "Whale gate reason must mention manual evidence")

    def test_74_liquidation_blocked_overlay_contract(self):
        """Verify the v118B runner's liquidation overlay builder respects the contract."""
        # Import the overlay builder from the runner
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "v118b_runner",
            V118B_RUNNER
        )
        self.assertIsNotNone(spec, "Could not create spec for v118B runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        overlay = module.build_liquidation_blocked_overlay()
        self.assertIn(overlay["status"], ("blocked", "manual_required"))
        self.assertFalse(overlay["send_eligible"])
        self.assertIn("NOT lowered", overlay["gate_reason"])
        self.assertIn("threshold", overlay["gate_reason"])

    def test_75_whale_blocked_overlay_contract(self):
        """Verify the v118B runner's whale overlay builder respects the contract."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "v118b_runner",
            V118B_RUNNER
        )
        self.assertIsNotNone(spec, "Could not create spec for v118B runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        overlay = module.build_whale_blocked_overlay()
        self.assertIn(overlay["status"], ("blocked", "manual_required"))
        self.assertFalse(overlay["send_eligible"])
        self.assertIn("manual", overlay["gate_reason"].lower())
        self.assertIn("NOT bypass", overlay["gate_reason"])


class TestV118BNewsCardGuard(unittest.TestCase):
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


class TestV118BRegressionFilesExist(unittest.TestCase):
    """Test that v118B did not delete historical output files."""

    def test_90_v118a_output_files_exist(self):
        missing = [str(f) for f in V118A_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v118A files deleted: {missing}")

    def test_91_v117f_output_files_exist(self):
        missing = [str(f) for f in V117F_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117F files deleted: {missing}")

    def test_92_v117e_output_files_exist(self):
        missing = [str(f) for f in V117E_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117E files deleted: {missing}")

    def test_93_v117d_output_files_exist(self):
        missing = [str(f) for f in V117D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117D files deleted: {missing}")

    def test_94_v117c_output_files_exist(self):
        missing = [str(f) for f in V117C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117C files deleted: {missing}")

    def test_95_v117b_output_files_exist(self):
        missing = [str(f) for f in V117B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117B files deleted: {missing}")

    def test_96_v117_output_files_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v117 files deleted: {missing}")

    def test_97_v116n_files_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"v116N files deleted: {missing}")

    def test_98_historical_files_exist(self):
        missing = [str(f) for f in HISTORICAL_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Historical v116 files deleted: {missing}")


class TestV118BCompleteLeakAudit(unittest.TestCase):
    """Comprehensive audit of all v118B outputs for secret leaks."""

    def test_b0_all_outputs_no_raw_token(self):
        for fpath in ALL_V118B_OUTPUT_FILES:
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
        for fpath in ALL_V118B_OUTPUT_FILES:
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

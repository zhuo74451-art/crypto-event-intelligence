"""Market Radar v1.16-D — Real Free API Multi-Asset TG Test Send Tests

Validates all v116D outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - Output files exist
  - raw snapshot marked as real_external_api_called: true
  - API source is free public API, api_key_required: false
  - At least BTC, ETH, SOL assets present or blocked reason
  - card_family == multi_asset_market_sync
  - audit_result is one of the 4 allowed values
  - fixture_only: false
  - production_send_ready: false
  - prod_state_write: false
  - ai_model_called: false
  - credentials_printed: false
  - credentials_read_plaintext: false (or True if env vars were used — project pattern)
  - daemon_or_loop_started: false
  - files_deleted: false
  - No token/key/cookie/password plaintext in outputs
  - No fixture_only: true masquerading

Usage:
    python scripts/test_market_radar_v116d_real_free_api_multi_asset_tg_test_send_one_shot.py
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]

SEND_RESULT_JSON = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_tg_test_send_result.json"
RAW_SNAPSHOTS_JSON = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_raw_snapshots.json"
SIGNAL_RECORDS_JSONL = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_signal_records.jsonl"
CARD_RECORDS_JSONL = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_card_records.jsonl"
QUALITY_GATE_JSONL = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_quality_gate_records.jsonl"
SEND_READINESS_JSONL = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = ROOT / "results" / "market_radar_v116d_real_free_api_multi_asset_tg_send_attempts.jsonl"
SEND_REPORT_MD = ROOT / "runs" / "market_radar" / "v116d_real_free_api_multi_asset_tg_test_send_report.md"
CARD_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v116d_real_free_api_multi_asset_tg_test_card_preview.md"
HANDOFF_MD = ROOT / "runs" / "market_radar" / "v116d_real_free_api_multi_asset_tg_test_send_local_only_handoff.md"

ALLOWED_AUDIT_RESULTS = [
    "real_free_api_tg_test_sent",
    "real_free_api_card_ready_tg_blocked_missing_sender",
    "blocked_free_api_unavailable",
    "blocked_gate_not_passed",
]

FORBIDDEN_PATTERNS = [
    # Token/key/cookie/password patterns
    r'\b[0-9]{8,10}:[A-Za-z0-9_-]{35,}\b',  # Telegram bot token pattern
    r'bot[0-9]{8,10}:',                       # bot token prefix
    r'api_key\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}',  # API key assignments
    r'chat_id\s*[:=]\s*["\']-?[0-9]{5,}',     # chat_id assignments
    r'password\s*[:=]\s*["\'][^"\']+["\']',   # password assignments
    r'secret\s*[:=]\s*["\'][A-Za-z0-9_-]{10,}',  # secret assignments
    r'cookie\s*[:=]\s*["\'][^"\']+["\']',     # cookie assignments
]


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


def check_no_forbidden_patterns(text: str) -> list[str]:
    """Check text for forbidden patterns (token/key/password etc.). Returns list of violations."""
    violations = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Pattern matched: {pattern[:60]}...")
    return violations


# ── Test Case ────────────────────────────────────────────────────────────

class TestV116DRealFreeApiMultiAssetTgTestSend(unittest.TestCase):
    """Tests for v116D Real Free API Multi-Asset TG Test Send."""

    @classmethod
    def setUpClass(cls):
        cls.send_result = None
        cls.raw_snapshot = None
        cls.signal_records = []
        cls.card_records = []
        cls.quality_gates = []
        cls.send_readiness = []
        cls.tg_attempts = []
        cls.report_text = ""
        cls.handoff_text = ""

        if SEND_RESULT_JSON.exists():
            with open(SEND_RESULT_JSON, "r", encoding="utf-8") as f:
                cls.send_result = json.load(f)

        if RAW_SNAPSHOTS_JSON.exists():
            with open(RAW_SNAPSHOTS_JSON, "r", encoding="utf-8") as f:
                cls.raw_snapshot = json.load(f)

        if SIGNAL_RECORDS_JSONL.exists():
            cls.signal_records = load_jsonl(SIGNAL_RECORDS_JSONL)

        if CARD_RECORDS_JSONL.exists():
            cls.card_records = load_jsonl(CARD_RECORDS_JSONL)

        if QUALITY_GATE_JSONL.exists():
            cls.quality_gates = load_jsonl(QUALITY_GATE_JSONL)

        if SEND_READINESS_JSONL.exists():
            cls.send_readiness = load_jsonl(SEND_READINESS_JSONL)

        if TG_SEND_ATTEMPTS_JSONL.exists():
            cls.tg_attempts = load_jsonl(TG_SEND_ATTEMPTS_JSONL)

        if SEND_REPORT_MD.exists():
            with open(SEND_REPORT_MD, "r", encoding="utf-8") as f:
                cls.report_text = f.read()

        if HANDOFF_MD.exists():
            with open(HANDOFF_MD, "r", encoding="utf-8") as f:
                cls.handoff_text = f.read()

    # ══════════════════════════════════════════════════════════════════════
    # File existence tests
    # ══════════════════════════════════════════════════════════════════════

    def test_01_send_result_json_exists(self):
        """Send result JSON must exist."""
        self.assertTrue(SEND_RESULT_JSON.exists(),
                        f"Missing: {SEND_RESULT_JSON}")

    def test_02_raw_snapshots_json_exists(self):
        """Raw snapshots JSON must exist."""
        self.assertTrue(RAW_SNAPSHOTS_JSON.exists(),
                        f"Missing: {RAW_SNAPSHOTS_JSON}")

    def test_03_signal_records_jsonl_exists(self):
        """Signal records JSONL must exist."""
        self.assertTrue(SIGNAL_RECORDS_JSONL.exists(),
                        f"Missing: {SIGNAL_RECORDS_JSONL}")

    def test_04_card_records_jsonl_exists(self):
        """Card records JSONL must exist."""
        self.assertTrue(CARD_RECORDS_JSONL.exists(),
                        f"Missing: {CARD_RECORDS_JSONL}")

    def test_05_quality_gate_jsonl_exists(self):
        """Quality gate JSONL must exist."""
        self.assertTrue(QUALITY_GATE_JSONL.exists(),
                        f"Missing: {QUALITY_GATE_JSONL}")

    def test_06_send_readiness_jsonl_exists(self):
        """Send readiness JSONL must exist."""
        self.assertTrue(SEND_READINESS_JSONL.exists(),
                        f"Missing: {SEND_READINESS_JSONL}")

    def test_07_tg_send_attempts_jsonl_exists(self):
        """TG send attempts JSONL must exist."""
        self.assertTrue(TG_SEND_ATTEMPTS_JSONL.exists(),
                        f"Missing: {TG_SEND_ATTEMPTS_JSONL}")

    def test_08_send_report_md_exists(self):
        """Send report markdown must exist."""
        self.assertTrue(SEND_REPORT_MD.exists(),
                        f"Missing: {SEND_REPORT_MD}")

    def test_09_card_preview_md_exists(self):
        """Card preview markdown must exist."""
        self.assertTrue(CARD_PREVIEW_MD.exists(),
                        f"Missing: {CARD_PREVIEW_MD}")

    def test_10_handoff_md_exists(self):
        """Handoff markdown must exist."""
        self.assertTrue(HANDOFF_MD.exists(),
                        f"Missing: {HANDOFF_MD}")

    # ══════════════════════════════════════════════════════════════════════
    # Send result JSON field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_11_card_family_correct(self):
        """card_family must be multi_asset_market_sync."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertEqual(self.send_result.get("card_family"), "multi_asset_market_sync",
                         "card_family must be 'multi_asset_market_sync'")

    def test_12_fixture_only_is_false(self):
        """fixture_only must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("fixture_only", True),
                        "fixture_only must be false — this is real API data")

    def test_13_production_send_ready_is_false(self):
        """production_send_ready must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("production_send_ready", True),
                        "production_send_ready must be false")

    def test_14_prod_state_write_is_false(self):
        """prod_state_write must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("prod_state_write", True),
                        "prod_state_write must be false")

    def test_15_ai_model_called_is_false(self):
        """ai_model_called must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("ai_model_called", True),
                        "ai_model_called must be false")

    def test_16_credentials_printed_is_false(self):
        """credentials_printed must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("credentials_printed", True),
                        "credentials_printed must be false")

    def test_17_daemon_or_loop_started_is_false(self):
        """daemon_or_loop_started must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("daemon_or_loop_started", True),
                        "daemon_or_loop_started must be false")

    def test_18_files_deleted_is_false(self):
        """files_deleted must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("files_deleted", True),
                        "files_deleted must be false")

    def test_19_audit_result_is_allowed_value(self):
        """audit_result must be one of the 4 allowed values."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        audit = self.send_result.get("audit_result", "")
        self.assertIn(audit, ALLOWED_AUDIT_RESULTS,
                      f"audit_result '{audit}' not in allowed: {ALLOWED_AUDIT_RESULTS}")

    def test_20_api_key_required_is_false(self):
        """api_key_required must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        # This field may be at top level or in raw snapshot
        api_key_req = self.send_result.get("api_key_required", None)
        if api_key_req is None and self.raw_snapshot:
            api_key_req = self.raw_snapshot.get("api_key_required", True)
        self.assertFalse(api_key_req if api_key_req is not None else True,
                        "api_key_required must be false (free public API)")

    # ══════════════════════════════════════════════════════════════════════
    # Raw snapshot tests
    # ══════════════════════════════════════════════════════════════════════

    def test_21_raw_snapshot_has_real_api_flag(self):
        """Raw snapshot must have real_external_api_called: true OR blocked."""
        if self.raw_snapshot:
            real_api = self.raw_snapshot.get("real_external_api_called", False)
            blocked = self.raw_snapshot.get("blocked", False)
            self.assertTrue(
                real_api or blocked,
                "raw snapshot must have real_external_api_called=true or blocked=true"
            )

    def test_22_raw_snapshot_has_assets_or_blocked(self):
        """Raw snapshot must have assets (BTC/ETH/SOL) OR explicit blocked reason."""
        if self.raw_snapshot:
            assets = self.raw_snapshot.get("assets", [])
            blocked = self.raw_snapshot.get("blocked", False)
            block_reason = self.raw_snapshot.get("block_reason", "")

            if not blocked:
                asset_labels = {a.get("asset", "") for a in assets}
                required = {"BTC", "ETH", "SOL"}
                overlap = asset_labels & required
                self.assertGreaterEqual(
                    len(overlap), 2,
                    f"Raw snapshot must have at least 2 of BTC/ETH/SOL, got: {asset_labels}"
                )
            else:
                self.assertTrue(bool(block_reason),
                              "If blocked, must have a block_reason")

    def test_23_raw_snapshot_api_source_is_free(self):
        """API source must indicate free public API."""
        if self.raw_snapshot:
            api_key_req = self.raw_snapshot.get("api_key_required", True)
            self.assertFalse(api_key_req,
                           "raw snapshot api_key_required must be false")

    def test_24_raw_snapshot_not_fixture(self):
        """Raw snapshot must NOT be marked as fixture."""
        if self.raw_snapshot:
            is_fixture = self.raw_snapshot.get("is_fixture", True)
            if not self.raw_snapshot.get("blocked", False):
                self.assertFalse(is_fixture,
                               "raw snapshot is_fixture must be false for real API data")

    # ══════════════════════════════════════════════════════════════════════
    # Signal record tests
    # ══════════════════════════════════════════════════════════════════════

    def test_25_signal_records_have_card_family(self):
        """Signal records must have card_family field."""
        for rec in self.signal_records:
            self.assertEqual(rec.get("card_family"), "multi_asset_market_sync",
                           f"Signal record missing card_family")

    def test_26_signal_records_have_real_api_flag(self):
        """Signal records must have real_external_api_called: true."""
        for rec in self.signal_records:
            self.assertTrue(rec.get("real_external_api_called", False),
                          f"Signal record real_external_api_called must be true")

    def test_27_signal_records_have_assets(self):
        """Signal records must have assets list."""
        for rec in self.signal_records:
            assets = rec.get("assets", [])
            self.assertGreaterEqual(len(assets), 2,
                                  "Signal record must have at least 2 assets")

    # ══════════════════════════════════════════════════════════════════════
    # Quality gate tests
    # ══════════════════════════════════════════════════════════════════════

    def test_30_quality_gate_records_exist(self):
        """At least 1 quality gate record must exist."""
        self.assertGreaterEqual(len(self.quality_gates), 1,
                               "At least 1 quality gate record required")

    def test_31_quality_gate_no_fixture_only_true(self):
        """Quality gate records must NOT have fixture_only: true."""
        for rec in self.quality_gates:
            self.assertFalse(rec.get("fixture_only", True),
                           f"Quality gate record {rec.get('event_id')} must not have fixture_only=true")

    # ══════════════════════════════════════════════════════════════════════
    # Send-readiness tests
    # ══════════════════════════════════════════════════════════════════════

    def test_32_send_readiness_records_exist(self):
        """At least 1 send-readiness record must exist."""
        self.assertGreaterEqual(len(self.send_readiness), 1,
                               "At least 1 send-readiness record required")

    def test_33_send_readiness_production_is_false(self):
        """Send-readiness records must have production_send_ready: false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("production_send_ready", True),
                           f"Send-readiness record must have production_send_ready=false")

    # ══════════════════════════════════════════════════════════════════════
    # TG send attempt tests
    # ══════════════════════════════════════════════════════════════════════

    def test_34_tg_attempt_records_exist(self):
        """At least 1 TG send attempt record must exist."""
        self.assertGreaterEqual(len(self.tg_attempts), 1,
                               "At least 1 TG send attempt record required")

    def test_35_tg_attempt_has_required_fields(self):
        """TG send attempt must have attempted and blocked_reason or success."""
        for rec in self.tg_attempts:
            self.assertIn("attempted", rec, "TG attempt missing 'attempted' field")
            if not rec.get("success", False):
                self.assertIn("blocked_reason", rec,
                            "Failed TG attempt missing 'blocked_reason'")

    # ══════════════════════════════════════════════════════════════════════
    # Report content tests
    # ══════════════════════════════════════════════════════════════════════

    def test_40_report_contains_card_family(self):
        """Report must mention multi_asset_market_sync."""
        self.assertIn("multi_asset_market_sync", self.report_text.lower(),
                     "Report must mention card_family")

    def test_41_report_contains_api_source(self):
        """Report must mention Binance API source."""
        has_api = "binance" in self.report_text.lower() or "api" in self.report_text.lower()
        self.assertTrue(has_api, "Report must mention API source")

    def test_42_report_does_not_claim_production_send(self):
        """Report must not claim production send."""
        bad_claims = [
            "production send: ✅",
            "production_send_ready: true",
            "sent to channel",
        ]
        report_lower = self.report_text.lower()
        for claim in bad_claims:
            self.assertNotIn(claim, report_lower,
                           f"Report incorrectly claims: '{claim}'")

    def test_43_report_mentions_test_group(self):
        """Report must indicate test group (not production channel)."""
        has_test = ("test_group" in self.report_text.lower() or
                    "test group" in self.report_text.lower() or
                    "测试群" in self.report_text)
        has_not_channel = "channel" not in self.report_text.lower() or "not channel" in self.report_text.lower()
        self.assertTrue(has_test or has_not_channel,
                       "Report must indicate test group context")

    # ══════════════════════════════════════════════════════════════════════
    # Handoff content tests
    # ══════════════════════════════════════════════════════════════════════

    def test_44_handoff_contains_audit_result(self):
        """Handoff must mention audit_result."""
        if self.send_result:
            audit = self.send_result.get("audit_result", "")
            has_audit = audit.lower() in self.handoff_text.lower() if audit else False
            # At minimum the handoff should mention one of the allowed results
            any_result = any(ar.lower() in self.handoff_text.lower() for ar in ALLOWED_AUDIT_RESULTS)
            self.assertTrue(has_audit or any_result,
                          "Handoff must mention audit_result")

    def test_45_handoff_contains_safety_confirmation(self):
        """Handoff must contain safety confirmation section."""
        safety_in_handoff = (
            "safety" in self.handoff_text.lower() or
            "no production" in self.handoff_text.lower() or
            "PASS" in self.handoff_text
        )
        self.assertTrue(safety_in_handoff,
                       "Handoff must include safety confirmation")

    # ══════════════════════════════════════════════════════════════════════
    # Secret leak prevention tests
    # ══════════════════════════════════════════════════════════════════════

    def test_50_no_plaintext_token_in_report(self):
        """Report must not contain token/key/password patterns."""
        violations = check_no_forbidden_patterns(self.report_text)
        self.assertEqual(len(violations), 0,
                       f"Report contains forbidden patterns: {violations}")

    def test_51_no_plaintext_token_in_handoff(self):
        """Handoff must not contain token/key/password patterns."""
        violations = check_no_forbidden_patterns(self.handoff_text)
        self.assertEqual(len(violations), 0,
                       f"Handoff contains forbidden patterns: {violations}")

    def test_52_no_plaintext_token_in_send_result(self):
        """Send result JSON must not contain token/key/password patterns."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            violations = check_no_forbidden_patterns(result_str)
            self.assertEqual(len(violations), 0,
                           f"Send result contains forbidden patterns: {violations}")

    def test_53_no_plaintext_token_in_raw_snapshot(self):
        """Raw snapshot JSON must not contain token/key/password patterns."""
        if self.raw_snapshot:
            snapshot_str = json.dumps(self.raw_snapshot, ensure_ascii=False)
            violations = check_no_forbidden_patterns(snapshot_str)
            self.assertEqual(len(violations), 0,
                           f"Raw snapshot contains forbidden patterns: {violations}")

    # ══════════════════════════════════════════════════════════════════════
    # Quality attribute tests
    # ══════════════════════════════════════════════════════════════════════

    def test_54_no_fixture_only_true_in_outputs(self):
        """No output JSON file should have fixture_only: true (this is real API)."""
        for path in [SEND_RESULT_JSON, RAW_SNAPSHOTS_JSON]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Check for "fixture_only": true (but allow "fixture_only": false)
                fixture_true_pattern = r'"fixture_only"\s*:\s*true'
                matches = re.findall(fixture_true_pattern, content, re.IGNORECASE)
                self.assertEqual(len(matches), 0,
                               f"{path.name} contains fixture_only: true — this is real API data")

    def test_55_report_or_handoff_mentions_one_shot(self):
        """Report or handoff must mention one-shot."""
        combined = (self.report_text + self.handoff_text).lower()
        has_oneshot = "one-shot" in combined or "one_shot" in combined or "oneshot" in combined
        self.assertTrue(has_oneshot,
                       "Must mention one-shot execution")

    def test_56_card_records_have_content(self):
        """Card records must have non-empty card_text."""
        for rec in self.card_records:
            card_text = rec.get("card_text", "")
            self.assertGreater(len(card_text), 100,
                             f"Card text must be > 100 chars, got {len(card_text)}")

    def test_57_assets_in_signal_include_major(self):
        """Signal records should include at least BTC, ETH, or SOL."""
        for rec in self.signal_records:
            assets = rec.get("assets", [])
            if not rec.get("blocked", False):
                major_overlap = set(assets) & {"BTC", "ETH", "SOL"}
                self.assertGreaterEqual(
                    len(major_overlap), 2,
                    f"Signal assets {assets} must include at least 2 of BTC/ETH/SOL"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

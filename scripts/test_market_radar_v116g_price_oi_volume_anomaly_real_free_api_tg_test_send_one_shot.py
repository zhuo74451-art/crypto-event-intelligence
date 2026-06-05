"""Market Radar v1.16-G — Price/OI/Volume Anomaly Real Free API TG Test Send Tests

Validates all v116G outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116G output files exist
  - card_family == price_oi_volume_anomaly
  - real_external_api_called == true
  - fixture_only == false
  - api_key_required == false
  - At least BTC/ETH/SOL three assets attempted
  - audit_result is one of the 4 allowed values
  - production_send_ready == false
  - prod_state_write == false
  - ai_model_called == false
  - daemon_or_loop_started == false
  - files_deleted == false
  - secret_preflight_run == true (v116G mandatory)
  - No token/key/cookie/password plaintext in any output
  - No raw TELEGRAM_BOT_TOKEN in any output
  - No raw TELEGRAM_CHAT_ID in any output
  - TG success → redacted proof present
  - TG blocked → real blocked reason present
  - TG blocked → not masquerading as success

Usage:
    python scripts/test_market_radar_v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot.py
"""

import json
import re
import sys
import unittest
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]

SEND_RESULT_JSON = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json"
RAW_SNAPSHOTS_JSON = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_raw_snapshots.json"
SIGNAL_RECORDS_JSONL = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_signal_records.jsonl"
CARD_RECORDS_JSONL = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_card_records.jsonl"
QUALITY_GATE_JSONL = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_quality_gate_records.jsonl"
SEND_READINESS_JSONL = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = ROOT / "results" / "market_radar_v116g_price_oi_volume_anomaly_tg_send_attempts.jsonl"
SEND_REPORT_MD = ROOT / "runs" / "market_radar" / "v116g_price_oi_volume_anomaly_tg_test_send_report.md"
HANDOFF_MD = ROOT / "runs" / "market_radar" / "v116g_price_oi_volume_anomaly_local_only_handoff.md"
CARD_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v116g_price_oi_volume_anomaly_card_preview.md"

ALLOWED_AUDIT_RESULTS = [
    "real_free_api_tg_test_sent",
    "real_free_api_card_ready_tg_blocked_missing_sender",
    "blocked_free_api_unavailable",
    "blocked_gate_not_passed",
]

FORBIDDEN_PATTERNS = [
    # Telegram bot token pattern (bot<NUM>:<HASH>)
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

EXPECTED_TARGET_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


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


def check_no_raw_token(text: str) -> bool:
    """Check if text contains a raw Telegram bot token pattern. Returns True if CLEAN."""
    return not bool(RAW_TOKEN_PATTERN.search(text))


def check_no_raw_chat_id_assignment(text: str) -> bool:
    """Check if text contains a raw chat_id assignment. Returns True if CLEAN."""
    return not bool(RAW_CHAT_ID_PATTERN.search(text))


# ── Test Case ────────────────────────────────────────────────────────────

class TestV116GPriceOiVolumeAnomalyRealFreeApiTgTestSend(unittest.TestCase):
    """Tests for v116G Price/OI/Volume Anomaly Real Free API TG Test Send."""

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

    def test_02_send_report_md_exists(self):
        """Send report markdown must exist."""
        self.assertTrue(SEND_REPORT_MD.exists(),
                        f"Missing: {SEND_REPORT_MD}")

    def test_03_handoff_md_exists(self):
        """Handoff markdown must exist."""
        self.assertTrue(HANDOFF_MD.exists(),
                        f"Missing: {HANDOFF_MD}")

    def test_04_raw_snapshots_json_exists(self):
        """Raw snapshots JSON must exist."""
        self.assertTrue(RAW_SNAPSHOTS_JSON.exists(),
                        f"Missing: {RAW_SNAPSHOTS_JSON}")

    def test_05_signal_records_jsonl_exists(self):
        """Signal records JSONL must exist."""
        self.assertTrue(SIGNAL_RECORDS_JSONL.exists(),
                        f"Missing: {SIGNAL_RECORDS_JSONL}")

    def test_06_card_records_jsonl_exists(self):
        """Card records JSONL must exist."""
        self.assertTrue(CARD_RECORDS_JSONL.exists(),
                        f"Missing: {CARD_RECORDS_JSONL}")

    def test_07_quality_gate_jsonl_exists(self):
        """Quality gate JSONL must exist."""
        self.assertTrue(QUALITY_GATE_JSONL.exists(),
                        f"Missing: {QUALITY_GATE_JSONL}")

    def test_08_send_readiness_jsonl_exists(self):
        """Send-readiness JSONL must exist."""
        self.assertTrue(SEND_READINESS_JSONL.exists(),
                        f"Missing: {SEND_READINESS_JSONL}")

    def test_09_tg_send_attempts_jsonl_exists(self):
        """TG send attempts JSONL must exist."""
        self.assertTrue(TG_SEND_ATTEMPTS_JSONL.exists(),
                        f"Missing: {TG_SEND_ATTEMPTS_JSONL}")

    def test_10_card_preview_md_exists(self):
        """Card preview markdown must exist."""
        self.assertTrue(CARD_PREVIEW_MD.exists(),
                        f"Missing: {CARD_PREVIEW_MD}")

    # ══════════════════════════════════════════════════════════════════════
    # Core field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_11_card_family_correct(self):
        """card_family must be price_oi_volume_anomaly."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertEqual(self.send_result.get("card_family"), "price_oi_volume_anomaly")

    def test_12_real_external_api_called_true(self):
        """real_external_api_called must be true."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertTrue(self.send_result.get("real_external_api_called", False),
                       "real_external_api_called must be true — real Binance API used")

    def test_13_fixture_only_is_false(self):
        """fixture_only must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("fixture_only", True))

    def test_14_api_key_required_is_false(self):
        """api_key_required must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("api_key_required", True))

    def test_15_production_send_ready_is_false(self):
        """production_send_ready must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("production_send_ready", True))

    def test_16_prod_state_write_is_false(self):
        """prod_state_write must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("prod_state_write", True))

    def test_17_ai_model_called_is_false(self):
        """ai_model_called must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("ai_model_called", True))

    def test_18_daemon_or_loop_started_is_false(self):
        """daemon_or_loop_started must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("daemon_or_loop_started", True))

    def test_19_files_deleted_is_false(self):
        """files_deleted must be false."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("files_deleted", True))

    # ══════════════════════════════════════════════════════════════════════
    # Asset coverage tests
    # ══════════════════════════════════════════════════════════════════════

    def test_20_at_least_three_assets_in_snapshot(self):
        """Raw snapshot must contain at least BTC/ETH/SOL three assets."""
        self.assertIsNotNone(self.raw_snapshot, "Raw snapshot not loaded")
        assets = self.raw_snapshot.get("assets", [])
        asset_symbols = [a.get("symbol", "") for a in assets]
        for expected_sym in EXPECTED_TARGET_ASSETS:
            self.assertIn(expected_sym, asset_symbols,
                         f"Missing expected asset {expected_sym} in snapshot")

    def test_21_at_least_three_assets_in_signals(self):
        """At least 3 signal records (one per asset) must exist."""
        self.assertGreaterEqual(len(self.signal_records), 3,
                               f"Expected >= 3 signal records, got {len(self.signal_records)}")

    def test_22_signals_contain_required_fields(self):
        """Each signal must contain required anomaly fields."""
        required = [
            "card_family", "asset", "symbol", "price_change_24h_pct",
            "quote_volume_24h", "open_interest_current", "anomaly_type",
            "admission_passed", "confirmation_factors", "oi_history_missing",
        ]
        for sig in self.signal_records:
            for field in required:
                self.assertIn(field, sig,
                             f"Signal for {sig.get('asset', '?')} missing field: {field}")

    def test_23_signals_have_correct_card_family(self):
        """All signals must have card_family == price_oi_volume_anomaly."""
        for sig in self.signal_records:
            self.assertEqual(sig.get("card_family"), "price_oi_volume_anomaly",
                           f"Wrong card_family in signal for {sig.get('asset')}")

    # ══════════════════════════════════════════════════════════════════════
    # audit_result test
    # ══════════════════════════════════════════════════════════════════════

    def test_30_audit_result_is_allowed_value(self):
        """audit_result must be one of the 4 allowed values."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        audit = self.send_result.get("audit_result", "")
        self.assertIn(audit, ALLOWED_AUDIT_RESULTS,
                      f"audit_result '{audit}' not in allowed: {ALLOWED_AUDIT_RESULTS}")

    # ══════════════════════════════════════════════════════════════════════
    # v116G-specific: secret preflight tests
    # ══════════════════════════════════════════════════════════════════════

    def test_31_secret_preflight_run(self):
        """secret_preflight_run must be true — v116G mandatory step."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        preflight_run = self.send_result.get("secret_preflight_run", False)
        self.assertTrue(preflight_run,
                       "v116G requires secret_preflight_run == true")

    def test_32_preflight_boolean_flags_present(self):
        """Send result must have boolean flags for token/chat_id presence (not values)."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        bot_present = self.send_result.get("telegram_bot_token_present")
        chat_present = self.send_result.get("telegram_chat_id_present")
        self.assertIsInstance(bot_present, bool,
                            "telegram_bot_token_present must be a boolean")
        self.assertIsInstance(chat_present, bool,
                            "telegram_chat_id_present must be a boolean")

    # ══════════════════════════════════════════════════════════════════════
    # TG send / blocked reason tests
    # ══════════════════════════════════════════════════════════════════════

    def test_33_tg_attempt_has_required_fields(self):
        """TG send attempts must have attempted, target_type, one_shot fields."""
        for rec in self.tg_attempts:
            self.assertIn("attempted", rec, "Missing 'attempted' field")
            if rec.get("attempted", False):
                self.assertIn("target_type", rec, "Missing 'target_type' field")
                self.assertEqual(rec.get("target_type"), "test_group",
                               "target_type must be test_group")
                self.assertTrue(rec.get("one_shot", False),
                              "one_shot must be true")

    def test_34_tg_success_has_redacted_proof(self):
        """If TG sent successfully, must have redacted message proof."""
        for rec in self.tg_attempts:
            if rec.get("success", False):
                self.assertTrue(
                    rec.get("message_id_present", False),
                    "TG success must have message_id_present: true"
                )
                self.assertIsNotNone(
                    rec.get("message_id_redacted"),
                    "TG success must have message_id_redacted (NOT raw message_id)"
                )
                redacted = rec.get("message_id_redacted", "")
                self.assertTrue(
                    redacted.startswith("sha256:"),
                    f"message_id_redacted must be sha256 hashed, got: {redacted[:30]}"
                )

    def test_35_tg_blocked_has_real_reason(self):
        """If TG blocked, must have a real blocked_reason."""
        for rec in self.tg_attempts:
            if not rec.get("success", False) and rec.get("attempted", False):
                self.assertIn("blocked_reason", rec,
                            "Failed TG attempt missing 'blocked_reason'")
                self.assertIsNotNone(rec.get("blocked_reason"),
                                   "blocked_reason must not be None")

    def test_36_tg_blocked_not_masquerading_as_success(self):
        """TG blocked must have success: false, not true."""
        for rec in self.tg_attempts:
            if rec.get("blocked_reason"):
                self.assertFalse(rec.get("success", True),
                               f"Has blocked_reason '{rec.get('blocked_reason')}' but success=true")

    # ══════════════════════════════════════════════════════════════════════
    # Secret leak prevention tests (v116G critical)
    # ══════════════════════════════════════════════════════════════════════

    def test_40_no_forbidden_patterns_in_send_result(self):
        """Send result JSON must not contain token/key/password patterns."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            violations = check_no_forbidden_patterns(result_str)
            self.assertEqual(len(violations), 0,
                           f"Send result contains forbidden patterns: {violations}")

    def test_41_no_forbidden_patterns_in_report(self):
        """Report must not contain token/key/password patterns."""
        violations = check_no_forbidden_patterns(self.report_text)
        self.assertEqual(len(violations), 0,
                       f"Report contains forbidden patterns: {violations}")

    def test_42_no_forbidden_patterns_in_handoff(self):
        """Handoff must not contain token/key/password patterns."""
        violations = check_no_forbidden_patterns(self.handoff_text)
        self.assertEqual(len(violations), 0,
                       f"Handoff contains forbidden patterns: {violations}")

    def test_43_no_raw_token_in_send_result(self):
        """Send result must not contain raw TELEGRAM_BOT_TOKEN pattern."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            self.assertTrue(check_no_raw_token(result_str),
                           "Send result contains raw TELEGRAM_BOT_TOKEN pattern")

    def test_44_no_raw_chat_id_in_send_result(self):
        """Send result must not contain raw TELEGRAM_CHAT_ID assignment."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            self.assertTrue(check_no_raw_chat_id_assignment(result_str),
                           "Send result contains raw TELEGRAM_CHAT_ID")

    def test_45_no_raw_token_in_report(self):
        """Report must not contain raw TELEGRAM_BOT_TOKEN pattern."""
        self.assertTrue(check_no_raw_token(self.report_text),
                       "Report contains raw TELEGRAM_BOT_TOKEN pattern")

    def test_46_no_raw_chat_id_in_report(self):
        """Report must not contain raw TELEGRAM_CHAT_ID."""
        self.assertTrue(check_no_raw_chat_id_assignment(self.report_text),
                       "Report contains raw TELEGRAM_CHAT_ID")

    def test_47_no_raw_token_in_handoff(self):
        """Handoff must not contain raw TELEGRAM_BOT_TOKEN pattern."""
        self.assertTrue(check_no_raw_token(self.handoff_text),
                       "Handoff contains raw TELEGRAM_BOT_TOKEN pattern")

    def test_48_no_raw_chat_id_in_handoff(self):
        """Handoff must not contain raw TELEGRAM_CHAT_ID."""
        self.assertTrue(check_no_raw_chat_id_assignment(self.handoff_text),
                       "Handoff contains raw TELEGRAM_CHAT_ID")

    def test_49_all_outputs_clean(self):
        """All JSONL outputs must not contain forbidden patterns."""
        for path in [
            RAW_SNAPSHOTS_JSON, SIGNAL_RECORDS_JSONL, CARD_RECORDS_JSONL,
            QUALITY_GATE_JSONL, SEND_READINESS_JSONL, TG_SEND_ATTEMPTS_JSONL,
        ]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                violations = check_no_forbidden_patterns(content)
                self.assertEqual(len(violations), 0,
                               f"{path.name} contains forbidden patterns: {violations}")

    # ══════════════════════════════════════════════════════════════════════
    # Content quality and safety tests
    # ══════════════════════════════════════════════════════════════════════

    def test_50_report_mentions_preflight(self):
        """Report must mention safe secret preflight."""
        has_preflight = ("preflight" in self.report_text.lower() or
                        "secret" in self.report_text.lower())
        self.assertTrue(has_preflight,
                       "Report must mention safe secret preflight")

    def test_51_handoff_mentions_safety(self):
        """Handoff must include safety confirmation."""
        combined = (self.handoff_text + self.report_text).lower()
        has_safety = ("safety" in combined or "preflight" in combined or
                      "PASS" in self.handoff_text)
        self.assertTrue(has_safety,
                       "Handoff/report must include safety confirmation")

    def test_52_no_fixture_only_true(self):
        """No output should claim fixture_only: true."""
        for path in [SEND_RESULT_JSON, RAW_SNAPSHOTS_JSON]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixture_true_pattern = r'"fixture_only"\s*:\s*true'
                matches = re.findall(fixture_true_pattern, content, re.IGNORECASE)
                self.assertEqual(len(matches), 0,
                               f"{path.name} contains fixture_only: true")

    def test_53_report_or_handoff_mentions_one_shot(self):
        """Report or handoff must mention one-shot."""
        combined = (self.report_text + self.handoff_text).lower()
        has_oneshot = ("one-shot" in combined or "one_shot" in combined or "oneshot" in combined)
        self.assertTrue(has_oneshot,
                       "Must mention one-shot execution")

    def test_54_report_mentions_test_group(self):
        """Report must indicate test group (not production channel)."""
        has_test = ("test_group" in self.report_text.lower() or
                    "test group" in self.report_text.lower() or
                    "测试群" in self.report_text)
        self.assertTrue(has_test,
                       "Report must indicate test group context")

    def test_55_audit_result_in_report(self):
        """Report must contain the audit_result value."""
        if self.send_result:
            audit = self.send_result.get("audit_result", "")
            if audit:
                has_audit = audit.lower() in self.report_text.lower()
                self.assertTrue(has_audit,
                              f"Report must contain audit_result '{audit}'")

    def test_56_no_investment_advice_in_cards(self):
        """Cards must not contain investment advice phrases."""
        bad_phrases = ["买入", "卖出", "做多", "做空", "all in", "满仓", "清仓",
                       "必涨", "必跌", "稳赚", "抄底", "梭哈"]
        for card in self.card_records:
            card_text = card.get("card_text", "")
            for phrase in bad_phrases:
                self.assertNotIn(phrase, card_text,
                               f"Card for {card.get('asset', '?')} contains '{phrase}'")

    def test_57_signals_have_number_of_confirmation_factors(self):
        """Each signal's confirmation_factors should be a list."""
        for sig in self.signal_records:
            factors = sig.get("confirmation_factors", None)
            self.assertIsInstance(factors, list,
                                f"Signal for {sig.get('asset', '?')}: confirmation_factors must be a list")

    def test_58_no_production_send_ready_true(self):
        """No output should claim production_send_ready: true."""
        for path in [SEND_RESULT_JSON, SEND_READINESS_JSONL]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                prod_true_pattern = r'"production_send_ready"\s*:\s*true'
                matches = re.findall(prod_true_pattern, content, re.IGNORECASE)
                self.assertEqual(len(matches), 0,
                               f"{path.name} contains production_send_ready: true")

    def test_59_oi_history_missing_is_boolean(self):
        """oi_history_missing in signals must be a boolean."""
        for sig in self.signal_records:
            oi_missing = sig.get("oi_history_missing")
            self.assertIsInstance(oi_missing, bool,
                                f"Signal for {sig.get('asset', '?')}: oi_history_missing must be bool")

    def test_60_admission_passed_is_boolean(self):
        """admission_passed in signals must be a boolean."""
        for sig in self.signal_records:
            adm = sig.get("admission_passed")
            self.assertIsInstance(adm, bool,
                                f"Signal for {sig.get('asset', '?')}: admission_passed must be bool")


if __name__ == "__main__":
    unittest.main(verbosity=2)

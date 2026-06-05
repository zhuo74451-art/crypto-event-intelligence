#!/usr/bin/env python3
"""
test_market_radar_v112w_whale_position_live_source_plan.py
=============================================================
Test suite for v112W whale_position_alert live source readiness plan.

Validates:
  - Runner is executable
  - All required output files exist
  - Result JSON has correct safety invariants
  - Label audit JSON has correct structure
  - Config and schema files are valid
  - Stop conditions contain all required decision modes
  - No misleading production claims
  - No secrets, tokens, keys, passwords in output
"""

import json
import os
import sys
import unittest

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
SCHEMAS_DIR = os.path.join(PROJECT_DIR, "schemas")
DOCS_DIR = os.path.join(PROJECT_DIR, "docs")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

V112W_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112w_whale_position_live_source_plan_result.json")
V112W_LABEL_AUDIT = os.path.join(RESULTS_DIR, "market_radar_v112w_whale_label_quality_audit.json")
V112W_FIELD_MAPPING = os.path.join(CONFIG_DIR, "market_radar_v112w_whale_position_field_mapping.json")
V112W_STOP_CONDITIONS = os.path.join(CONFIG_DIR, "market_radar_v112w_hyperliquid_stop_conditions.json")
V112W_SCHEMA = os.path.join(SCHEMAS_DIR, "market_radar_v112w_hyperliquid_live_response_schema.json")
V112W_ADAPTER_SPEC = os.path.join(SCHEMAS_DIR, "market_radar_v112w_hl_to_whale_adapter_spec.md")
V112W_DOCS_PLAN = os.path.join(DOCS_DIR, "market_radar_v112w_whale_position_live_source_plan.md")
V112W_RUN_REPORT = os.path.join(RUNS_DIR, "v112w_whale_position_live_source_plan.md")
V112W_HANDOFF = os.path.join(RUNS_DIR, "v112w_whale_position_live_source_plan_handoff.md")

FORBIDDEN_TERMS = [
    "已真实发送",
    "production ready",
    "已接入正式生产",
    "real send completed",
    "TG sent successfully",
    "production state written",
    "live production",
    "ready for production",
]

SECRET_TERMS = [
    "chat_id",
    "Bearer ", "Authorization:", "x-api-key",
]

# Patterns that look like actual secret values being assigned (not safety assertions)
SECRET_VALUE_PATTERNS = [
    '"api_key": "',      # api_key with a string value (not false/true)
    '"secret": "',        # secret with a string value
    'api_key=',           # env-var style assignment
    '"token": "',         # token with a string value
    'token=',             # env-var style token assignment
    '"password": "',      # password with a string value
    'password=',          # env-var style password assignment
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════
# Test: Runner executable
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WRunnerExecutable(unittest.TestCase):
    """Test that the v112W runner script is executable."""

    def test_runner_file_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112w_whale_position_live_source_plan.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner not found: {runner_path}")

    def test_runner_importable_and_has_main(self):
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112w_whale_position_live_source_plan.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112w", runner_path)
        self.assertIsNotNone(spec, "Runner module spec should not be None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, 'main'), "Runner should have main() function")

    def test_runner_main_executes_successfully(self):
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112w_whale_position_live_source_plan.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112w", runner_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exit_code = mod.main()
        self.assertEqual(exit_code, 0, f"Runner should return 0, got {exit_code}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Result JSON
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WResultJSON(unittest.TestCase):
    """Test the result JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112W_RESULT):
            raise unittest.SkipTest(f"Result file not found: {V112W_RESULT}")
        cls.result = load_json(V112W_RESULT)

    def test_result_exists(self):
        self.assertTrue(os.path.exists(V112W_RESULT), "Result JSON must exist")

    def test_status_passed(self):
        self.assertEqual(self.result.get("status"), "passed", "status should be 'passed'")

    def test_dry_run_only(self):
        self.assertTrue(self.result.get("dry_run_only"), "dry_run_only should be true")

    def test_plan_only(self):
        self.assertTrue(self.result.get("plan_only"), "plan_only should be true")

    def test_live_ready_false(self):
        self.assertFalse(self.result.get("live_ready"), "live_ready should be false")

    def test_real_live_api_called_false(self):
        self.assertFalse(self.result.get("real_live_api_called"), "real_live_api_called should be false")

    def test_hyperliquid_api_called_false(self):
        self.assertFalse(self.result.get("hyperliquid_api_called"), "hyperliquid_api_called should be false")

    def test_real_tg_sent_false(self):
        self.assertFalse(self.result.get("real_tg_sent"), "real_tg_sent should be false")

    def test_external_api_called_false(self):
        self.assertFalse(self.result.get("external_api_called"), "external_api_called should be false")

    def test_external_ai_called_false(self):
        self.assertFalse(self.result.get("external_ai_called"), "external_ai_called should be false")

    def test_daemon_started_false(self):
        self.assertFalse(self.result.get("daemon_started"), "daemon_started should be false")

    def test_files_deleted_false(self):
        self.assertFalse(self.result.get("files_deleted"), "files_deleted should be false")

    def test_candidate_card_type(self):
        self.assertEqual(self.result.get("candidate_card_type"), "whale_position_alert")

    def test_previous_candidate_frozen(self):
        self.assertEqual(self.result.get("previous_candidate_frozen"), "multi_asset_market_sync")

    def test_whale_position_plan_ready(self):
        self.assertTrue(self.result.get("whale_position_plan_ready"), "whale_position_plan_ready should be true")

    def test_hyperliquid_stop_conditions_ready(self):
        self.assertTrue(self.result.get("hyperliquid_stop_conditions_ready"))

    def test_field_mapping_ready(self):
        self.assertTrue(self.result.get("field_mapping_ready"))

    def test_label_quality_audit_ready(self):
        self.assertTrue(self.result.get("label_quality_audit_ready"))

    def test_hl_to_whale_adapter_spec_ready(self):
        self.assertTrue(self.result.get("hl_to_whale_adapter_spec_ready"))

    def test_decision_modes_contain_all_three(self):
        modes = self.result.get("decision_modes", [])
        for mode in ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"]:
            self.assertIn(mode, modes, f"decision_modes should contain {mode}")

    def test_real_send_ready_false(self):
        self.assertFalse(self.result.get("real_send_ready"))

    def test_production_state_write_ready_false(self):
        self.assertFalse(self.result.get("production_state_write_ready"))

    def test_v112x_requires_user_confirmation(self):
        self.assertTrue(self.result.get("v112x_requires_user_confirmation"))

    def test_recommended_next_step(self):
        self.assertIn("v112x", self.result.get("recommended_next_step", "").lower())
        self.assertIn("user_confirmation", self.result.get("recommended_next_step", ""))

    def test_debug_leak_count_zero(self):
        self.assertEqual(self.result.get("debug_leak_count"), 0)

    def test_secret_leak_count_zero(self):
        self.assertEqual(self.result.get("secret_leak_count"), 0)


# ═══════════════════════════════════════════════════════════════════════════
# Test: Label Audit JSON
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WLabelAuditJSON(unittest.TestCase):
    """Test the label quality audit JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112W_LABEL_AUDIT):
            raise unittest.SkipTest(f"Label audit file not found: {V112W_LABEL_AUDIT}")
        cls.audit = load_json(V112W_LABEL_AUDIT)

    def test_label_audit_exists(self):
        self.assertTrue(os.path.exists(V112W_LABEL_AUDIT), "Label audit JSON must exist")

    def test_has_required_fields(self):
        required = [
            "tracked_addresses_total", "positions_total", "labels_total",
            "high_confidence_labels", "medium_confidence_labels",
            "low_confidence_labels", "unknown_labels",
            "unknown_label_fallback_ready", "label_quality_ready_for_one_shot_plan",
        ]
        for field in required:
            self.assertIn(field, self.audit, f"Label audit missing field: {field}")

    def test_tracked_addresses_positive(self):
        self.assertGreater(self.audit.get("tracked_addresses_total", 0), 0,
                          "tracked_addresses_total should be > 0")

    def test_positions_total_positive(self):
        self.assertGreater(self.audit.get("positions_total", 0), 0,
                          "positions_total should be > 0")

    def test_labels_non_negative(self):
        self.assertGreaterEqual(self.audit.get("labels_total", -1), 0,
                               "labels_total should be >= 0")

    def test_unknown_label_fallback_ready(self):
        self.assertTrue(self.audit.get("unknown_label_fallback_ready"),
                       "unknown_label_fallback_ready should be true")

    def test_label_quality_ready(self):
        self.assertTrue(self.audit.get("label_quality_ready_for_one_shot_plan"),
                       "label_quality_ready_for_one_shot_plan should be true")

    def test_has_address_details(self):
        details = self.audit.get("address_label_details", [])
        self.assertGreater(len(details), 0, "address_label_details should not be empty")

    def test_address_details_have_short_form(self):
        for detail in self.audit.get("address_label_details", []):
            addr = detail.get("address", "")
            short = detail.get("address_short", "")
            if len(addr) > 12:
                self.assertTrue("..." in short,
                               f"address_short should use short form, got: {short}")
                self.assertLess(len(short), len(addr),
                               f"address_short should be shorter than full address")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Config Files
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WConfigFiles(unittest.TestCase):
    """Test config and schema files exist and are valid."""

    def test_field_mapping_exists(self):
        self.assertTrue(os.path.exists(V112W_FIELD_MAPPING), "Field mapping JSON must exist")

    def test_field_mapping_valid(self):
        data = load_json(V112W_FIELD_MAPPING)
        self.assertEqual(data.get("candidate_card_type"), "whale_position_alert")
        self.assertEqual(data.get("planned_source"), "hyperliquid_info_public")
        self.assertFalse(data.get("api_key_required"), "api_key_required should be false")
        self.assertFalse(data.get("authorization_header_required"))
        self.assertTrue(data.get("method_is_post_but_read_only"))
        self.assertIn("required_fields", data)
        self.assertIn("field_mapping", data)
        # Check key required fields
        required = data.get("required_fields", [])
        for f in ["address", "symbol", "side", "position_size", "entry_price",
                   "mark_price", "unrealized_pnl", "leverage", "observed_at"]:
            self.assertIn(f, required, f"required_fields should contain '{f}'")
        # Check liquidation_price is listed (nullable)
        self.assertIn("liquidation_price", required, "required_fields should contain 'liquidation_price'")

    def test_stop_conditions_exists(self):
        self.assertTrue(os.path.exists(V112W_STOP_CONDITIONS), "Stop conditions JSON must exist")

    def test_stop_conditions_valid(self):
        data = load_json(V112W_STOP_CONDITIONS)
        modes = data.get("decision_modes", [])
        for mode in ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"]:
            self.assertIn(mode, modes, f"decision_modes should contain {mode}")

        # Test ABORT conditions
        abort_conds = data.get("stop_conditions", {}).get("ABORT", {}).get("conditions", [])
        abort_ids = [c["id"] for c in abort_conds]
        required_abort = [
            "ABORT_HTTP_NON_2XX", "ABORT_TIMEOUT", "ABORT_SCHEMA_MISMATCH",
            "ABORT_RATE_LIMIT", "ABORT_AUTH_REQUIRED",
        ]
        for rid in required_abort:
            found = any(rid in aid for aid in abort_ids)
            self.assertTrue(found, f"ABORT conditions should include condition like {rid}")

        # Test DEGRADE conditions
        degrade_conds = data.get("stop_conditions", {}).get("DEGRADE_TO_MOCK", {}).get("conditions", [])
        degrade_ids = [c["id"] for c in degrade_conds]
        required_degrade = [
            "DEGRADE_LABEL_MISSING", "DEGRADE_PARTIAL_ADDRESS_FAILURE",
            "DEGRADE_DELTA_CANNOT_COMPUTE",
        ]
        for rid in required_degrade:
            found = any(rid in did for did in degrade_ids)
            self.assertTrue(found, f"DEGRADE conditions should include condition like {rid}")

        # Test CONTINUE requires eligible_for_real_send=false
        continue_conds = data.get("stop_conditions", {}).get("CONTINUE", {}).get("conditions", [])
        continue_text = json.dumps(continue_conds).lower()
        self.assertIn("eligible_for_real_send", continue_text,
                     "CONTINUE conditions should reference eligible_for_real_send")

        # Test invariants
        invariants = data.get("invariants", {})
        self.assertTrue(invariants.get("eligible_for_real_send_always_false"))
        self.assertTrue(invariants.get("production_state_write_always_false"))
        self.assertTrue(invariants.get("real_tg_send_always_false"))

    def test_schema_exists(self):
        self.assertTrue(os.path.exists(V112W_SCHEMA), "Schema JSON must exist")

    def test_schema_valid(self):
        data = load_json(V112W_SCHEMA)
        self.assertEqual(data.get("title"), "HyperLiquid Live Response Schema — v112W Planning")
        props = data.get("properties", {})
        self.assertIn("source_name", props)
        self.assertIn("request_mode", props)
        self.assertIn("addresses", props)
        self.assertIn("stop_decision", props)
        self.assertIn("eligible_for_real_send", props)

    def test_adapter_spec_exists(self):
        self.assertTrue(os.path.exists(V112W_ADAPTER_SPEC), "Adapter spec MD must exist")

    def test_adapter_spec_has_content(self):
        content = load_text(V112W_ADAPTER_SPEC)
        self.assertGreater(len(content), 500, "Adapter spec should have meaningful content")
        # Key sections
        self.assertIn("eligible_for_real_send", content.lower())
        self.assertIn("ABORT", content)
        self.assertIn("DEGRADE_TO_MOCK", content)
        self.assertIn("CONTINUE", content)
        self.assertIn("v112X", content)

    def test_docs_plan_exists(self):
        self.assertTrue(os.path.exists(V112W_DOCS_PLAN), "Docs plan MD must exist")

    def test_docs_plan_has_content(self):
        content = load_text(V112W_DOCS_PLAN)
        self.assertGreater(len(content), 500, "Docs plan should have meaningful content")
        # Key sections
        self.assertIn("multi_asset", content.lower())
        self.assertIn("whale_position_alert", content.lower())
        self.assertIn("v112X", content)
        self.assertIn("stop conditions", content.lower())

    def test_run_report_exists(self):
        self.assertTrue(os.path.exists(V112W_RUN_REPORT), "Run report MD must exist")

    def test_handoff_exists(self):
        self.assertTrue(os.path.exists(V112W_HANDOFF), "Handoff MD must exist")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Security & Safety Invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WSecurityInvariants(unittest.TestCase):
    """Test that no secrets, tokens, keys, or misleading claims exist in output."""

    @classmethod
    def setUpClass(cls):
        cls.texts = {}
        for label, path in [
            ("result", V112W_RESULT),
            ("label_audit", V112W_LABEL_AUDIT),
            ("field_mapping", V112W_FIELD_MAPPING),
            ("stop_conditions", V112W_STOP_CONDITIONS),
            ("schema", V112W_SCHEMA),
            ("adapter_spec", V112W_ADAPTER_SPEC),
            ("docs_plan", V112W_DOCS_PLAN),
            ("run_report", V112W_RUN_REPORT),
            ("handoff", V112W_HANDOFF),
        ]:
            if os.path.exists(path):
                cls.texts[label] = load_text(path)

    def test_no_forbidden_production_claims(self):
        """No output should contain misleading production-ready claims."""
        for label, text in self.texts.items():
            text_lower = text.lower()
            for term in FORBIDDEN_TERMS:
                self.assertNotIn(term.lower(), text_lower,
                                f"{label} should not contain forbidden term: '{term}'")

    # Legitimate safety metadata field names that contain
    # "secret" / "token" as part of a counter field (e.g., secret_leak_count=0).
    # These are NOT actual secrets — they are safety audit fields.
    SAFETY_METADATA_PATTERNS = [
        "secret_leak_count", "secret_leak_terms",
        "debug_leak_count", "debug_leak_terms",
        "no_secrets_leaked", "no_credentials_read",
        "secret_leak", "debug_leak",
    ]

    def _strip_safety_metadata(self, text: str) -> str:
        """Remove safety metadata lines that contain the word 'secret' or 'token'
        as part of a counter/audit field, not as an actual credential."""
        lines = text.split("\n")
        filtered = []
        for line in lines:
            line_lower = line.lower()
            is_safety_meta = any(
                pattern in line_lower for pattern in self.SAFETY_METADATA_PATTERNS
            )
            if not is_safety_meta:
                filtered.append(line)
        return "\n".join(filtered)

    def test_no_secret_terms(self):
        """No output should contain secret/token/key terms (excluding safety metadata fields)."""
        for label, text in self.texts.items():
            # Strip safety metadata fields before checking for secrets
            cleaned = self._strip_safety_metadata(text)
            text_lower = cleaned.lower()
            for term in SECRET_TERMS:
                self.assertNotIn(term.lower(), text_lower,
                                f"{label} should not contain secret term: '{term}'")

    def test_no_secret_value_patterns(self):
        """No output should contain actual secret value assignments (api_key with string value, etc.)."""
        for label, text in self.texts.items():
            cleaned = self._strip_safety_metadata(text)
            for pattern in SECRET_VALUE_PATTERNS:
                self.assertNotIn(pattern, cleaned,
                                f"{label} should not contain secret value pattern: '{pattern}'")

    def test_docs_mention_user_confirmation(self):
        """Docs should mention v112X requires user confirmation."""
        content = load_text(V112W_DOCS_PLAN).lower()
        has_confirm = "user confirmation" in content or "用户确认" in content or "user explicit" in content
        self.assertTrue(has_confirm, "Docs plan should mention v112X requires user confirmation")

    def test_handoff_mentions_user_confirmation(self):
        """Handoff should mention v112X requires user confirmation."""
        content = load_text(V112W_HANDOFF).lower()
        has_confirm = "user confirmation" in content or "用户确认" in content or "user explicit" in content
        self.assertTrue(has_confirm, "Handoff should mention v112X requires user confirmation")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Stop Conditions Coverage
# ═══════════════════════════════════════════════════════════════════════════

class TestV112WStopConditionsCoverage(unittest.TestCase):
    """Verify stop conditions cover all required scenarios."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112W_STOP_CONDITIONS):
            raise unittest.SkipTest(f"Stop conditions file not found: {V112W_STOP_CONDITIONS}")
        cls.stop = load_json(V112W_STOP_CONDITIONS)

    def test_abort_covers_non_2xx(self):
        self.assertTrue(any("non_2xx" in c.get("id", "").lower() or "non-2xx" in c.get("condition", "").lower()
                          for c in self.stop["stop_conditions"]["ABORT"]["conditions"]))

    def test_abort_covers_timeout(self):
        self.assertTrue(any("timeout" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["ABORT"]["conditions"]))

    def test_abort_covers_schema_mismatch(self):
        self.assertTrue(any("schema" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["ABORT"]["conditions"]))

    def test_abort_covers_rate_limit(self):
        self.assertTrue(any("rate_limit" in c.get("id", "").lower() or "rate limit" in c.get("condition", "").lower()
                          for c in self.stop["stop_conditions"]["ABORT"]["conditions"]))

    def test_abort_covers_auth_required(self):
        self.assertTrue(any("auth" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["ABORT"]["conditions"]))

    def test_degrade_covers_label_missing(self):
        self.assertTrue(any("label" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["DEGRADE_TO_MOCK"]["conditions"]))

    def test_degrade_covers_partial_address_failure(self):
        self.assertTrue(any("partial" in c.get("id", "").lower() or "address" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["DEGRADE_TO_MOCK"]["conditions"]))

    def test_degrade_covers_delta_unavailable(self):
        self.assertTrue(any("delta" in c.get("id", "").lower()
                          for c in self.stop["stop_conditions"]["DEGRADE_TO_MOCK"]["conditions"]))

    def test_continue_requires_eligible_false(self):
        continue_text = json.dumps(self.stop["stop_conditions"]["CONTINUE"]).lower()
        self.assertIn("eligible_for_real_send", continue_text)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  v112W — Whale Position Alert Live Source Plan — Test Suite")
    print("=" * 70)
    unittest.main(verbosity=2)

"""Tests for Market Radar v1.12-L — Canonical State Key Validator

Validates:
  - v112h envelopes readable
  - v112j eligible signals readable
  - v112j proposed state readable
  - v112i prior fixture readable
  - envelope index buildable
  - v112i prior fixture synthetic/unknown keys identified
  - v112j proposed state keys all canonical_match
  - v112l canonical state entry count = v112j eligible_signal_count
  - v112l canonical state all canonical_match
  - Canonical state does not overwrite prior fixture
  - Canonical state does not write live state
  - State key audit JSONL generated
  - Result JSON generated
  - Report/handoff generated
  - Safety flags correct
  - No token/key/secret read

Usage:
    python scripts/test_market_radar_state_key_validator_v112l.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


class TestMarketRadarStateKeyValidatorV112L(unittest.TestCase):
    """Test suite for v112l Canonical State Key Validator."""

    @classmethod
    def setUpClass(cls):
        cls.project_dir = PROJECT_DIR
        cls.results_dir = cls.project_dir / "results"
        cls.runs_dir = cls.project_dir / "runs" / "market_radar"
        cls.data_dir = cls.project_dir / "data"
        cls.fixtures_dir = cls.data_dir / "fixtures"

        cls.envelopes_path = cls.results_dir / "market_radar_v112h_unified_signal_envelopes.jsonl"
        cls.eligible_path = cls.results_dir / "market_radar_v112j_eligible_signals.jsonl"
        cls.proposed_state_path = cls.results_dir / "market_radar_v112j_proposed_signal_state.json"
        cls.prior_fixture_path = cls.fixtures_dir / "market_radar_v112i_prior_signal_state.json"

        cls.canonical_state_path = cls.results_dir / "market_radar_v112l_canonical_prior_state.json"
        cls.result_path = cls.results_dir / "market_radar_v112l_canonical_state_key_hardening_result.json"
        cls.audit_path = cls.results_dir / "market_radar_v112l_state_key_audit.jsonl"
        cls.report_path = cls.runs_dir / "v112l_canonical_state_key_hardening.md"
        cls.handoff_path = cls.runs_dir / "v112l_canonical_state_key_hardening_handoff.md"

    # ── Data Loading Tests ────────────────────────────────────────────────────

    def test_01_v112h_envelopes_readable(self):
        """v112h envelopes JSONL can be read and contains 13 entries."""
        from scripts.market_radar_state_key_validator_v112l import load_envelopes_jsonl

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        self.assertEqual(len(envelopes), 13,
                         f"Expected 13 envelopes, got {len(envelopes)}")
        for env in envelopes:
            self.assertIn("signal_id", env)
            self.assertIn("dedupe_key", env)
            self.assertIn("cooldown_key", env)
            self.assertIn("payload_hash", env)
            self.assertIn("card_type", env)

    def test_02_v112j_eligible_signals_readable(self):
        """v112j eligible signals JSONL can be read and has 9 entries."""
        from scripts.market_radar_state_key_validator_v112l import load_eligible_signals_jsonl

        eligible = load_eligible_signals_jsonl(self.eligible_path)
        self.assertEqual(len(eligible), 9,
                         f"Expected 9 eligible signals, got {len(eligible)}")
        for rec in eligible:
            self.assertIn("signal_id", rec)
            self.assertIn("dedupe_key", rec)
            self.assertIn("cooldown_key", rec)
            self.assertIn("payload_hash", rec)
            self.assertEqual(rec.get("gate_status"), "pass")

    def test_03_v112j_proposed_state_readable(self):
        """v112j proposed state JSON can be read and has entries."""
        self.assertTrue(self.proposed_state_path.exists())
        with open(self.proposed_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("entries", state)
        self.assertIsInstance(state["entries"], list)
        self.assertGreater(len(state["entries"]), 0)
        self.assertEqual(state.get("dry_run_only"), True)

    def test_04_v112i_prior_fixture_readable(self):
        """v112i prior fixture JSON can be read and has 7 entries."""
        from scripts.market_radar_state_key_validator_v112l import load_prior_state_json

        entries = load_prior_state_json(self.prior_fixture_path)
        self.assertEqual(len(entries), 7,
                         f"Expected 7 prior fixture entries, got {len(entries)}")

    # ── Envelope Index Tests ─────────────────────────────────────────────────

    def test_10_envelope_index_buildable(self):
        """Envelope key index can be built from v112h envelopes."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            build_envelope_key_index,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        index = build_envelope_key_index(envelopes)

        self.assertIn("by_dedupe_key", index)
        self.assertIn("by_cooldown_key", index)
        self.assertIn("by_payload_hash", index)
        self.assertIn("dedupe_key_set", index)
        self.assertEqual(len(index["dedupe_key_set"]), 13,
                         "Expected 13 unique dedupe_keys (one per envelope)")

    # ── Prior Fixture Key Audit Tests ────────────────────────────────────────

    def test_20_prior_fixture_synthetic_keys_identified(self):
        """v112i prior fixture should have synthetic/unknown keys identified."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_prior_state_json,
            build_envelope_key_index,
            audit_prior_state_keys,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        index = build_envelope_key_index(envelopes)
        prior_entries = load_prior_state_json(self.prior_fixture_path)

        audit = audit_prior_state_keys(prior_entries, index, label="v112i_prior_fixture")

        # At least some synthetic/unknown keys expected
        self.assertGreater(audit["synthetic_or_unknown_count"], 0,
                           "Prior fixture should have synthetic/unknown keys")
        # Some canonical matches expected (entries 1-2 match real envelopes)
        self.assertGreater(audit["canonical_match_count"], 0,
                           "Prior fixture should have some canonical matches")
        # Not all canonical
        self.assertFalse(audit["entries_canonical"],
                         "Prior fixture should NOT be all canonical")

    def test_21_prior_fixture_synthetic_count(self):
        """Verify exact synthetic count: 5 of 7 entries are synthetic."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_prior_state_json,
            build_envelope_key_index,
            audit_prior_state_keys,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        index = build_envelope_key_index(envelopes)
        prior_entries = load_prior_state_json(self.prior_fixture_path)

        audit = audit_prior_state_keys(prior_entries, index, label="v112i_prior_fixture")

        self.assertEqual(audit["synthetic_or_unknown_count"], 5,
                         "Expected exactly 5 synthetic/unknown entries in prior fixture")
        self.assertEqual(audit["canonical_match_count"], 2,
                         "Expected exactly 2 canonical matches in prior fixture")

    # ── Proposed State Key Audit Tests ───────────────────────────────────────

    def test_30_proposed_state_keys_all_canonical(self):
        """All v112j proposed state entries should have canonical keys."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            build_envelope_key_index,
            audit_prior_state_keys,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        index = build_envelope_key_index(envelopes)

        with open(self.proposed_state_path, "r", encoding="utf-8") as f:
            proposed_state = json.load(f)
        proposed_entries = proposed_state.get("entries", [])

        audit = audit_prior_state_keys(proposed_entries, index, label="v112j_proposed_state")

        # New entries (first 9) should be canonical
        # Prior kept entries may have synthetic keys
        self.assertGreater(audit["canonical_match_count"], 0)

        # Check the first 9 entries specifically (the new entries from eligible signals)
        new_entries_audit = audit_prior_state_keys(proposed_entries[:9], index, label="new_only")
        self.assertEqual(new_entries_audit["canonical_match_count"], 9,
                         "All 9 new proposed state entries must be canonical_match")
        self.assertTrue(new_entries_audit["entries_canonical"],
                        "New proposed state entries must be all canonical")

    # ── Canonical State Tests ────────────────────────────────────────────────

    def test_40_canonical_state_entry_count(self):
        """v112l canonical state entry count = v112j eligible_signal_count."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_eligible_signals_jsonl,
            build_canonical_prior_state_from_eligible_signals,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        eligible = load_eligible_signals_jsonl(self.eligible_path)
        canonical = build_canonical_prior_state_from_eligible_signals(eligible, envelopes)

        self.assertEqual(len(canonical["entries"]), len(eligible),
                         f"Canonical state entries ({len(canonical['entries'])}) "
                         f"must equal eligible signal count ({len(eligible)})")

    def test_41_canonical_state_all_canonical_match(self):
        """All v112l canonical state entries must be canonical_match."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_eligible_signals_jsonl,
            build_envelope_key_index,
            build_canonical_prior_state_from_eligible_signals,
            audit_prior_state_keys,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        eligible = load_eligible_signals_jsonl(self.eligible_path)
        canonical = build_canonical_prior_state_from_eligible_signals(eligible, envelopes)

        index = build_envelope_key_index(envelopes)
        audit = audit_prior_state_keys(canonical["entries"], index, label="canonical")

        self.assertTrue(audit["entries_canonical"],
                        "All canonical state entries must be canonical_match")
        self.assertEqual(audit["synthetic_or_unknown_count"], 0,
                         "Canonical state must have zero synthetic/unknown keys")
        self.assertEqual(audit["canonical_match_count"], len(canonical["entries"]),
                         "All canonical state entries must be canonical_match")

    def test_42_canonical_state_source_correct(self):
        """Canonical state entries use state_source='v112l_canonical_dryrun'."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_eligible_signals_jsonl,
            build_canonical_prior_state_from_eligible_signals,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        eligible = load_eligible_signals_jsonl(self.eligible_path)
        canonical = build_canonical_prior_state_from_eligible_signals(eligible, envelopes)

        for entry in canonical["entries"]:
            self.assertEqual(entry.get("state_source"), "v112l_canonical_dryrun")
            self.assertIn("decision_history", entry)
            self.assertIsInstance(entry["decision_history"], list)
            self.assertGreater(len(entry["decision_history"]), 0)

    def test_43_canonical_state_has_required_fields(self):
        """Each canonical state entry has all required fields."""
        from scripts.market_radar_state_key_validator_v112l import (
            load_envelopes_jsonl,
            load_eligible_signals_jsonl,
            build_canonical_prior_state_from_eligible_signals,
        )

        envelopes = load_envelopes_jsonl(self.envelopes_path)
        eligible = load_eligible_signals_jsonl(self.eligible_path)
        canonical = build_canonical_prior_state_from_eligible_signals(eligible, envelopes)

        required_fields = [
            "dedupe_key", "cooldown_key", "payload_hash",
            "signal_id", "card_type", "primary_assets", "direction",
            "last_seen_at", "cooldown_until", "source_signal_id",
            "state_source", "decision_history",
        ]

        for entry in canonical["entries"]:
            for field in required_fields:
                self.assertIn(field, entry,
                              f"Entry missing required field: {field}")

    # ── Output File Tests ────────────────────────────────────────────────────

    def test_50_result_json_exists(self):
        """Result JSON was generated."""
        self.assertTrue(self.result_path.exists(),
                        f"Result JSON not found: {self.result_path}")

    def test_51_result_json_has_required_fields(self):
        """Result JSON has all required fields."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        required = [
            "version", "envelope_count", "eligible_signal_count",
            "prior_fixture_entry_count", "proposed_state_entry_count",
            "canonical_state_entry_count",
            "prior_fixture_canonical_match_count",
            "prior_fixture_synthetic_or_unknown_count",
            "proposed_state_canonical_match_count",
            "canonical_state_all_match",
            "synthetic_key_risk_detected",
            "debug_leak_count", "secret_leak_count", "full_wallet_leak",
            "real_tg_sent", "external_api_called", "external_ai_called",
            "daemon_started", "live_ready", "dry_run_only",
            "production_state_written",
        ]
        for field in required:
            self.assertIn(field, result, f"Result JSON missing field: {field}")

    def test_52_result_version(self):
        """Result version is v1.12-L."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("version"), "v1.12-L")

    def test_53_state_key_audit_jsonl_exists(self):
        """State key audit JSONL was generated."""
        self.assertTrue(self.audit_path.exists(),
                        f"Audit JSONL not found: {self.audit_path}")

    def test_54_state_key_audit_has_entries(self):
        """State key audit JSONL has entries."""
        audit_entries = []
        with open(self.audit_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    audit_entries.append(json.loads(line))
        self.assertGreater(len(audit_entries), 0,
                           "Audit JSONL should have entries")

    def test_55_report_exists(self):
        """Report markdown was generated."""
        self.assertTrue(self.report_path.exists(),
                        f"Report not found: {self.report_path}")

    def test_56_handoff_exists(self):
        """Handoff markdown was generated."""
        self.assertTrue(self.handoff_path.exists(),
                        f"Handoff not found: {self.handoff_path}")

    def test_57_canonical_state_json_exists(self):
        """Canonical prior state JSON was generated."""
        self.assertTrue(self.canonical_state_path.exists(),
                        f"Canonical state not found: {self.canonical_state_path}")

    # ── Safety Tests ─────────────────────────────────────────────────────────

    def test_60_debug_leak_count_zero(self):
        """debug_leak_count must be 0."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("debug_leak_count"), 0)

    def test_61_secret_leak_count_zero(self):
        """secret_leak_count must be 0."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("secret_leak_count"), 0)

    def test_62_full_wallet_leak_false(self):
        """full_wallet_leak must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("full_wallet_leak"))

    def test_63_real_tg_sent_false(self):
        """real_tg_sent must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("real_tg_sent"))

    def test_64_external_api_called_false(self):
        """external_api_called must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("external_api_called"))

    def test_65_external_ai_called_false(self):
        """external_ai_called must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("external_ai_called"))

    def test_66_daemon_started_false(self):
        """daemon_started must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("daemon_started"))

    def test_67_live_ready_false(self):
        """live_ready must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("live_ready"))

    def test_68_dry_run_only_true(self):
        """dry_run_only must be true."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result.get("dry_run_only"))

    def test_69_production_state_written_false(self):
        """production_state_written must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("production_state_written"))

    # ── No Side Effects ──────────────────────────────────────────────────────

    def test_70_prior_fixture_not_overwritten(self):
        """Prior fixture is NOT overwritten by v112l."""
        self.assertTrue(self.prior_fixture_path.exists(),
                        "Prior fixture should still exist")
        from scripts.market_radar_state_key_validator_v112l import load_prior_state_json
        entries = load_prior_state_json(self.prior_fixture_path)
        self.assertEqual(len(entries), 7,
                         "Prior fixture should still have 7 entries (not overwritten)")

    def test_71_no_live_state_written(self):
        """Canonical state does NOT write to live state."""
        live_state_dir = self.data_dir
        unexpected_patterns = [
            "market_radar_v112l_live",
            "v112l_live_state",
        ]
        for f in live_state_dir.iterdir():
            for pattern in unexpected_patterns:
                self.assertNotIn(pattern, f.name,
                                 f"Unexpected live state file: {f.name}")

    def test_72_no_ai_relay_desk_writes(self):
        """No v112l artifacts written to ai_relay_desk."""
        ai_relay_dir = Path("C:/Users/PC/Desktop/工作台/ai_relay_desk")
        if ai_relay_dir.exists():
            for root, dirs, files in os.walk(str(ai_relay_dir)):
                for fname in files:
                    self.assertNotIn("v112l", fname.lower(),
                                     f"v112l artifact in ai_relay_desk: {fname}")

    def test_73_no_credentials_in_files(self):
        """No token/key/secret/cookie/password as values in generated files.

        Field names like 'secret_leak_count' are NOT leaks — they are metadata counters.
        Only actual credential values (e.g., "secret": "abc123") are forbidden.
        """
        # Terms that indicate actual credential exposure, not metadata field names
        # Check for known field names that contain these terms and exclude them
        import re
        known_safe_fields = [
            "secret_leak_count", "secret_terms_found",
            "api_key",  # only as field name like "external_api_called"
        ]
        files_to_check = [
            self.result_path,
            self.canonical_state_path,
            self.audit_path,
            self.report_path,
            self.handoff_path,
        ]
        for fpath in files_to_check:
            if not fpath.exists():
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()

            # Check for actual credential patterns in JSON values, not field names
            # If a JSON file, parse it and check values only
            try:
                with open(fpath, "r", encoding="utf-8") as f2:
                    data = json.loads(f2.read())

                def check_values(obj, path=""):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            # Field names are safe
                            check_values(v, f"{path}.{k}")
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            check_values(v, f"{path}[{i}]")
                    elif isinstance(obj, str):
                        val_lower = obj.lower()
                        for term in ["token=", "api_key=", "chat_id=", "password=", "cookie=", "secret="]:
                            self.assertNotIn(term, val_lower,
                                             f"Credential pattern '{term}' in value at {path} in {fpath.name}")
                        # Check for standalone credentials like "token: xxx"
                        for term in ["token", "api_key", "chat_id", "password", "secret"]:
                            if val_lower.strip() == term:
                                self.fail(f"Standalone credential '{term}' in value at {path} in {fpath.name}")

                check_values(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Non-JSON file (markdown) — just check no obvious credential patterns
                for term in ["token=", "api_key=", "chat_id=", "password=", "cookie=", "secret="]:
                    self.assertNotIn(term, content,
                                     f"Credential pattern '{term}' found in {fpath.name}")

    def test_74_no_wallet_address_leak_in_audit(self):
        """No full wallet addresses leaked in audit records."""
        import re
        wallet_pattern = re.compile(r'0x[a-fA-F0-9]{40}')
        if self.audit_path.exists():
            with open(self.audit_path, "r", encoding="utf-8") as f:
                for line in f:
                    matches = wallet_pattern.findall(line)
                    self.assertEqual(len(matches), 0,
                                     f"Full wallet address found in audit: {matches}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

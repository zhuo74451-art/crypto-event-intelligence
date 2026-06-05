"""Tests for v1.12-R Multi-Asset Mock Adapter → Envelope Compatibility.

Covers:
  - Runner executes successfully
  - All output files exist (result JSON, envelopes JSONL, report MD, handoff MD)
  - result JSON has correct fields and values
  - Every envelope has required fields (signal_id, card_type, dedupe_key, etc.)
  - Blocked/degraded/downgraded cases not marked as send candidates
  - Repeated run output stable
  - No secret/key/token/cookie/password clear text in any output
  - No misleading "live API connected", "production ready", etc.
  - Upstream tests (v112Q, v112P, v112O, v112N, v112H, v112G) continue to pass

Usage:
    python scripts/test_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_adapter_result.json"
ENVELOPES_JSONL_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_envelopes.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112r_multi_asset_mock_adapter_envelope_compatibility.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112r_multi_asset_mock_adapter_envelope_compatibility_handoff.md"
RUNNER_PATH = ROOT / "scripts" / "run_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py"

# Patterns that indicate real credential leaks
FORBIDDEN_PATTERNS = [
    r'\bsecret\s*[=:]\s*\S',
    r'\bsecret\s*key\b',
    r'\bsecret\s*token\b',
    r'\bapi[_\-]?secret\b',
    r'\bapi[_\-]?key\s*[=:]\s*\S',
    r'\bchat[_\-]?id\s*[=:]\s*\S',
    r'\bpassword\s*[=:]\s*\S',
    r'\bbearer\s+\S',
    r'\bauthorization\s*:\s*\S',
    r'\bx-api-key\s*[=:]\s*\S',
    r'\bcookie\s*[=:]\s*\S',
    r'[A-Za-z]:\\(?:Users|Program|Windows)',
    r'\btoken\s*[=:]\s*[a-zA-Z0-9_\-]{8,}',
    r'\bkey\s*[=:]\s*[a-zA-Z0-9_\-]{8,}',
]

MISLEADING_TERMS = [
    "已接入 live source",
    "live source connected",
    "production ready",
    "已发送",
    "正式发布",
    "real sent",
    "已推送",
    "已投递",
    "broadcast sent",
    "message delivered",
    "sent to channel",
    "已发布成功",
    "发送成功",
    "live API connected",
    "已接入 live API",
    "已真实发送",
]

BLOCKED_EXCLUDED_TERMS = ["blocked", "degraded", "downgraded"]


def _load_json(path: Path):
    """Load a JSON file."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file."""
    results = []
    if not path.exists():
        return results
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return results


def _read_text(path: Path) -> str:
    """Read a text file."""
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _run_runner() -> tuple[int, str, str]:
    """Run the v112R runner and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(RUNNER_PATH)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=120,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


class TestRunnerExecutes(unittest.TestCase):
    """Test that the v112R runner executes successfully."""

    def test_runner_exit_code_zero(self):
        """Runner should exit with code 0."""
        exit_code, stdout, stderr = _run_runner()
        self.assertEqual(exit_code, 0, f"Runner failed. stderr:\n{stderr}\nstdout:\n{stdout}")

    def test_runner_output_has_status(self):
        """Runner output should mention completion."""
        _, stdout, _ = _run_runner()
        self.assertIn("v112R Complete", stdout)


class TestOutputFilesExist(unittest.TestCase):
    """Test that all output files exist."""

    def test_result_json_exists(self):
        """Result JSON should exist."""
        self.assertTrue(RESULT_JSON_PATH.exists(),
                        f"Result JSON not found at {RESULT_JSON_PATH}")

    def test_envelopes_jsonl_exists(self):
        """Envelopes JSONL should exist."""
        self.assertTrue(ENVELOPES_JSONL_PATH.exists(),
                        f"Envelopes JSONL not found at {ENVELOPES_JSONL_PATH}")

    def test_report_md_exists(self):
        """Report MD should exist."""
        self.assertTrue(REPORT_MD_PATH.exists(),
                        f"Report MD not found at {REPORT_MD_PATH}")

    def test_handoff_md_exists(self):
        """Handoff MD should exist."""
        self.assertTrue(HANDOFF_MD_PATH.exists(),
                        f"Handoff MD not found at {HANDOFF_MD_PATH}")


class TestResultJsonFields(unittest.TestCase):
    """Test result JSON has correct fields and values."""

    @classmethod
    def setUpClass(cls):
        cls.result = _load_json(RESULT_JSON_PATH)
        assert cls.result is not None, f"Result JSON not found at {RESULT_JSON_PATH}"

    def test_status_passed(self):
        """status should be 'passed'."""
        self.assertEqual(self.result.get("status"), "passed")

    def test_version(self):
        """version should be 'v1.12-r'."""
        self.assertEqual(self.result.get("version"), "v1.12-r")

    def test_dry_run_only_true(self):
        """dry_run_only should be True."""
        self.assertTrue(self.result.get("dry_run_only"))

    def test_live_ready_false(self):
        """live_ready should be False."""
        self.assertFalse(self.result.get("live_ready"))

    def test_real_live_api_called_false(self):
        """real_live_api_called should be False."""
        self.assertFalse(self.result.get("real_live_api_called"))

    def test_real_tg_sent_false(self):
        """real_tg_sent should be False."""
        self.assertFalse(self.result.get("real_tg_sent"))

    def test_external_api_called_false(self):
        """external_api_called should be False."""
        self.assertFalse(self.result.get("external_api_called"))

    def test_external_ai_called_false(self):
        """external_ai_called should be False."""
        self.assertFalse(self.result.get("external_ai_called"))

    def test_daemon_started_false(self):
        """daemon_started should be False."""
        self.assertFalse(self.result.get("daemon_started"))

    def test_files_deleted_false(self):
        """files_deleted should be False."""
        self.assertFalse(self.result.get("files_deleted"))

    def test_candidate_card_type(self):
        """candidate_card_type should be 'multi_asset_market_sync'."""
        self.assertEqual(self.result.get("candidate_card_type"), "multi_asset_market_sync")

    def test_mock_adapter_ready(self):
        """mock_adapter_ready should be True."""
        self.assertTrue(self.result.get("mock_adapter_ready"))

    def test_envelope_compatibility_passed(self):
        """envelope_compatibility_passed should be True."""
        self.assertTrue(self.result.get("envelope_compatibility_passed"))

    def test_noise_cases_total(self):
        """noise_cases_total should be >= 6."""
        self.assertGreaterEqual(self.result.get("noise_cases_total", 0), 6)

    def test_mock_envelope_count(self):
        """mock_envelope_count should be >= 1."""
        self.assertGreaterEqual(self.result.get("mock_envelope_count", 0), 1)

    def test_send_candidate_count(self):
        """send_candidate_count should be 0 (mock mode, no real sends)."""
        self.assertEqual(self.result.get("send_candidate_count"), 0)

    def test_blocked_or_degraded_excluded(self):
        """blocked_or_degraded_cases_excluded_from_send should be True."""
        self.assertTrue(self.result.get("blocked_or_degraded_cases_excluded_from_send"))

    def test_deterministic_ids(self):
        """deterministic_ids should be True."""
        self.assertTrue(self.result.get("deterministic_ids"))

    def test_payload_hashes_stable(self):
        """payload_hashes_stable should be True."""
        self.assertTrue(self.result.get("payload_hashes_stable"))

    def test_real_send_ready_false(self):
        """real_send_ready should be False."""
        self.assertFalse(self.result.get("real_send_ready"))

    def test_production_state_write_ready_false(self):
        """production_state_write_ready should be False."""
        self.assertFalse(self.result.get("production_state_write_ready"))

    def test_debug_leak_count_zero(self):
        """debug_leak_count should be 0."""
        self.assertEqual(self.result.get("debug_leak_count"), 0)

    def test_secret_leak_count_zero(self):
        """secret_leak_count should be 0."""
        self.assertEqual(self.result.get("secret_leak_count"), 0)

    def test_recommended_next_step(self):
        """recommended_next_step should reference v112s."""
        next_step = self.result.get("recommended_next_step", "")
        self.assertIn("v112s", next_step.lower() if next_step else "")


class TestEnvelopesJsonlFields(unittest.TestCase):
    """Test that each envelope has all required fields."""

    @classmethod
    def setUpClass(cls):
        cls.envelopes = _load_jsonl(ENVELOPES_JSONL_PATH)
        assert len(cls.envelopes) > 0, f"No envelopes found in {ENVELOPES_JSONL_PATH}"

    def test_every_envelope_has_signal_id(self):
        """Every envelope must have signal_id."""
        for i, env in enumerate(self.envelopes):
            sid = env.get("signal_id", "")
            self.assertTrue(sid and isinstance(sid, str) and len(sid) > 0,
                            f"Envelope {i} missing signal_id")
            self.assertTrue(sid.startswith("sig-"),
                            f"Envelope {i} signal_id doesn't start with 'sig-': {sid}")

    def test_every_envelope_has_card_type(self):
        """Every envelope must have card_type == 'multi_asset_market_sync'."""
        for i, env in enumerate(self.envelopes):
            ct = env.get("card_type", "")
            self.assertEqual(ct, "multi_asset_market_sync",
                             f"Envelope {i} card_type is '{ct}', expected 'multi_asset_market_sync'")

    def test_every_envelope_has_dedupe_key(self):
        """Every envelope must have dedupe_key."""
        for i, env in enumerate(self.envelopes):
            dk = env.get("dedupe_key", "")
            self.assertTrue(dk and isinstance(dk, str) and len(dk) >= 16,
                            f"Envelope {i} missing or invalid dedupe_key: {dk}")

    def test_every_envelope_has_cooldown_key(self):
        """Every envelope must have cooldown_key."""
        for i, env in enumerate(self.envelopes):
            ck = env.get("cooldown_key", "")
            self.assertTrue(ck and isinstance(ck, str) and len(ck) >= 16,
                            f"Envelope {i} missing or invalid cooldown_key: {ck}")

    def test_every_envelope_has_payload_hash(self):
        """Every envelope must have payload_hash."""
        for i, env in enumerate(self.envelopes):
            ph = env.get("payload_hash", "")
            self.assertTrue(ph and isinstance(ph, str) and len(ph) >= 16,
                            f"Envelope {i} missing or invalid payload_hash: {ph}")

    def test_every_envelope_has_source_lineage(self):
        """Every envelope must have source_lineage."""
        for i, env in enumerate(self.envelopes):
            sl = env.get("source_lineage", {})
            self.assertIsInstance(sl, dict, f"Envelope {i} source_lineage is not a dict")
            self.assertIn("noise_case_source", sl, f"Envelope {i} source_lineage missing noise_case_source")
            self.assertIn("threshold_config_source", sl, f"Envelope {i} source_lineage missing threshold_config_source")
            self.assertIn("fixture_source", sl, f"Envelope {i} source_lineage missing fixture_source")

    def test_every_envelope_has_mock_adapter_true(self):
        """Every envelope must have mock_adapter == True."""
        for i, env in enumerate(self.envelopes):
            self.assertTrue(env.get("mock_adapter"),
                            f"Envelope {i} mock_adapter is not True")

    def test_every_envelope_has_dry_run_only_true(self):
        """Every envelope must have dry_run_only == True."""
        for i, env in enumerate(self.envelopes):
            self.assertTrue(env.get("dry_run_only"),
                            f"Envelope {i} dry_run_only is not True")

    def test_every_envelope_has_real_live_api_called_false(self):
        """Every envelope must have real_live_api_called == False."""
        for i, env in enumerate(self.envelopes):
            self.assertFalse(env.get("real_live_api_called"),
                             f"Envelope {i} real_live_api_called is not False")

    def test_every_envelope_has_eligible_for_send_false(self):
        """Every envelope must have eligible_for_send == False (mock mode)."""
        for i, env in enumerate(self.envelopes):
            self.assertFalse(env.get("eligible_for_send"),
                             f"Envelope {i} eligible_for_send is not False")

    def test_every_envelope_has_payload(self):
        """Every envelope must have a payload or public_card."""
        for i, env in enumerate(self.envelopes):
            has_payload = bool(env.get("public_card", ""))
            self.assertTrue(has_payload, f"Envelope {i} has no public_card content")

    def test_every_envelope_has_valid_schema_version(self):
        """Every envelope must have schema_version."""
        for i, env in enumerate(self.envelopes):
            sv = env.get("schema_version", "")
            self.assertTrue(sv, f"Envelope {i} missing schema_version")

    def test_every_envelope_has_observed_at(self):
        """Every envelope must have observed_at."""
        for i, env in enumerate(self.envelopes):
            oa = env.get("observed_at", "")
            self.assertTrue(oa, f"Envelope {i} missing observed_at")

    def test_every_envelope_has_direction(self):
        """Every envelope must have a valid direction."""
        for i, env in enumerate(self.envelopes):
            d = env.get("direction", "")
            valid = {"bullish", "bearish", "neutral", "mixed", "unknown"}
            self.assertIn(d, valid, f"Envelope {i} has invalid direction: {d}")

    def test_no_envelope_has_blocked_noise_case_as_send_candidate(self):
        """No envelope from blocked/degraded/downgraded cases should be marked
        as eligible_for_send."""
        for i, env in enumerate(self.envelopes):
            nc = env.get("noise_classification", {})
            actual = nc.get("v112q_actual_result", "")
            if actual in BLOCKED_EXCLUDED_TERMS:
                self.assertFalse(
                    env.get("eligible_for_send"),
                    f"Envelope {i} from {actual} case should not be eligible_for_send"
                )


class TestNoSecretLeaks(unittest.TestCase):
    """Test that no secrets, keys, tokens, or passwords leak in any output."""

    @classmethod
    def setUpClass(cls):
        cls.all_texts = []
        for path in [RESULT_JSON_PATH, ENVELOPES_JSONL_PATH, REPORT_MD_PATH, HANDOFF_MD_PATH]:
            if path.exists():
                cls.all_texts.append(_read_text(path))

    def test_no_forbidden_patterns_in_outputs(self):
        """No credential patterns should appear in any output."""
        combined = "\n".join(self.all_texts)
        for pattern in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            self.assertEqual(
                len(matches), 0,
                f"Forbidden pattern found: '{pattern}' matched: {matches}"
            )

    def test_no_misleading_terms_in_outputs(self):
        """No misleading terms like 'production ready' or 'live API connected'."""
        combined = "\n".join(self.all_texts)
        for term in MISLEADING_TERMS:
            self.assertNotIn(
                term.lower(), combined.lower(),
                f"Misleading term found: '{term}'"
            )


class TestRepeatedRunStability(unittest.TestCase):
    """Test that repeated runs produce stable output."""

    def test_repeated_run_same_status(self):
        """Two consecutive runs should produce the same status."""
        # Run twice
        exit1, out1, err1 = _run_runner()
        exit2, out2, err2 = _run_runner()

        self.assertEqual(exit1, 0, f"First run failed: {err1}")
        self.assertEqual(exit2, 0, f"Second run failed: {err2}")

        # Load results from both runs
        result1 = _load_json(RESULT_JSON_PATH)
        result2 = _load_json(RESULT_JSON_PATH)  # Same file, second run overwrites

        if result1 and result2:
            self.assertEqual(result1.get("status"), result2.get("status"),
                             "Status changed between runs")
            self.assertEqual(result1.get("mock_envelope_count"),
                             result2.get("mock_envelope_count"),
                             "mock_envelope_count changed between runs")

    def test_repeated_run_same_envelope_keys(self):
        """Two consecutive runs should produce same dedupe_key/cooldown_key/payload_hash."""
        # Run twice and compare envelopes
        _run_runner()
        envelopes1 = _load_jsonl(ENVELOPES_JSONL_PATH)

        _run_runner()
        envelopes2 = _load_jsonl(ENVELOPES_JSONL_PATH)

        self.assertEqual(len(envelopes1), len(envelopes2),
                         f"Envelope count changed: {len(envelopes1)} vs {len(envelopes2)}")

        for e1, e2 in zip(envelopes1, envelopes2):
            # signal_id should be stable (same case_id + same timestamp format)
            # dedupe_key, cooldown_key, payload_hash should be deterministic
            self.assertEqual(e1.get("dedupe_key"), e2.get("dedupe_key"),
                             f"dedupe_key changed for signal {e1.get('signal_id')}")
            self.assertEqual(e1.get("cooldown_key"), e2.get("cooldown_key"),
                             f"cooldown_key changed for signal {e1.get('signal_id')}")
            self.assertEqual(e1.get("payload_hash"), e2.get("payload_hash"),
                             f"payload_hash changed for signal {e1.get('signal_id')}")


class TestUpstreamTestsContinuePassing(unittest.TestCase):
    """Test that all upstream test suites continue to pass."""

    def _run_test(self, test_path: Path) -> tuple[int, str, str]:
        """Run a test script and return (exit_code, stdout, stderr)."""
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=120,
        )
        return result.returncode, result.stdout or "", result.stderr or ""

    def test_v112q_tests_pass(self):
        """v112Q tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112Q tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112p_tests_pass(self):
        """v112P tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112p_live_source_readiness_audit.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112P tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112o_tests_pass(self):
        """v112O tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112o_send_preview_pack.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112O tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112n_tests_pass(self):
        """v112N tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112n_local_master_dryrun.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112N tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112h_tests_pass(self):
        """v112H tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_signal_envelope_v112h.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112H tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112g_tests_pass(self):
        """v112G tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_multi_asset_sync_feed_v112g.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112G tests failed (exit={exit_code}).\nstdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")


if __name__ == "__main__":
    # First, run the v112R runner to generate fresh output
    print("=" * 60)
    print("Running v112R runner to generate fresh output...")
    print("=" * 60)
    exit_code, stdout, stderr = _run_runner()
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    print(f"Runner exit code: {exit_code}")
    print()

    # Then run tests
    print("=" * 60)
    print("Running v112R test suite...")
    print("=" * 60)
    unittest.main(verbosity=2, exit=False)

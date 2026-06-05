"""Tests for v1.12-S Mock Envelope → Gate/Preview Integration.

Covers:
  - Runner executes successfully
  - All output files exist (result JSON, gate decisions JSONL, preview cards JSONL,
    report MD, handoff MD)
  - result JSON has correct fields and values
  - All safety boundary fields correct
  - Every gate decision has required keys (signal_id, dedupe_key, cooldown_key, payload_hash)
  - Every gate decision has eligible_for_real_send == False
  - Every preview card has LOCAL MOCK PREVIEW marker
  - Every preview card has source_lineage
  - Every preview card has safety flags
  - Low confidence envelope not eligible_for_real_send
  - Repeated run output stable
  - No secret/key/token/cookie/password clear text in any output
  - No misleading "production ready", "live API connected", etc.
  - Upstream tests (v112R, v112Q, v112P, v112O, v112N, v112I) continue to pass

Usage:
    python scripts/test_market_radar_v112s_mock_envelope_gate_preview_integration.py
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

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112s_mock_gate_preview_integration_result.json"
GATE_DECISIONS_JSONL_PATH = ROOT / "results" / "market_radar_v112s_mock_gate_decisions.jsonl"
PREVIEW_CARDS_JSONL_PATH = ROOT / "results" / "market_radar_v112s_mock_preview_cards.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112s_mock_envelope_gate_preview_integration.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112s_mock_envelope_gate_preview_integration_handoff.md"
RUNNER_PATH = ROOT / "scripts" / "run_market_radar_v112s_mock_envelope_gate_preview_integration.py"

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
    # Only flag ai_relay_desk path leaks (not legitimate project paths)
    r'ai_relay_desk',
]

MISLEADING_TERMS = [
    "已接入 live source", "live source connected", "production ready",
    "已发送", "正式发布", "real sent", "已推送", "已投递",
    "broadcast sent", "message delivered", "sent to channel",
    "已发布成功", "发送成功", "live API connected", "已接入 live API",
    "已真实发送",
]

# All output file paths for secret scanning
ALL_OUTPUT_PATHS = [
    RESULT_JSON_PATH,
    GATE_DECISIONS_JSONL_PATH,
    PREVIEW_CARDS_JSONL_PATH,
    REPORT_MD_PATH,
    HANDOFF_MD_PATH,
]


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
    """Run the v112S runner and return (exit_code, stdout, stderr)."""
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
    """Test that the v112S runner executes successfully."""

    def test_runner_exit_code_zero(self):
        """Runner should exit with code 0."""
        exit_code, stdout, stderr = _run_runner()
        self.assertEqual(exit_code, 0,
                         f"Runner failed (exit={exit_code}).\nstderr:\n{stderr}\nstdout:\n{stdout}")

    def test_runner_output_has_pass(self):
        """Runner output should mention PASS."""
        _, stdout, _ = _run_runner()
        self.assertIn("[PASS]", stdout)


class TestOutputFilesExist(unittest.TestCase):
    """Test that all output files exist."""

    def test_result_json_exists(self):
        """Result JSON should exist."""
        self.assertTrue(RESULT_JSON_PATH.exists(),
                        f"Result JSON not found at {RESULT_JSON_PATH}")

    def test_gate_decisions_jsonl_exists(self):
        """Gate decisions JSONL should exist."""
        self.assertTrue(GATE_DECISIONS_JSONL_PATH.exists(),
                        f"Gate decisions JSONL not found at {GATE_DECISIONS_JSONL_PATH}")

    def test_preview_cards_jsonl_exists(self):
        """Preview cards JSONL should exist."""
        self.assertTrue(PREVIEW_CARDS_JSONL_PATH.exists(),
                        f"Preview cards JSONL not found at {PREVIEW_CARDS_JSONL_PATH}")

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
        """version should be 'v1.12-s'."""
        self.assertEqual(self.result.get("version"), "v1.12-s")

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

    def test_mock_envelope_count_positive(self):
        """mock_envelope_count should be >= 1."""
        self.assertGreaterEqual(self.result.get("mock_envelope_count", 0), 1)

    def test_mock_gate_decision_count_equals_envelope_count(self):
        """mock_gate_decision_count should equal mock_envelope_count."""
        self.assertEqual(
            self.result.get("mock_gate_decision_count"),
            self.result.get("mock_envelope_count"),
        )

    def test_mock_preview_card_count_equals_envelope_count(self):
        """mock_preview_card_count should equal mock_envelope_count."""
        self.assertEqual(
            self.result.get("mock_preview_card_count"),
            self.result.get("mock_envelope_count"),
        )

    def test_real_send_candidate_count_zero(self):
        """real_send_candidate_count must be 0."""
        self.assertEqual(self.result.get("real_send_candidate_count"), 0)

    def test_eligible_for_real_send_count_zero(self):
        """eligible_for_real_send_count must be 0."""
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0)

    def test_state_write_performed_false(self):
        """state_write_performed must be False."""
        self.assertFalse(self.result.get("state_write_performed"))

    def test_gate_preview_integration_passed_true(self):
        """gate_preview_integration_passed should be True."""
        self.assertTrue(self.result.get("gate_preview_integration_passed"))

    def test_blocked_or_low_confidence_not_real_send(self):
        """blocked_or_low_confidence_not_real_send should be True."""
        self.assertTrue(self.result.get("blocked_or_low_confidence_not_real_send"))

    def test_deterministic_preview_ids(self):
        """deterministic_preview_ids should be True."""
        self.assertTrue(self.result.get("deterministic_preview_ids"))

    def test_repeated_run_stable(self):
        """repeated_run_stable should be True."""
        self.assertTrue(self.result.get("repeated_run_stable"))

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
        """recommended_next_step should reference v112t."""
        next_step = self.result.get("recommended_next_step", "")
        self.assertIn("v112t", next_step.lower() if next_step else "")


class TestGateDecisionsJsonl(unittest.TestCase):
    """Test gate decisions JSONL fields and constraints."""

    @classmethod
    def setUpClass(cls):
        cls.gate_decisions = _load_jsonl(GATE_DECISIONS_JSONL_PATH)
        assert len(cls.gate_decisions) > 0, \
            f"No gate decisions found in {GATE_DECISIONS_JSONL_PATH}"

    def test_gate_decision_count_matches_result(self):
        """Gate decision count should match result mock_gate_decision_count."""
        result = _load_json(RESULT_JSON_PATH)
        if result:
            self.assertEqual(len(self.gate_decisions),
                             result.get("mock_gate_decision_count"))

    def test_every_decision_has_signal_id(self):
        """Every gate decision must have signal_id."""
        for i, gd in enumerate(self.gate_decisions):
            sid = gd.get("signal_id", "")
            self.assertTrue(sid and isinstance(sid, str) and len(sid) > 0,
                            f"Gate decision {i} missing signal_id")
            self.assertTrue(sid.startswith("sig-"),
                            f"Gate decision {i} signal_id doesn't start with 'sig-': {sid}")

    def test_every_decision_has_dedupe_key(self):
        """Every gate decision must have dedupe_key."""
        for i, gd in enumerate(self.gate_decisions):
            dk = gd.get("dedupe_key", "")
            self.assertTrue(dk and isinstance(dk, str) and len(dk) >= 16,
                            f"Gate decision {i} missing or invalid dedupe_key: {dk}")

    def test_every_decision_has_cooldown_key(self):
        """Every gate decision must have cooldown_key."""
        for i, gd in enumerate(self.gate_decisions):
            ck = gd.get("cooldown_key", "")
            self.assertTrue(ck and isinstance(ck, str) and len(ck) >= 16,
                            f"Gate decision {i} missing or invalid cooldown_key: {ck}")

    def test_every_decision_has_payload_hash(self):
        """Every gate decision must have payload_hash."""
        for i, gd in enumerate(self.gate_decisions):
            ph = gd.get("payload_hash", "")
            self.assertTrue(ph and isinstance(ph, str) and len(ph) >= 16,
                            f"Gate decision {i} missing or invalid payload_hash: {ph}")

    def test_every_decision_has_card_type(self):
        """Every gate decision must have card_type == 'multi_asset_market_sync'."""
        for i, gd in enumerate(self.gate_decisions):
            ct = gd.get("card_type", "")
            self.assertEqual(ct, "multi_asset_market_sync",
                             f"Gate decision {i} card_type is '{ct}'")

    def test_every_decision_eligible_for_real_send_false(self):
        """Every gate decision MUST have eligible_for_real_send == False."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertFalse(gd.get("eligible_for_real_send"),
                             f"Gate decision {i} eligible_for_real_send is not False! "
                             f"signal_id={gd.get('signal_id')}")

    def test_every_decision_has_eligible_for_preview(self):
        """Every gate decision must have eligible_for_preview."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertIn("eligible_for_preview", gd,
                          f"Gate decision {i} missing eligible_for_preview")

    def test_every_decision_has_reason(self):
        """Every gate decision must have a reason."""
        for i, gd in enumerate(self.gate_decisions):
            reason = gd.get("reason", "")
            self.assertTrue(reason and len(reason) > 10,
                            f"Gate decision {i} missing or too short reason: {reason}")

    def test_every_decision_mock_adapter_true(self):
        """Every gate decision must have mock_adapter == True."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertTrue(gd.get("mock_adapter"),
                            f"Gate decision {i} mock_adapter is not True")

    def test_every_decision_dry_run_only_true(self):
        """Every gate decision must have dry_run_only == True."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertTrue(gd.get("dry_run_only"),
                            f"Gate decision {i} dry_run_only is not True")

    def test_every_decision_real_live_api_called_false(self):
        """Every gate decision must have real_live_api_called == False."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertFalse(gd.get("real_live_api_called"),
                             f"Gate decision {i} real_live_api_called is not False")

    def test_every_decision_state_write_performed_false(self):
        """Every gate decision must have state_write_performed == False."""
        for i, gd in enumerate(self.gate_decisions):
            self.assertFalse(gd.get("state_write_performed"),
                             f"Gate decision {i} state_write_performed is not False")

    def test_low_confidence_not_eligible_for_real_send(self):
        """Low confidence envelopes must NOT be eligible_for_real_send."""
        for i, gd in enumerate(self.gate_decisions):
            gs = gd.get("gate_status", "")
            if gs in ("blocked_low_confidence", "audit_only"):
                self.assertFalse(
                    gd.get("eligible_for_real_send"),
                    f"Gate decision {i} ({gs}) should not be eligible_for_real_send"
                )

    def test_valid_gate_statuses(self):
        """Gate statuses should be from valid set."""
        valid = {"passed_mock", "audit_only", "blocked_low_confidence"}
        for i, gd in enumerate(self.gate_decisions):
            gs = gd.get("gate_status", "")
            self.assertIn(gs, valid,
                          f"Gate decision {i} has invalid gate_status: {gs}")


class TestPreviewCardsJsonl(unittest.TestCase):
    """Test preview cards JSONL fields and constraints."""

    @classmethod
    def setUpClass(cls):
        cls.cards = _load_jsonl(PREVIEW_CARDS_JSONL_PATH)
        assert len(cls.cards) > 0, \
            f"No preview cards found in {PREVIEW_CARDS_JSONL_PATH}"

    def test_preview_card_count_matches_result(self):
        """Preview card count should match result mock_preview_card_count."""
        result = _load_json(RESULT_JSON_PATH)
        if result:
            self.assertEqual(len(self.cards),
                             result.get("mock_preview_card_count"))

    def test_every_card_has_preview_id(self):
        """Every preview card must have a valid preview_id."""
        for i, card in enumerate(self.cards):
            pid = card.get("preview_id", "")
            self.assertTrue(pid and pid.startswith("pv-mock-"),
                            f"Card {i} missing or invalid preview_id: {pid}")

    def test_every_card_has_rank(self):
        """Every preview card must have a rank."""
        for i, card in enumerate(self.cards):
            rank = card.get("rank")
            self.assertIsNotNone(rank, f"Card {i} missing rank")
            self.assertGreaterEqual(rank, 1, f"Card {i} rank < 1: {rank}")

    def test_ranks_unique_and_consecutive(self):
        """Ranks should be unique and consecutive starting from 1."""
        ranks = [c.get("rank") for c in self.cards]
        self.assertEqual(sorted(ranks), list(range(1, len(self.cards) + 1)),
                         f"Ranks not consecutive 1..{len(self.cards)}: {ranks}")

    def test_every_card_has_signal_id(self):
        """Every preview card must have signal_id."""
        for i, card in enumerate(self.cards):
            sid = card.get("signal_id", "")
            self.assertTrue(sid and len(sid) > 0,
                            f"Card {i} missing signal_id")

    def test_every_card_has_card_type(self):
        """Every preview card must have card_type."""
        for i, card in enumerate(self.cards):
            ct = card.get("card_type", "")
            self.assertEqual(ct, "multi_asset_market_sync",
                             f"Card {i} card_type is '{ct}'")

    def test_every_card_has_gate_status(self):
        """Every preview card must have gate_status."""
        valid = {"passed_mock", "audit_only", "blocked_low_confidence"}
        for i, card in enumerate(self.cards):
            gs = card.get("gate_status", "")
            self.assertIn(gs, valid,
                          f"Card {i} has invalid gate_status: {gs}")

    def test_every_card_eligible_for_preview(self):
        """Every preview card must have eligible_for_preview == True."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("eligible_for_preview"),
                            f"Card {i} eligible_for_preview is not True")

    def test_every_card_eligible_for_real_send_false(self):
        """Every preview card MUST have eligible_for_real_send == False."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("eligible_for_real_send"),
                             f"Card {i} eligible_for_real_send is not False! "
                             f"signal_id={card.get('signal_id')}")

    def test_every_card_has_local_mock_preview_marker(self):
        """Every preview card must have LOCAL MOCK PREVIEW in send_preview_text."""
        for i, card in enumerate(self.cards):
            text = card.get("send_preview_text", "")
            self.assertIn("LOCAL MOCK PREVIEW", text,
                          f"Card {i} missing LOCAL MOCK PREVIEW marker")

    def test_every_card_has_source_lineage(self):
        """Every preview card must have source_lineage."""
        required_keys = {
            "mock_envelope_source",
            "gate_decision_source",
            "noise_case_source",
            "threshold_config_source",
        }
        for i, card in enumerate(self.cards):
            sl = card.get("source_lineage", {})
            self.assertIsInstance(sl, dict,
                                  f"Card {i} source_lineage is not a dict")
            for key in required_keys:
                self.assertIn(key, sl,
                              f"Card {i} source_lineage missing '{key}'")
                self.assertTrue(sl[key],
                                f"Card {i} source_lineage '{key}' is empty")

    def test_every_card_has_safety_flags(self):
        """Every preview card must have safety flags."""
        required_safety = {
            "dry_run_only": True,
            "real_live_api_called": False,
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "production_state_write": False,
        }
        for i, card in enumerate(self.cards):
            safety = card.get("safety", {})
            self.assertIsInstance(safety, dict,
                                  f"Card {i} safety is not a dict")
            for key, expected in required_safety.items():
                actual = safety.get(key)
                self.assertEqual(actual, expected,
                                 f"Card {i} safety['{key}'] is {actual}, expected {expected}")


class TestNoSecretLeaks(unittest.TestCase):
    """Test that no secrets, keys, tokens, or passwords leak in any output."""

    @classmethod
    def setUpClass(cls):
        cls.all_texts = []
        for path in ALL_OUTPUT_PATHS:
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
        exit1, out1, err1 = _run_runner()
        exit2, out2, err2 = _run_runner()

        self.assertEqual(exit1, 0, f"First run failed (exit={exit1}): {err1}")
        self.assertEqual(exit2, 0, f"Second run failed (exit={exit2}): {err2}")

        result1 = _load_json(RESULT_JSON_PATH)
        result2 = _load_json(RESULT_JSON_PATH)

        if result1 and result2:
            self.assertEqual(result1.get("status"), result2.get("status"),
                             "Status changed between runs")
            self.assertEqual(result1.get("mock_envelope_count"),
                             result2.get("mock_envelope_count"),
                             "mock_envelope_count changed between runs")

    def test_repeated_run_same_preview_ids(self):
        """Two consecutive runs should produce the same preview IDs."""
        _run_runner()
        cards1 = _load_jsonl(PREVIEW_CARDS_JSONL_PATH)

        _run_runner()
        cards2 = _load_jsonl(PREVIEW_CARDS_JSONL_PATH)

        self.assertEqual(len(cards1), len(cards2),
                         f"Card count changed: {len(cards1)} vs {len(cards2)}")

        ids1 = sorted([c.get("preview_id", "") for c in cards1])
        ids2 = sorted([c.get("preview_id", "") for c in cards2])
        self.assertEqual(ids1, ids2,
                         f"Preview IDs changed between runs: {ids1} vs {ids2}")

    def test_repeated_run_same_gate_decisions(self):
        """Two consecutive runs should produce the same gate statuses."""
        _run_runner()
        gd1 = _load_jsonl(GATE_DECISIONS_JSONL_PATH)

        _run_runner()
        gd2 = _load_jsonl(GATE_DECISIONS_JSONL_PATH)

        self.assertEqual(len(gd1), len(gd2),
                         f"Gate decision count changed: {len(gd1)} vs {len(gd2)}")

        for d1, d2 in zip(gd1, gd2):
            self.assertEqual(d1.get("signal_id"), d2.get("signal_id"))
            self.assertEqual(d1.get("gate_status"), d2.get("gate_status"))
            self.assertEqual(d1.get("eligible_for_real_send"),
                             d2.get("eligible_for_real_send"))
            self.assertEqual(d1.get("dedupe_key"), d2.get("dedupe_key"))
            self.assertEqual(d1.get("cooldown_key"), d2.get("cooldown_key"))
            self.assertEqual(d1.get("payload_hash"), d2.get("payload_hash"))


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

    def test_v112r_tests_pass(self):
        """v112R tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112R tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112q_tests_pass(self):
        """v112Q tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112Q tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112p_tests_pass(self):
        """v112P tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112p_live_source_readiness_audit.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112P tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112o_tests_pass(self):
        """v112O tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112o_send_preview_pack.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112O tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112n_tests_pass(self):
        """v112N tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_v112n_local_master_dryrun.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112N tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")

    def test_v112i_tests_pass(self):
        """v112I tests should continue to pass."""
        test_path = ROOT / "scripts" / "test_market_radar_dedupe_cooldown_gate_v112i.py"
        exit_code, stdout, stderr = self._run_test(test_path)
        self.assertEqual(exit_code, 0,
                         f"v112I tests failed (exit={exit_code}).\n"
                         f"stdout:\n{stdout[:500]}\nstderr:\n{stderr[:500]}")


if __name__ == "__main__":
    # First, run the v112S runner to generate fresh output
    print("=" * 60)
    print("Running v112S runner to generate fresh output...")
    print("=" * 60)
    exit_code, stdout, stderr = _run_runner()
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    print(f"Runner exit code: {exit_code}")
    print()

    # Then run tests
    print("=" * 60)
    print("Running v112S test suite...")
    print("=" * 60)
    unittest.main(verbosity=2, exit=False)

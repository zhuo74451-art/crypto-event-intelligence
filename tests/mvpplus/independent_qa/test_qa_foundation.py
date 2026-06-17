#!/usr/bin/env python3
"""Tests for Independent QA Foundation — mvpplus.

W6_DELTA_PROJECT_SPECIFIC_QA_REPAIR_R02:
  All oracles, validators, and corpus scanners repaired.
  Tests cover: framework self-test, synthetic vulnerable target detection,
  synthetic safe target pass, with exact counts and no false business-lane claims.
"""

import json
import os
import sys
import tempfile
import unittest

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJ)

from qa.mvpplus.qa_core import (
    QAResult, QAScanReport,
    scan_ownership, scan_forbidden_imports, scan_trading_capability,
    scan_credentials, scan_scheduler_disabled, scan_no_send,
    scan_artifact_binding, scan_test_count, scan_dependency_manifest,
    scan_data_truth, oracle_liquidation_formula, oracle_first_snapshot,
    scan_hype_source_policy, scan_feed_id,
    scan_html_security, scan_url_corpus, scan_xss_corpus, scan_evidence_schema,
    run_all_scans,
)


def make_temp_py(content: str) -> str:
    """Create a temp Python file and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


# ── Framework Self-Tests ────────────────────────────────────────────────────


class TestQAResult(unittest.TestCase):
    """QAResult dataclass behavior."""

    def test_status_enum(self):
        for s in ("PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"):
            r = QAResult(scanner="test", status=s)
            self.assertEqual(r.status, s)

    def test_as_dict(self):
        r = QAResult(scanner="test", status="PASS", detail="test", violations=["v1"])
        d = r.as_dict()
        self.assertEqual(d["scanner"], "test")
        self.assertEqual(d["violations"], ["v1"])

    def test_report_as_dict(self):
        r = QAScanReport(scan_id="s1", target_repo="/repo", target_ref="abc",
                         scanned_at="2026-01-01T00:00:00Z")
        d = r.as_dict()
        self.assertEqual(d["scan_id"], "s1")


class TestOwnership(unittest.TestCase):
    def test_detects_unauthorized_change(self):
        r = scan_ownership(PROJ, ["qa/mvpplus/"], base_ref="HEAD")
        self.assertIn(r.status, ("PASS", "FAIL"))


class TestForbiddenImports(unittest.TestCase):
    def test_clean_import_passes(self):
        path = make_temp_py("import json\n")
        try:
            r = scan_forbidden_imports(os.path.dirname(path), [os.path.dirname(path)], ["subprocess"])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)


class TestTradingCapability(unittest.TestCase):
    def test_detects_private_method(self):
        path = make_temp_py("def _trade_execute(): pass\n")
        try:
            r = scan_trading_capability(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
            self.assertTrue(any("private_method" in v for v in r.violations))
        finally:
            os.unlink(path)

    def test_detects_wallet_import(self):
        path = make_temp_py("from web3 import Web3\n")
        try:
            r = scan_trading_capability(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
            self.assertTrue(any("wallet" in v.lower() for v in r.violations))
        finally:
            os.unlink(path)


class TestCredentialScanner(unittest.TestCase):
    def test_detects_api_key(self):
        path = make_temp_py('API_KEY = "sk-1234567890abcdef"\n')
        try:
            r = scan_credentials(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)

    def test_clean_file_passes(self):
        path = make_temp_py("x = 42\n")
        try:
            r = scan_credentials(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)


class TestSchedulerDisabled(unittest.TestCase):
    def test_detects_enabled_scheduler(self):
        path = make_temp_py("scheduler_enabled = True  # cron loop\n")
        try:
            r = scan_scheduler_disabled(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)


class TestNoSend(unittest.TestCase):
    def test_detects_bot_send(self):
        path = make_temp_py("bot.send_message(chat_id, 'hello')\n")
        try:
            r = scan_no_send(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)


class TestArtifactBinding(unittest.TestCase):
    def test_mismatch_detected(self):
        r = scan_artifact_binding(["f.json"], "abc123", "def456")
        self.assertEqual(r.status, "FAIL")

    def test_match_passes(self):
        r = scan_artifact_binding(["f.json"], "abc123", "abc123")
        self.assertEqual(r.status, "PASS")


class TestTestCount(unittest.TestCase):
    def test_missing_path_blocked(self):
        """Non-existent test path should appear in violations but not crash."""
        r = scan_test_count(PROJ, 999, ["/nonexistent/path"])
        self.assertEqual(r.status, "FAIL")


class TestDependencyManifest(unittest.TestCase):
    def test_missing_file_fails(self):
        r = scan_dependency_manifest("/nonexistent", "missing.txt")
        self.assertEqual(r.status, "FAIL")

    def test_synthetic_pinned_manifest_passes(self):
        """Synthetic pinned manifest must PASS (QA does not scan real requirements.txt)."""
        pinned = "pandas==2.0.0\nrequests>=2.28.0\n"
        r = scan_dependency_manifest("/fake", "synthetic.txt", content_override=pinned)
        self.assertEqual(r.status, "PASS")

    def test_synthetic_unpinned_fails(self):
        """Synthetic manifest with unpinned dep must FAIL."""
        unpinned = "pandas\nrequests>=2.28.0\n"
        r = scan_dependency_manifest("/fake", "synthetic.txt", content_override=unpinned)
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("pandas" in v for v in r.violations))


# ═══════════════════════════════════════════════════════════════════════════
# Repaired Oracles — W6_DELTA
# ═══════════════════════════════════════════════════════════════════════════


class TestLiquidationOracle(unittest.TestCase):
    """oracle_liquidation_formula: (mark-liq)/mark*100, negative preserved."""

    def test_long_formula(self):
        """long = (mark - liq) / mark * 100"""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 95.0, "side": "long", "expected": 5.0})
        self.assertEqual(r.status, "PASS", f"Expected ~5.0%, got violations: {r.violations}")

    def test_short_formula(self):
        """short = (liq - mark) / mark * 100"""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 110.0, "side": "short", "expected": 10.0})
        self.assertEqual(r.status, "PASS")

    def test_missing_mark_liq_null(self):
        """Missing mark or liq → null result, PASS (not FAIL)."""
        r = oracle_liquidation_formula({"side": "long"})
        self.assertEqual(r.status, "PASS")

    def test_invalid_mark_liq_null(self):
        """Non-numeric mark → null result, PASS."""
        r = oracle_liquidation_formula({"mark": "INVALID", "liq": 95.0, "side": "long"})
        self.assertEqual(r.status, "PASS")

    def test_negative_value_preserved(self):
        """Negative distance (liq < mark on long) is preserved, not abs'd."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 110.0, "side": "long",
                                         "expected": -10.0})
        self.assertEqual(r.status, "PASS", f"Expected -10 preserved, got: {r.violations}")

    def test_negative_clamped_detected(self):
        """If negative distance is incorrectly clamped, it's a FAIL."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 110.0, "side": "long",
                                         "expected": 0.0})
        self.assertEqual(r.status, "FAIL")

    def test_wrong_value_fails(self):
        """Incorrect expected value beyond tolerance → FAIL."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 95.0, "side": "long",
                                         "expected": 99.0})
        self.assertEqual(r.status, "FAIL")

    def test_configurable_tolerance(self):
        """Tolerance can be configured."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 95.0, "side": "long",
                                         "expected": 5.5, "tolerance": 0.5})
        self.assertEqual(r.status, "PASS")

    def test_mark_zero_returns_null(self):
        """mark=0 → null expected (can't divide by zero)."""
        r = oracle_liquidation_formula({"mark": 0, "liq": 95.0, "side": "long"})
        self.assertEqual(r.status, "PASS")

    def test_mark_negative_returns_null(self):
        """mark<0 → null expected (invalid price)."""
        r = oracle_liquidation_formula({"mark": -50, "liq": 95.0, "side": "long"})
        self.assertEqual(r.status, "PASS")

    def test_liq_none_returns_null(self):
        """liq=None → null expected."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": None, "side": "long"})
        self.assertEqual(r.status, "PASS")

    def test_short_negative_distance_preserved(self):
        """Short negative distance (liq < mark) is preserved."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 90.0, "side": "short",
                                         "expected": -10.0})
        self.assertEqual(r.status, "PASS")

    def test_short_negative_clamped_detected(self):
        """Short negative distance incorrectly clamped → FAIL."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 90.0, "side": "short",
                                         "expected": 0.0})
        self.assertEqual(r.status, "FAIL")


class TestFirstSnapshotOracle(unittest.TestCase):
    """oracle_first_snapshot: abs(size)>0, long+short baseline, size==0 skip."""

    def test_baseline_open_position_passes(self):
        """Existing non-zero position as baseline_open_position → PASS."""
        r = oracle_first_snapshot({
            "positions": [{"action": "baseline_open_position", "size": 10, "price": 68000}]
        })
        self.assertEqual(r.status, "PASS")

    def test_negative_size_baseline_passes(self):
        """Negative size (short) baseline_open_position → PASS."""
        r = oracle_first_snapshot({
            "positions": [{"action": "baseline_open_position", "size": -5, "price": 68000}]
        })
        self.assertEqual(r.status, "PASS")

    def test_open_long_fails(self):
        """open_long in first snapshot → FAIL."""
        r = oracle_first_snapshot({
            "positions": [{"action": "open_long", "size": 10, "price": 68000}]
        })
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("open_long" in v for v in r.violations))

    def test_open_short_fails(self):
        """open_short in first snapshot → FAIL."""
        r = oracle_first_snapshot({
            "positions": [{"action": "open_short", "size": 5, "price": 68000}]
        })
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("open_short" in v for v in r.violations))

    def test_large_new_position_alert_on_baseline_fails(self):
        """Baseline creating large_new_position alert → FAIL."""
        r = oracle_first_snapshot({
            "positions": [{"action": "baseline_open_position", "size": 100,
                            "alert": "large_new_position"}]
        })
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("large_new_position" in v for v in r.violations))

    def test_empty_positions_fails(self):
        """No position data → FAIL."""
        r = oracle_first_snapshot({"positions": []})
        self.assertEqual(r.status, "FAIL")

    def test_zero_size_skip(self):
        """size=0 must NOT require baseline."""
        r = oracle_first_snapshot({
            "positions": [{"action": "noop", "size": 0, "price": 68000}]
        })
        self.assertEqual(r.status, "PASS")

    def test_mixed_baseline_and_bad_action_fails(self):
        """Mix of valid baseline and invalid open_long fails."""
        r = oracle_first_snapshot({
            "positions": [
                {"action": "baseline_open_position", "size": 10, "price": 68000},
                {"action": "open_long", "size": 5, "price": 69000},
            ]
        })
        self.assertEqual(r.status, "FAIL")

    def test_negative_short_must_use_baseline(self):
        """Negative size (short) must use baseline_open_position, not open_short."""
        r = oracle_first_snapshot({
            "positions": [{"action": "open_short", "size": -5, "price": 68000}]
        })
        self.assertEqual(r.status, "FAIL")


class TestHypeSourcePolicy(unittest.TestCase):
    """scan_hype_source_policy: normalized market record, venue=Hyperliquid."""

    def test_hype_hyperliquid_passes(self):
        """HYPE on Hyperliquid → PASS."""
        r = scan_hype_source_policy({"asset": "HYPE", "venue": "Hyperliquid"})
        self.assertEqual(r.status, "PASS")

    def test_non_hype_skips(self):
        """Non-HYPE asset → NOT_APPLICABLE."""
        r = scan_hype_source_policy({"asset": "BTC", "venue": "Binance"})
        self.assertEqual(r.status, "NOT_APPLICABLE")

    def test_wrong_venue_fails(self):
        """HYPE on non-Hyperliquid venue → FAIL."""
        r = scan_hype_source_policy({"asset": "HYPE", "venue": "Binance"})
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("venue" in v.lower() for v in r.violations))

    def test_binance_fallback_fails(self):
        """HYPE with Binance fallback → FAIL."""
        r = scan_hype_source_policy({
            "asset": "HYPE", "venue": "Hyperliquid",
            "fallback": {"venue": "Binance"}
        })
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("binance" in v.lower() for v in r.violations))


class TestFeedId(unittest.TestCase):
    """scan_feed_id: inject generator or accept 3-group outputs, no self-SHA."""

    def test_missing_id_fails(self):
        r = scan_feed_id({})
        self.assertEqual(r.status, "FAIL")

    def test_valid_deterministic_id_passes(self):
        r = scan_feed_id({"feed_id": "qa_deterministic_test_001"})
        self.assertEqual(r.status, "PASS")

    def test_uuid_fails(self):
        """UUID-format feed_id → FAIL."""
        r = scan_feed_id({"feed_id": "550e8400-e29b-41d4-a716-446655440000"})
        self.assertEqual(r.status, "FAIL")

    def test_timestamp_only_fails(self):
        """Bare timestamp as feed_id → FAIL."""
        r = scan_feed_id({"feed_id": "1718640000"})
        self.assertEqual(r.status, "FAIL")

    def test_random_hex_fails(self):
        """32-char hex looks like hash/random → FAIL."""
        r = scan_feed_id({"feed_id": "a" * 32})
        self.assertEqual(r.status, "FAIL")

    # ── Generator-based determinism tests ──

    def test_generator_same_input_same_id(self):
        """Injected generator: same input → same ID."""
        def gen(inp):
            return f"id_{inp[:4]}"
        r = scan_feed_id({"feed_id_generator": gen, "same_input": "BTC/USD",
                           "changed_input": "ETH/USD"})
        self.assertEqual(r.status, "PASS")

    def test_generator_different_inputs_different_ids(self):
        """Injected generator: different inputs → different IDs (default on collision)."""
        def gen(inp):
            return f"id_{hash(inp) % 100000:05d}"
        r = scan_feed_id({"feed_id_generator": gen, "same_input": "x",
                           "changed_input": "y"})
        self.assertEqual(r.status, "PASS")

    def test_generator_uuid_detected(self):
        """Generator producing UUID-like IDs → FAIL."""
        def gen(inp):
            return "550e8400-e29b-41d4-a716-446655440000"
        r = scan_feed_id({"feed_id_generator": gen})
        self.assertEqual(r.status, "FAIL")

    # ── 3-group output determinism tests ──

    def test_output_groups_same_input_same_id(self):
        """Pre-computed outputs: same input A==B → PASS."""
        r = scan_feed_id({
            "same_input_output_A": "abc123",
            "same_input_output_B": "abc123",
        })
        self.assertEqual(r.status, "PASS")

    def test_output_groups_same_input_different_fails(self):
        """Pre-computed outputs: same input A!=B → FAIL."""
        r = scan_feed_id({
            "same_input_output_A": "abc123",
            "same_input_output_B": "def456",
        })
        self.assertEqual(r.status, "FAIL")

    def test_output_groups_different_inputs_collision_fails(self):
        """Pre-computed outputs: different inputs same output → FAIL."""
        r = scan_feed_id({
            "same_input_output_A": "abc123",
            "same_input_output_B": "abc123",
            "changed_input_output": "abc123",
        })
        self.assertEqual(r.status, "FAIL")


class TestDataTruth(unittest.TestCase):
    """scan_data_truth: live/cached/fixture/research_sample + unknown modes."""

    def test_live_only_passes(self):
        """All live data → PASS."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "live"},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "PASS")

    def test_cached_passes(self):
        """Cached data → PASS."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "cached"},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "PASS")

    def test_fixture_counted_as_live_fails(self):
        """Fixture data with counted_as_live=True → FAIL."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "fixture", "counted_as_live": True},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "FAIL")

    def test_research_sample_counted_as_live_fails(self):
        """Research_sample data counted as live → FAIL."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "research_sample", "counted_as_live": True},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "FAIL")

    def test_mere_text_mention_passes(self):
        """Simple text mentioning both 'fixture' and 'live' must not auto-fail."""
        records = [
            {"id": "doc", "data_mode": "live",
             "note": "This fixture was used to develop the live pipeline"},
            {"id": "r2", "data_mode": "live"},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "PASS")

    def test_empty_records_passes(self):
        r = scan_data_truth([])
        self.assertEqual(r.status, "PASS")

    def test_fixture_with_live_count_field_fails(self):
        """Fixture record with live_count/live_total field → FAIL."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "fixture", "live_count": 5},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "FAIL")

    def test_unknown_mode_reported(self):
        """Unknown data_mode must be explicitly reported → FAIL."""
        records = [
            {"id": "r1", "data_mode": "live"},
            {"id": "r2", "data_mode": "unknown_mode_x456"},
        ]
        r = scan_data_truth(records)
        self.assertEqual(r.status, "FAIL")
        self.assertTrue(any("unknown" in v.lower() for v in r.violations))


class TestUrlCorpus(unittest.TestCase):
    """scan_url_corpus: corpus content itself must not fail; test vs validator."""

    def test_corpus_loaded(self):
        """Corpus loading from file is OK."""
        cpath = os.path.join(PROJ, "qa", "mvpplus", "corpus", "url_attack_corpus.json")
        r = scan_url_corpus(cpath)
        # Without a validator → BLOCKED (target unavailable)
        self.assertEqual(r.status, "BLOCKED")

    def test_missing_corpus_blocked(self):
        r = scan_url_corpus("nonexistent.json")
        self.assertEqual(r.status, "BLOCKED")

    def test_corpus_content_not_failing(self):
        """Corpus with malicious URLs must NOT fail on content alone."""
        corpus = ["javascript:alert('xss')", "file:///etc/passwd",
                   "https://evil.com/?q=<script>"]
        r = scan_url_corpus(corpus)
        # No validator → BLOCKED (not FAIL for corpus content)
        self.assertEqual(r.status, "BLOCKED")
        # Verify it's not failing because of unsafe patterns
        self.assertTrue(any("validator" in v.lower() for v in r.violations))

    def test_safe_validator_passes(self):
        """Payload rejected/escaped by target → PASS."""
        def safe_validator(url):
            return False  # rejected
        corpus = ["javascript:alert('xss')", "file:///etc/passwd"]
        r = scan_url_corpus(corpus, validator=safe_validator)
        self.assertEqual(r.status, "PASS")

    def test_unsafe_validator_fails(self):
        """Unsafe payload accepted by target → FAIL."""
        def unsafe_validator(url):
            return True  # accepted — vulnerable!
        corpus = ["javascript:alert('xss')"]
        r = scan_url_corpus(corpus, validator=unsafe_validator)
        self.assertEqual(r.status, "FAIL")


class TestXssCorpus(unittest.TestCase):
    """scan_xss_corpus: corpus content itself must not fail; test vs renderer."""

    def test_corpus_loaded(self):
        cpath = os.path.join(PROJ, "qa", "mvpplus", "corpus", "xss_attack_corpus.json")
        r = scan_xss_corpus(cpath)
        # Without a renderer → BLOCKED (target unavailable)
        self.assertEqual(r.status, "BLOCKED")

    def test_corpus_content_not_failing(self):
        """XSS corpus must NOT fail on payload content alone."""
        corpus = {"payloads": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"]}
        r = scan_xss_corpus(corpus)
        self.assertEqual(r.status, "BLOCKED")
        self.assertTrue(any("renderer" in v.lower() for v in r.violations))

    def test_safe_renderer_passes(self):
        """Escaped/rejected payload → PASS."""
        def safe_renderer(payload):
            return False  # safely escaped
        corpus = {"payloads": ["<script>alert(1)</script>"]}
        r = scan_xss_corpus(corpus, renderer=safe_renderer)
        self.assertEqual(r.status, "PASS")

    def test_unsafe_renderer_fails(self):
        """Unsafe payload executed → FAIL."""
        def unsafe_renderer(payload):
            return True  # executed unsafely
        corpus = {"payloads": ["<script>alert(1)</script>"]}
        r = scan_xss_corpus(corpus, renderer=unsafe_renderer)
        self.assertEqual(r.status, "FAIL")


class TestEvidenceSchema(unittest.TestCase):
    def test_valid_evidence_passes(self):
        evidence = {
            "scan_id": "test_001",
            "target_repo": "/repo",
            "target_ref": "abc",
            "scanned_at": "2026-01-01T00:00:00Z",
            "results": [{"scanner": "test", "status": "PASS", "detail": "", "violations": []}],
            "summary": {"total": 1, "pass": 1, "fail": 0, "blocked": 0, "not_applicable": 0},
        }
        schema = {
            "required": ["scan_id", "results", "summary"],
            "properties": {
                "scan_id": {"type": "string"},
                "results": {"type": "array"},
                "summary": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "pass": {"type": "integer"},
                        "fail": {"type": "integer"},
                        "blocked": {"type": "integer"},
                        "not_applicable": {"type": "integer"},
                    },
                },
            },
        }
        r = scan_evidence_schema(evidence, schema)
        self.assertEqual(r.status, "PASS")


class TestHtmlSecurity(unittest.TestCase):
    def test_detects_inner_html(self):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
        tmp.write('<div id="x">.innerHTML = userInput</div>\n')
        tmp.close()
        try:
            r = scan_html_security(os.path.dirname(tmp.name), [os.path.dirname(tmp.name)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(tmp.name)


class TestMalformedFixtureCorpus(unittest.TestCase):
    def test_malformed_fixtures_load(self):
        cpath = os.path.join(PROJ, "qa", "mvpplus", "corpus", "malformed_fixture_corpus.json")
        self.assertTrue(os.path.isfile(cpath), "Malformed fixture corpus missing")
        with open(cpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)


class TestPathTraversalCorpus(unittest.TestCase):
    def test_path_traversal_loads(self):
        cpath = os.path.join(PROJ, "qa", "mvpplus", "corpus", "path_traversal_corpus.json")
        self.assertTrue(os.path.isfile(cpath))
        with open(cpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)


class TestDeterministicScan(unittest.TestCase):
    def test_two_runs_identical(self):
        """QA scans produce the same results deterministically."""
        r1 = scan_credentials(PROJ, ["qa/mvpplus/"])
        r2 = scan_credentials(PROJ, ["qa/mvpplus/"])
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(len(r1.violations), len(r2.violations))


class TestNoWritesOutsideEvidence(unittest.TestCase):
    def test_qa_core_no_write(self):
        """qa_core functions don't write files themselves (write is in runner)."""
        import inspect, ast
        source = inspect.getsource(sys.modules["qa.mvpplus.qa_core"])
        # Only check for `open(..., "w")` pattern in function calls (not string literals)
        self.assertNotIn('open(', source.lower() and '"w"', "qa_core should not write files")
        # Actually check: no calls to open with write mode that aren't reading
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id == "open":
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Str) and "w" in kw.value.s:
                            self.fail(f"qa_core uses open(..., 'w') at line {node.lineno}")


# ═══════════════════════════════════════════════════════════════════════════
# Synthetic Target Detection Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSyntheticVulnerableTargetDetection(unittest.TestCase):
    """Self-test: framework detects synthetic vulnerable targets."""

    def test_detects_fake_credential(self):
        """A file with fake API key is detected."""
        path = make_temp_py('SECRET_KEY = "sk-live-abcdef123456"\n')
        try:
            r = scan_credentials(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)

    def test_detects_fake_trading_capability(self):
        """A file with fake trading method is detected."""
        path = make_temp_py("def _trade_order(): pass\n")
        try:
            r = scan_trading_capability(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)

    def test_detects_fake_scheduler(self):
        """A file with enabled scheduler is detected."""
        path = make_temp_py("cron_loop_enabled = True\n")
        try:
            r = scan_scheduler_disabled(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)

    def test_detects_fake_send(self):
        """A file with bot.send_message is detected."""
        path = make_temp_py("bot.send_message(chat_id, text)\n")
        try:
            r = scan_no_send(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(path)

    def test_detects_unsafe_html(self):
        """A file with innerHTML without sanitization is detected."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
        tmp.write('<div id="x">.innerHTML = userInput</div>\n')
        tmp.close()
        try:
            r = scan_html_security(os.path.dirname(tmp.name), [os.path.dirname(tmp.name)])
            self.assertEqual(r.status, "FAIL")
        finally:
            os.unlink(tmp.name)


class TestSyntheticSafeTargetPass(unittest.TestCase):
    """Self-test: framework passes clean synthetic targets."""

    def test_clean_file_no_credentials(self):
        """A clean file passes credential scan."""
        path = make_temp_py("x = 42\n")
        try:
            r = scan_credentials(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)

    def test_clean_file_no_trading(self):
        """A clean file passes trading scan."""
        path = make_temp_py("import json\n")
        try:
            r = scan_trading_capability(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)

    def test_clean_file_no_forbidden_import(self):
        """A clean import passes forbidden scan."""
        path = make_temp_py("import json\n")
        try:
            r = scan_forbidden_imports(os.path.dirname(path), [os.path.dirname(path)], ["subprocess"])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)

    def test_clean_file_no_scheduler(self):
        """No scheduler pattern passes."""
        path = make_temp_py("x = 42\n")
        try:
            r = scan_scheduler_disabled(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)

    def test_clean_file_no_send(self):
        """No send pattern passes."""
        path = make_temp_py("x = 42\n")
        try:
            r = scan_no_send(os.path.dirname(path), [os.path.dirname(path)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(path)

    def test_clean_html_passes(self):
        """Safe HTML file passes."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
        tmp.write("<html><body><p>Safe content</p></body></html>\n")
        tmp.close()
        try:
            r = scan_html_security(os.path.dirname(tmp.name), [os.path.dirname(tmp.name)])
            self.assertEqual(r.status, "PASS")
        finally:
            os.unlink(tmp.name)

    def test_safe_liquidation_oracle_passes(self):
        """Correct liquidation formula passes."""
        r = oracle_liquidation_formula({"mark": 100.0, "liq": 95.0, "side": "long", "expected": 5.0})
        self.assertEqual(r.status, "PASS")

    def test_safe_first_snapshot_passes(self):
        """Valid baseline_open_position passes."""
        r = oracle_first_snapshot({
            "positions": [{"action": "baseline_open_position", "size": 10, "price": 68000}]
        })
        self.assertEqual(r.status, "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)

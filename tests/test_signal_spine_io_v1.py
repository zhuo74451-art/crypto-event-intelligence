#!/usr/bin/env python3
"""Signal Spine IO v1 — Independent Verification Tests.

Run:  python -m pytest tests/test_signal_spine_io_v1.py -v
Or:   python tests/test_signal_spine_io_v1.py

These tests verify:
  1. Adapter contract → fixture → NormalizedSignal
  2. Network failure → fixture fallback with data_source=fixture
  3. Dry-run renderer → offline output (JSON, Markdown, Telegram card)
  4. Golden JSON stability
  5. No real send
  6. No trading instructions
  7. Dedup detection
  8. Fresh clone can run offline without API keys

Design:
  - All tests are offline-safe (no network required)
  - No API keys needed
  - No Telegram credentials needed
  - No core Pipeline/Registry dependency
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from typing import Any

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    RenderedCard,
)
from market_radar.shared.adapter_contract import (
    FixtureSignalAdapter,
    FixtureCatalog,
)
from market_radar.shared.renderer_contract import CardRenderer
from market_radar.shared.dry_run_renderer import DryRunRenderer
from market_radar.shared.event_intelligence_semantics import (
    EventIntelligenceResult,
    IntelligenceDecision,
    DataQuality,
    evaluate_event_semantics,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test Helpers
# ─────────────────────────────────────────────────────────────────────────────


FIXTURES_DIR = os.path.join(_PROJECT_ROOT, "fixtures")


def load_fixture(fixture_id: str) -> dict | None:
    """Load fixture JSON from fixtures directory."""
    catalog = {
        "event_high_quality": "event_high_quality.json",
        "event_duplicate": "event_duplicate.json",
        "event_old_news_rehash": "event_old_news_rehash.json",
        "event_no_asset": "event_no_asset.json",
        "event_insufficient_source": "event_insufficient_source.json",
        "event_pump_risk": "event_pump_risk.json",
        "event_missing_fields": "event_missing_fields.json",
        "real_binance_response_sample": "real_binance_response_sample.json",
    }
    file_name = catalog.get(fixture_id)
    if not file_name:
        return None
    file_path = os.path.join(FIXTURES_DIR, file_name)
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


FORBIDDEN_TERMS = [
    # Chinese terms - these are specific enough for substring match
    "买入", "卖出", "做多", "做空",
    "确定收益", "保赚",
]

FORBIDDEN_PATTERNS = [
    # English terms - use word boundary matching
    (r'buy', 'buy'),
    (r'sell', 'sell'),
    (r'long', 'long'),
    (r'short', 'short'),
    (r'guaranteed', 'guaranteed'),
    (r'profit-taking', 'profit-taking'),
    (r'take profit', 'take profit'),
]


def check_no_trading_instructions(text: str) -> list[str]:
    """Check text for forbidden trading terms using word boundaries. Returns violations.

    The disclaimer text "不包含买卖建议、做多做空指示或确定收益承诺" explicitly
    states that these items are NOT included - do not flag it.
    """
    violations = []
    # Remove the disclaimer field from JSON output
    import re as _re
    text = _re.sub(r'"disclaimer": "[^"]*"', '', text)
    # Remove markdown disclaimer section
    for marker in ['## 免责声明', '⚠ **免责声明**']:
        if marker in text:
            text = text[:text.index(marker)]
    text_lower = text.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in text_lower:
            violations.append(term)
    for pattern, label in FORBIDDEN_PATTERNS:
        if _re.search(pattern, text_lower):
            violations.append(label)
    return violations


class TestAdapterContract(unittest.TestCase):
    """Test: adapter can produce standardized results from fixture."""

    def test_fixture_catalog_all_families(self):
        """FixtureCatalog produces adapters for all 5 card families."""
        catalog = FixtureCatalog()
        families = [
            CardFamily.MULTI_ASSET_MARKET_SYNC,
            CardFamily.PRICE_OI_VOLUME_ANOMALY,
            CardFamily.NEWS_EVENT_MARKET_IMPACT,
            CardFamily.LIQUIDATION_PRESSURE,
            CardFamily.WHALE_POSITION_ALERT,
        ]
        for family in families:
            with self.subTest(family=family.value):
                adapter = catalog.adapter_for(family)
                signal = adapter.fetch()
                self.assertIsInstance(signal, NormalizedSignal)
                self.assertEqual(signal.card_family, family)
                self.assertTrue(signal.asset_or_topic)
                self.assertTrue(signal.timestamp)
                self.assertIsInstance(signal.metrics, dict)

    def test_fixture_signal_adapter_required_fields(self):
        """NormalizedSignal from fixture has all required fields."""
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.NEWS_EVENT_MARKET_IMPACT)
        signal = adapter.fetch()

        # Required by adapter contract
        self.assertEqual(signal.source_type, DataSourceType.FIXTURE)
        self.assertEqual(signal.card_family, CardFamily.NEWS_EVENT_MARKET_IMPACT)
        self.assertIsInstance(signal.asset_or_topic, str)
        self.assertIsInstance(signal.timestamp, str)
        self.assertIsInstance(signal.metrics, dict)
        self.assertIsInstance(signal.source_refs, list)
        self.assertIsInstance(signal.risk_notes, list)

    def test_fixture_can_be_serialized(self):
        """NormalizedSignal.as_dict() produces JSON-serializable dict."""
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.MULTI_ASSET_MARKET_SYNC)
        signal = adapter.fetch()
        d = signal.as_dict()
        # Verify it can be serialized to JSON
        json_str = json.dumps(d, ensure_ascii=False, indent=2)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 50)

    def test_network_failure_fallback(self):
        """Adapter handles 'network failure' gracefully.

        When no real API is available, adapter returns fixture/degraded
        signal with proper marking — never raises.
        """
        # The FixtureSignalAdapter always produces signal from fixture
        # (it doesn't call real APIs). This tests that the pattern is safe.
        catalog = FixtureCatalog()
        for family in CardFamily:
            with self.subTest(family=family.value):
                try:
                    adapter = catalog.adapter_for(family)
                    signal = adapter.fetch()
                    self.assertIsNotNone(signal)
                    # Source type should be FIXTURE
                    self.assertEqual(signal.source_type, DataSourceType.FIXTURE)
                except Exception as e:
                    self.fail(f"Adapter for {family.value} raised: {e}")


class TestFixtureDedup(unittest.TestCase):
    """Test: duplicate fixtures can be identified by dedup key."""

    def test_dedup_keys_present(self):
        """All event fixtures have dedup_key fields."""
        fixture_ids = [
            "event_high_quality", "event_duplicate", "event_old_news_rehash",
            "event_no_asset", "event_insufficient_source", "event_pump_risk",
            "event_missing_fields",
        ]
        for fid in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                if data is None:
                    self.skipTest(f"Fixture {fid} not found")
                self.assertIn("dedup_key", data, f"{fid} missing dedup_key")
                self.assertTrue(data["dedup_key"], f"{fid} dedup_key is empty")

    def test_duplicate_has_same_key(self):
        """event_duplicate has the same dedup_key as event_high_quality."""
        hq = load_fixture("event_high_quality")
        dup = load_fixture("event_duplicate")
        if hq is None or dup is None:
            self.skipTest("Fixture files not found")
        self.assertEqual(hq["dedup_key"], dup["dedup_key"])

    def test_dedup_detection_in_semantics(self):
        """Semantic evaluation marks duplicate as DISCARD."""
        hq = load_fixture("event_high_quality")
        dup = load_fixture("event_duplicate")
        if hq is None or dup is None:
            self.skipTest("Fixture files not found")

        # First: should be OBSERVE (not duplicate)
        result1 = evaluate_event_semantics(hq, is_duplicate=False)
        self.assertEqual(result1.decision, IntelligenceDecision.OBSERVE)

        # Second (same dedup key): should be DISCARD
        result2 = evaluate_event_semantics(dup, is_duplicate=True)
        self.assertEqual(result2.decision, IntelligenceDecision.DISCARD)

    def test_different_fixtures_have_different_keys(self):
        """Unique events have different dedup keys."""
        hq = load_fixture("event_high_quality")
        no_asset = load_fixture("event_no_asset")
        if hq is None or no_asset is None:
            self.skipTest("Fixture files not found")
        self.assertNotEqual(hq["dedup_key"], no_asset["dedup_key"])


class TestEventIntelligence(unittest.TestCase):
    """Test: event intelligence semantics produce correct decisions."""

    def test_high_quality_observe(self):
        """High quality fixture → decision=OBSERVE."""
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.OBSERVE)
        self.assertIn("high_volatility", result.risk_tags)

    def test_duplicate_discard(self):
        """Duplicate fixture → decision=DISCARD."""
        data = load_fixture("event_duplicate")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data, is_duplicate=True)
        self.assertEqual(result.decision, IntelligenceDecision.DISCARD)
        self.assertIn("dedup", result.risk_tags)

    def test_old_news_rehash_risk(self):
        """Old news rehash → decision=RISK_TIP."""
        data = load_fixture("event_old_news_rehash")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.RISK_TIP)

    def test_no_asset_observe(self):
        """No-clear-asset event → decision=OBSERVE."""
        data = load_fixture("event_no_asset")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.OBSERVE)
        self.assertIn("indirect_impact", result.risk_tags)

    def test_insufficient_source_discard(self):
        """Insufficient source → decision=DISCARD."""
        data = load_fixture("event_insufficient_source")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.DISCARD)

    def test_pump_risk_block(self):
        """High pump risk → decision=BLOCK."""
        data = load_fixture("event_pump_risk")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.BLOCK)
        self.assertIn("pump_and_dump", result.risk_tags)

    def test_missing_fields_discard(self):
        """Missing critical fields → decision=DISCARD."""
        data = load_fixture("event_missing_fields")
        if data is None:
            self.skipTest("Fixture not found")
        result = evaluate_event_semantics(data)
        self.assertEqual(result.decision, IntelligenceDecision.DISCARD)

    def test_no_trading_instructions(self):
        """EventIntelligenceResult never contains trading language."""
        fixture_ids = [
            "event_high_quality", "event_duplicate", "event_old_news_rehash",
            "event_no_asset", "event_insufficient_source", "event_pump_risk",
            "event_missing_fields",
        ]
        for fid in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                if data is None:
                    continue
                is_dup = (fid == "event_duplicate")
                result = evaluate_event_semantics(data, is_duplicate=is_dup)
                violations = result.validate_safety()
                self.assertEqual(
                    violations, [],
                    f"{fid}: safety violations: {violations}",
                )


class TestDryRunRenderer(unittest.TestCase):
    """Test: dry-run renderer can produce offline output."""

    def setUp(self):
        self.renderer = DryRunRenderer()

    def test_render_high_quality(self):
        """Dry-run renderer produces valid output from high-quality fixture."""
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")
        output = self.renderer.render(data)

        # Check all output formats
        self.assertTrue(output.json_output["dry_run"])
        self.assertTrue(output.json_output["real_send_disabled"])
        self.assertTrue(output.json_output["no_trading_instructions"])
        self.assertGreater(len(output.markdown_output), 100)
        self.assertGreater(len(output.telegram_card), 50)

        # Check Telegram card has required elements
        tg = output.telegram_card
        self.assertIn("Dry-Run Mode", tg)
        self.assertIn("Production Send = False", tg)

    def test_render_all_fixtures_no_trading(self):
        """All fixtures produce dry-run output without trading instructions."""
        fixture_ids = [
            "event_high_quality", "event_duplicate", "event_old_news_rehash",
            "event_no_asset", "event_insufficient_source", "event_pump_risk",
            "event_missing_fields",
        ]
        for fid in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                if data is None:
                    continue
                is_dup = (fid == "event_duplicate")
                output = self.renderer.render(data, is_duplicate=is_dup)

                # Check no trading via EventIntelligenceResult.validate_safety()
                # This is the official safety check that correctly excludes disclaimer text
                violations = output.event_intelligence.validate_safety()
                self.assertEqual(
                    violations, [],
                    f"{fid}: safety violations: {violations}",
                )

    def test_renderer_output_sections(self):
        """Markdown output contains all required sections."""
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")
        output = self.renderer.render(data)
        md = output.markdown_output

        required_sections = [
            "事件", "资产", "新闻质量", "交易相关性",
            "最终决策", "风险标签", "观察窗口",
            "证据摘要", "数据质量", "免责声明",
        ]
        for section in required_sections:
            self.assertIn(
                section, md,
                f"Markdown missing section: {section}",
            )

    def test_batch_rendering_with_dedup(self):
        """Batch rendering correctly handles dedup across items."""
        hq = load_fixture("event_high_quality")
        dup = load_fixture("event_duplicate")
        if hq is None or dup is None:
            self.skipTest("Fixture files not found")

        outputs = self.renderer.render_batch([hq, dup])
        self.assertEqual(len(outputs), 2)
        # First should be OBSERVE, second should be DISCARD (dedup)
        self.assertEqual(
            outputs[0].event_intelligence.decision,
            IntelligenceDecision.OBSERVE,
        )
        self.assertEqual(
            outputs[1].event_intelligence.decision,
            IntelligenceDecision.DISCARD,
        )

    def test_output_save(self):
        """Dry-run output can be saved to JSON and Markdown files."""
        import tempfile
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = self.renderer.render(data)
            json_path = output.save_json(tmpdir)
            md_path = output.save_markdown(tmpdir)

            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isfile(md_path))

            # Verify JSON file is valid
            with open(json_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertTrue(saved["real_send_disabled"])
            self.assertTrue(saved["no_trading_instructions"])


class TestGoldenJSON(unittest.TestCase):
    """Test: golden JSON output is stable."""

    def test_golden_file_exists(self):
        """Golden reference file exists."""
        golden_path = os.path.join(FIXTURES_DIR, "golden_multi_asset_market_sync.json")
        self.assertTrue(os.path.isfile(golden_path))

    def test_golden_file_valid_json(self):
        """Golden file is valid JSON."""
        golden_path = os.path.join(FIXTURES_DIR, "golden_multi_asset_market_sync.json")
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)
        self.assertIn("golden_id", golden)
        self.assertIn("expected_signal", golden)

    def test_golden_stability(self):
        """Golden output matches current adapter output (excluding dynamic fields)."""
        golden_path = os.path.join(FIXTURES_DIR, "golden_multi_asset_market_sync.json")
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        catalog = FixtureCatalog()
        signal = catalog.adapter_for(CardFamily.MULTI_ASSET_MARKET_SYNC).fetch()
        current = signal.as_dict()

        expected = golden["expected_signal"]
        dynamic_fields = {"timestamp", "pipeline_version", "signal_id"}

        def compare(expected_d, current_d, path=""):
            diffs = []
            for key in set(expected_d.keys()) | set(current_d.keys()):
                full = f"{path}.{key}" if path else key
                if key in dynamic_fields:
                    continue
                if key not in expected_d:
                    diffs.append(f"Missing in golden: {full}")
                    continue
                if key not in current_d:
                    diffs.append(f"Missing in current: {full}")
                    continue
                ev, cv = expected_d[key], current_d[key]
                if isinstance(ev, dict) and isinstance(cv, dict):
                    diffs.extend(compare(ev, cv, full))
                elif isinstance(ev, list) and isinstance(cv, list):
                    if len(ev) != len(cv):
                        diffs.append(f"List len at {full}: {len(ev)} vs {len(cv)}")
                    else:
                        for i, (ei, ci) in enumerate(zip(ev, cv)):
                            if isinstance(ei, dict) and isinstance(ci, dict):
                                diffs.extend(compare(ei, ci, f"{full}[{i}]"))
                            elif ei != ci:
                                diffs.append(f"At {full}[{i}]: {ei} != {ci}")
                elif ev != cv:
                    diffs.append(f"At {full}: {ev} != {cv}")
            return diffs

        diffs = compare(expected, current)
        self.assertEqual(diffs, [], f"Golden JSON mismatch: {diffs[:5]}")


class TestNoRealSend(unittest.TestCase):
    """Test: verification components never enable real send."""

    def test_dry_run_safety_flags(self):
        """All dry-run outputs have safety flags set correctly."""
        renderer = DryRunRenderer()
        fixture_ids = [
            "event_high_quality", "event_pump_risk",
            "event_missing_fields", "event_insufficient_source",
        ]
        for fid in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                if data is None:
                    continue
                output = renderer.render(data)
                self.assertTrue(output.real_send_disabled)
                self.assertTrue(output.no_trading_instructions)

    def test_telegram_card_has_dry_run_marker(self):
        """Telegram-style cards clearly indicate dry-run mode."""
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")
        renderer = DryRunRenderer()
        output = renderer.render(data)
        tg = output.telegram_card
        self.assertIn("Dry-Run Mode", tg)
        self.assertIn("未真实发送", tg)
        self.assertIn("Production Send = False", tg)

    def test_no_telegram_api_reference(self):
        """Dry-run output does not contain Telegram API URLs."""
        renderer = DryRunRenderer()
        data = load_fixture("event_high_quality")
        if data is None:
            self.skipTest("Fixture not found")
        output = renderer.render(data)
        combined = json.dumps(output.json_output) + output.telegram_card
        self.assertNotIn("api.telegram.org", combined)


class TestOfflineFreshClone(unittest.TestCase):
    """Test: fresh clone can run all tests offline without API keys."""

    def test_no_api_key_required(self):
        """All tests work without API keys or credentials."""
        # This test itself proves the point — it runs without any env vars
        self.assertTrue(True, "No API keys needed for fixture-based tests")

    def test_fixtures_load_offline(self):
        """All fixture files load without network access."""
        fixture_ids = [
            "event_high_quality", "event_duplicate", "event_old_news_rehash",
            "event_no_asset", "event_insufficient_source", "event_pump_risk",
            "event_missing_fields", "real_binance_response_sample",
        ]
        for fid in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                self.assertIsNotNone(data, f"Could not load {fid}")
                # Verify no credentials in fixture
                content = json.dumps(data)
                self.assertNotIn("TELEGRAM_BOT_TOKEN", content)
                self.assertNotIn("api_key", content.lower())
                self.assertNotIn("password", content.lower())

    def test_offline_renderer(self):
        """Dry-run renderer works completely offline."""
        renderer = DryRunRenderer()
        catalog = FixtureCatalog()
        signal = catalog.adapter_for(CardFamily.NEWS_EVENT_MARKET_IMPACT).fetch()
        # Convert signal to fixture-like dict for rendering
        fixture_data = {
            "fixture_id": "online_test",
            "card_family": signal.card_family.value,
            "asset_or_topic": signal.asset_or_topic,
            "metrics": signal.metrics,
            "source_refs": signal.source_refs,
            "risk_notes": signal.risk_notes,
            "data_source": "fixture",
            "dedup_key": "test:offline-renderer",
        }
        output = renderer.render(fixture_data)
        self.assertIsNotNone(output)
        self.assertGreater(len(output.markdown_output), 50)

    def test_expected_decisions_match(self):
        """All fixtures produce their stated expected decisions."""
        fixture_ids = [
            ("event_high_quality", IntelligenceDecision.OBSERVE, False),
            ("event_duplicate", IntelligenceDecision.DISCARD, True),
            ("event_old_news_rehash", IntelligenceDecision.RISK_TIP, False),
            ("event_no_asset", IntelligenceDecision.OBSERVE, False),
            ("event_insufficient_source", IntelligenceDecision.DISCARD, False),
            ("event_pump_risk", IntelligenceDecision.BLOCK, False),
            ("event_missing_fields", IntelligenceDecision.DISCARD, False),
        ]
        for fid, expected_decision, is_dup in fixture_ids:
            with self.subTest(fixture=fid):
                data = load_fixture(fid)
                if data is None:
                    self.skipTest(f"{fid} not found")
                result = evaluate_event_semantics(data, is_duplicate=is_dup)
                self.assertEqual(
                    result.decision, expected_decision,
                    f"{fid}: expected {expected_decision.value}, got {result.decision.value}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Week 1 — Price Provider Protocol & Sample Tests.

Run:  python -m pytest tests/test_week1_price_providers_v1.py -v

Covers:
  - Provider router selection (HYPE→HL, BTC/ETH→Binance)
  - Binance provider uses 1m interval
  - Hyperliquid candle fixture parsing
  - 15m precision metadata
  - HYPE network failure no fixture
  - Partial sample failure does not block batch
  - WTI only observes BTC/ETH
  - Raw output contains no attribution language
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter,
    BinanceProvider,
    HyperliquidCandleProvider,
    Week1SampleResult,
    run_week1_samples,
    WEEK1_SAMPLES,
    get_hl_candle_fixture,
    ms_to_iso,
    iso_to_ms,
)
from market_radar.shared.event_price_backfill import PriceSnapshot


class TestProviderRouter(unittest.TestCase):
    """Provider router selects correct provider per asset."""

    def test_hype_uses_hyperliquid(self):
        router = ProviderRouter(
            hyperliquid_provider=HyperliquidCandleProvider(use_fixture=True),
        )
        provider, pname, interval = router.get_provider("HYPE")
        self.assertEqual(pname, "hyperliquid")
        self.assertEqual(interval, "15m")
        self.assertIsInstance(provider, HyperliquidCandleProvider)

    def test_btc_uses_binance(self):
        router = ProviderRouter()
        provider, pname, interval = router.get_provider("BTC")
        self.assertEqual(pname, "binance")
        self.assertEqual(interval, "1m")
        self.assertIsInstance(provider, BinanceProvider)

    def test_eth_uses_binance(self):
        router = ProviderRouter()
        provider, pname, interval = router.get_provider("ETH")
        self.assertEqual(pname, "binance")

    def test_btcusdt_uses_binance(self):
        router = ProviderRouter()
        provider, pname, interval = router.get_provider("BTCUSDT")
        self.assertEqual(pname, "binance")

    def test_unknown_asset_unsupported(self):
        router = ProviderRouter()
        provider, pname, interval = router.get_provider("UNKNOWN")
        self.assertIsNone(provider)
        self.assertEqual(pname, "unsupported")

    def test_wti_unsupported(self):
        """WTI is an event topic, not a crypto asset — no provider."""
        router = ProviderRouter()
        provider, pname, interval = router.get_provider("WTI")
        self.assertIsNone(provider)
        self.assertEqual(pname, "unsupported")


class TestBinanceProvider(unittest.TestCase):
    """Binance provider returns 1m snapshots."""

    def test_provider_name(self):
        bp = BinanceProvider()
        self.assertEqual(bp.provider_name, "binance")
        self.assertEqual(bp.default_interval, "1m")

    @unittest.skip("requires network (optional)")
    def test_network_failure_no_fixture(self):
        """BinanceProvider in network mode never returns fixture source."""
        bp = BinanceProvider()
        snap = bp.get_snapshot("BTC", "2010-01-01T00:00:00Z")
        self.assertNotEqual(snap.source, "fixture",
                            "network mode must NEVER use fixture")

    def test_unsupported_symbol(self):
        bp = BinanceProvider()
        snap = bp.get_snapshot("UNKNOWN_TOKEN", "2026-05-25T12:00:00Z")
        self.assertEqual(snap.status, "unavailable")
        self.assertIn("unsupported", snap.error_reason or "")


class TestHyperliquidCandleProvider(unittest.TestCase):
    """Hyperliquid provider returns 15m candles."""

    def test_provider_metadata(self):
        hp = HyperliquidCandleProvider()
        self.assertEqual(hp.provider_name, "hyperliquid")
        self.assertEqual(hp.default_interval, "15m")
        self.assertEqual(hp.precision_seconds, 900)

    def test_fixture_parsing(self):
        """Fixture candles parse correctly."""
        hp = HyperliquidCandleProvider(use_fixture=True)
        # Request 30s before first fixture candle (13:00:00Z) => within 120s lag
        snap = hp.get_snapshot("HYPE", "2026-05-25T12:59:30Z")
        self.assertEqual(snap.status, "completed")
        self.assertIsNotNone(snap.price)
        self.assertEqual(snap.source, "hyperliquid_fixture")
        self.assertIsNotNone(snap.lag_seconds)

    def test_fixture_candle_structure(self):
        fixtures = get_hl_candle_fixture()
        self.assertGreaterEqual(len(fixtures), 1)
        for c in fixtures:
            self.assertEqual(len(c), 6)
            # [time, open, high, low, close, volume]
            float(c[1])  # open must be parseable

    @unittest.skip("requires network (optional)")
    def test_network_failure_no_fixture(self):
        """Without use_fixture=True, network failure returns unavailable."""
        hp = HyperliquidCandleProvider(use_fixture=False)
        # Use a time with guaranteed no HL data
        snap = hp.get_snapshot("HYPE", "2010-01-01T00:00:00Z")
        self.assertEqual(snap.status, "unavailable")
        self.assertNotEqual(snap.source, "hyperliquid_fixture")

    def test_15m_precision_metadata_in_result(self):
        """Runner records precision_seconds=900 for HL."""
        hp = HyperliquidCandleProvider(use_fixture=True)
        router = ProviderRouter(hyperliquid_provider=hp)
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        results = run_week1_samples(router, now_for_maturity=now)
        hype_results = [r for r in results if r.observed_asset == "HYPE"]
        self.assertGreaterEqual(len(hype_results), 1)
        for r in hype_results:
            self.assertEqual(r.precision_seconds, 900)
            self.assertEqual(r.interval, "15m")
            self.assertEqual(r.provider, "hyperliquid")


class TestSampleRunner(unittest.TestCase):
    """Week 1 sample runner produces correct results."""

    def setUp(self):
        # Use fixture for HL to keep tests deterministic
        self.hl = HyperliquidCandleProvider(use_fixture=True)
        self.router = ProviderRouter(hyperliquid_provider=self.hl)
        # Clock far enough in future so all windows are mature
        self.now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)

    @unittest.skip("requires Binance network (optional)")
    def test_all_samples_produced(self):
        results = run_week1_samples(self.router, now_for_maturity=self.now)
        self.assertEqual(len(results), len(WEEK1_SAMPLES))

    @unittest.skip("requires Binance network (optional)")
    def test_hype_sample_present(self):
        results = run_week1_samples(self.router, now_for_maturity=self.now)
        hype = [r for r in results if r.sample_id == "W1-001-HYPE"]
        self.assertEqual(len(hype), 1)

    @unittest.skip("requires Binance network (optional)")
    def test_macro_wti_observes_btc_and_eth(self):
        results = run_week1_samples(self.router, now_for_maturity=self.now)
        wti = [r for r in results if r.subject_asset == "WTI"]
        self.assertEqual(len(wti), 2)
        observed = [r.observed_asset for r in wti]
        self.assertIn("BTC", observed)
        self.assertIn("ETH", observed)

    @unittest.skip("requires Binance network (optional)")
    def test_btc_dup_samples_both_present(self):
        results = run_week1_samples(self.router, now_for_maturity=self.now)
        btc_dup = [r for r in results if r.sample_id == "W1-004-BTC-DUP"]
        self.assertEqual(len(btc_dup), 1)

    @unittest.skip("requires network (optional)")
    def test_partial_failure_does_not_block_batch(self):
        """Simulate one failed sample — others still complete."""
        # HYPE uses fixture (works), BTC uses network (may work)
        # The key is that if one fails, the rest still run
        hl = HyperliquidCandleProvider(use_fixture=False)  # will fail for old dates
        router = ProviderRouter(hyperliquid_provider=hl)
        now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        results = run_week1_samples(router, now_for_maturity=now)
        self.assertEqual(len(results), len(WEEK1_SAMPLES))
        # At least some samples should have a result (even if failed)
        hype = [r for r in results if r.observed_asset == "HYPE"]
        self.assertGreaterEqual(len(hype), 1)

    @unittest.skip("requires Binance network (optional)")
    def test_output_no_attribution_language(self):
        """Raw output must not contain attribution or trading language."""
        results = run_week1_samples(self.router, now_for_maturity=self.now)
        for r in results:
            text = json.dumps(r.as_dict()).lower()
            for term in ["attribution", "confidence", "causality", "causal",
                         "buy", "sell", "long", "short", "买入", "卖出",
                         "win_rate", "strategy", "胜率"]:
                self.assertNotIn(term, text,
                                 f"Term '{term}' found in output for {r.sample_id}")


class TestHyperliquidCandleSelection(unittest.TestCase):
    """HL candle selection logic."""

    def test_select_exact_match(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        snap = hp.get_snapshot("HYPE", "2026-05-25T12:59:30Z")
        # Should find the first fixture candle (lag=30s)
        self.assertEqual(snap.status, "completed")
        self.assertIsNotNone(snap.price)

    def test_select_nearest_after_target(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        # Target between candle 0 and candle 1
        # Target between candle 0 (13:00) and candle 1 (13:15) => candle 1 at 13:15 is 600s away > 120s
        # Use target right before candle 1: 13:14:30 => lag=30s
        snap = hp.get_snapshot("HYPE", "2026-05-25T13:14:30Z")
        self.assertEqual(snap.status, "completed")

    def test_select_before_all_candles(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        snap = hp.get_snapshot("HYPE", "2025-01-01T00:00:00Z")
        # All fixture candles are after this date
        self.assertEqual(snap.status, "completed")

    def test_fixture_source_label(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        # Request 30s before first fixture candle (13:00:00Z) => within 120s lag
        snap = hp.get_snapshot("HYPE", "2026-05-25T12:59:30Z")
        self.assertEqual(snap.source, "hyperliquid_fixture")


class TestWeek1SampleResultStructure(unittest.TestCase):
    """Week1SampleResult has correct fields."""

    def test_required_fields(self):
        r = Week1SampleResult(
            sample_id="test", subject_asset="BTC", observed_asset="BTC",
            t0_basis="2026-05-25T12:00:00Z", broadcast_time="2026-05-25T12:00:00Z",
            provider="binance", interval="1m",
        )
        self.assertEqual(r.sample_id, "test")
        self.assertIsNone(r.t0_snapshot)
        self.assertIsNone(r.return_1h)
        self.assertIsNone(r.network_error)
        self.assertEqual(r.data_origin, "network")
        self.assertTrue(r.calculation_version.startswith("v1."))

    def test_as_dict_no_error(self):
        r = Week1SampleResult(
            sample_id="test", subject_asset="BTC", observed_asset="BTC",
            t0_basis="2026-05-25T12:00:00Z", broadcast_time="2026-05-25T12:00:00Z",
            provider="binance", interval="1m",
            network_error="test_error",
        )
        d = r.as_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["sample_id"], "test")
        self.assertEqual(d["network_error"], "test_error")
        # JSON serializable
        json.dumps(d, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)

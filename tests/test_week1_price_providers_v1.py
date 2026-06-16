#!/usr/bin/env python3
"""Week 1 RC — Price Provider Protocol, Cache & Consistency Tests."""

import json
import sys
import unittest
from datetime import datetime, timezone
from copy import deepcopy

PROJ = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter, BinanceProvider, HyperliquidCandleProvider,
    parse_hl_candle, parse_hl_candles, HLCandle,
    select_nearest_candle, get_hl_candle_fixture,
    Week1ObservationResult, Week1WindowResult,
    make_cache_key, make_price_observation_key,
    SnapshotCache, PriceObservationBundle, fetch_bundle,
    run_week1, W1_SAMPLES, W1_WTI, ms_to_iso, iso_to_ms,
)
from market_radar.shared.event_price_backfill import PriceSnapshot

FB = 1779714000000


# ═══════════════════════════════════════════════════════════════════════════
# HL Candle Parsing
# ═══════════════════════════════════════════════════════════════════════════

class TestHLCandleParsing(unittest.TestCase):
    def test_parse_valid(self):
        d = {"t": FB, "T": FB+899999, "s": "HYPE", "i": "15m",
             "o": "12.50", "c": "12.65", "h": "12.80", "l": "12.30", "v": "500000", "n": "125"}
        c = parse_hl_candle(d)
        self.assertIsNotNone(c)
        self.assertEqual(c.open, 12.50)

    def test_missing_t(self):
        self.assertIsNone(parse_hl_candle({"o": "12.50"}))

    def test_missing_o(self):
        self.assertIsNone(parse_hl_candle({"t": FB}))

    def test_bad_price(self):
        self.assertIsNone(parse_hl_candle({"t": FB, "o": "xyz"}))

    def test_not_dict(self):
        self.assertIsNone(parse_hl_candle("abc"))
        self.assertIsNone(parse_hl_candle(None))

    def test_parse_list_filters_bad(self):
        good = {"t": FB, "o": "12.50", "s": "HYPE", "i": "15m"}
        self.assertEqual(len(parse_hl_candles([good, {"o": "x"}, "bad"])), 1)

    def test_fixture_parses(self):
        self.assertEqual(len(parse_hl_candles(get_hl_candle_fixture())), 3)


# ═══════════════════════════════════════════════════════════════════════════
# Nearest Candle
# ═══════════════════════════════════════════════════════════════════════════

class TestNearestCandle(unittest.TestCase):
    def setUp(self):
        self.candles = [
            HLCandle(FB, FB+899999, "HYPE", "15m", 12.50, 12.80, 12.30, 12.65, 500000, 125),
            HLCandle(FB+900000, FB+1799999, "HYPE", "15m", 12.65, 12.90, 12.40, 12.75, 450000, 110),
            HLCandle(FB+1800000, FB+2699999, "HYPE", "15m", 12.75, 13.10, 12.60, 12.95, 520000, 135),
        ]

    def test_exact(self):
        c, info = select_nearest_candle(self.candles, FB)
        self.assertIsNotNone(c); self.assertEqual(info["signed_lag_seconds"], 0)

    def test_1302_chooses_1300(self):
        c, info = select_nearest_candle(self.candles, iso_to_ms("2026-05-25T13:02:00Z"))
        self.assertIsNotNone(c); self.assertEqual(c.open, 12.50)
        self.assertEqual(info["signed_lag_seconds"], -120)

    def test_450s_accepted(self):
        c, info = select_nearest_candle(self.candles, FB+450000)
        self.assertIsNotNone(c); self.assertIsNone(info.get("error_reason"))

    def test_451s_rejected(self):
        c, info = select_nearest_candle(self.candles, FB-500000)
        self.assertIsNone(c); self.assertIn("max_lag_exceeded", info.get("error_reason", ""))

    def test_tie_earlier(self):
        c, info = select_nearest_candle(self.candles, FB+450000)
        self.assertIsNotNone(c); self.assertEqual(c.open, 12.50)

    def test_empty(self):
        self.assertIsNone(select_nearest_candle([], FB)[0])


# ═══════════════════════════════════════════════════════════════════════════
# HL Fixture
# ═══════════════════════════════════════════════════════════════════════════

class TestHLFixture(unittest.TestCase):
    def test_1302_completed(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        snap, info = hp.get_snapshot("HYPE", "2026-05-25T13:02:00Z")
        self.assertEqual(snap.status, "completed")
        self.assertEqual(info["signed_lag_seconds"], -120)

    def test_no_network_not_fixture(self):
        hp = HyperliquidCandleProvider(use_fixture=False)
        snap, _ = hp.get_snapshot("HYPE", "2010-01-01T00:00:00Z")
        self.assertEqual(snap.status, "unavailable")
        self.assertNotEqual(snap.source, "hyperliquid_fixture")


# ═══════════════════════════════════════════════════════════════════════════
# Binance Provider
# ═══════════════════════════════════════════════════════════════════════════

class TestBinance(unittest.TestCase):
    def test_name(self):
        self.assertEqual(BinanceProvider().provider_name, "binance")

    def test_unsupported(self):
        snap, _ = BinanceProvider().get_snapshot("UNKNOWN", "2026-05-25T12:00:00Z")
        self.assertEqual(snap.status, "unavailable")

    def test_not_fixture(self):
        snap, _ = BinanceProvider().get_snapshot("BTC", "2010-01-01T00:00:00Z")
        self.assertNotEqual(snap.source, "fixture")


# ═══════════════════════════════════════════════════════════════════════════
# Cache & Key Tests
# ═══════════════════════════════════════════════════════════════════════════

class CountingProvider:
    """Mock provider that counts get_snapshot calls."""
    def __init__(self, snap=None):
        self.call_count = 0
        self._snap = snap or PriceSnapshot(symbol="TEST", price=100.0, status="completed",
                                            source="mock", requested_time="2026-05-25T12:00:00Z")

    def get_snapshot(self, symbol="TEST", rtime="2026-05-25T12:00:00Z", interval="1m", max_lag=120):
        self.call_count += 1
        info = {"selection_policy": "mock", "precision_seconds": 60,
                "signed_lag_seconds": 0, "absolute_lag_seconds": 0}
        return deepcopy(self._snap), info


class TestSnapshotCache(unittest.TestCase):
    def test_cache_key_format(self):
        key = make_cache_key("binance", "BTCUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        self.assertIn("binance", key); self.assertIn("BTCUSDT", key)
        self.assertIn("2026-05-25T16:12:00Z", key)

    def test_same_key_fetches_once(self):
        """Same key across two calls = one network request."""
        provider = CountingProvider()
        router = ProviderRouter(binance_provider=provider, hyperliquid_provider=CountingProvider())
        cache = SnapshotCache(router)
        s1, _, _, _, _ = cache.get("BTC", "2026-05-25T16:12:00Z")
        s2, _, _, _, _ = cache.get("BTC", "2026-05-25T16:12:00Z")
        self.assertEqual(provider.call_count, 1)  # only one real fetch
        self.assertIsNotNone(s1.price)
        self.assertIsNotNone(s2.price)

    def test_different_keys_separate_fetches(self):
        provider = CountingProvider()
        router = ProviderRouter(binance_provider=provider, hyperliquid_provider=CountingProvider())
        cache = SnapshotCache(router)
        cache.get("BTC", "2026-05-25T16:12:00Z")
        cache.get("BTC", "2026-05-25T11:34:00Z")  # different time
        self.assertEqual(provider.call_count, 2)

    def test_cache_not_shared_across_instances(self):
        p1 = CountingProvider(); p2 = CountingProvider()
        r1 = ProviderRouter(binance_provider=p1); r2 = ProviderRouter(binance_provider=p2)
        c1 = SnapshotCache(r1); c2 = SnapshotCache(r2)
        c1.get("BTC", "2026-05-25T16:12:00Z")
        c2.get("BTC", "2026-05-25T16:12:00Z")
        self.assertEqual(p1.call_count, 1); self.assertEqual(p2.call_count, 1)


# ═══════════════════════════════════════════════════════════════════════════
# Price Observation Key & Reuse
# ═══════════════════════════════════════════════════════════════════════════

class TestPriceObservationKey(unittest.TestCase):
    def test_w1_003_and_w1_004_same_key(self):
        """w1_003 and w1_004 both BTC@16:12 → same observation key."""
        k1 = make_price_observation_key("binance", "BTCUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        k2 = make_price_observation_key("binance", "BTCUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        self.assertEqual(k1, k2)

    def test_different_times_different_keys(self):
        k1 = make_price_observation_key("binance", "BTCUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        k2 = make_price_observation_key("binance", "BTCUSDT", "2026-05-25T11:34:00Z", "1m", "first_after_target")
        self.assertNotEqual(k1, k2)

    def test_different_assets_different_keys(self):
        k1 = make_price_observation_key("binance", "BTCUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        k2 = make_price_observation_key("binance", "ETHUSDT", "2026-05-25T16:12:00Z", "1m", "first_after_target")
        self.assertNotEqual(k1, k2)


class TestObservationReuse(unittest.TestCase):
    def _make_router(self):
        hl = HyperliquidCandleProvider(use_fixture=True)
        bi = CountingProvider()
        return ProviderRouter(hyperliquid_provider=hl, binance_provider=bi)

    def test_w1_003_and_w1_004_reuse(self):
        """w1_004 reuses w1_003's observation (same key)."""
        router = self._make_router()
        now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        results = run_week1(router, now_maturity=now)
        w1_003 = next(r for r in results if r.sample_id == "w1_003")
        w1_004 = next(r for r in results if r.sample_id == "w1_004")

        self.assertTrue(w1_004.observation_reused,
                        "w1_004 should be marked as reused")
        self.assertEqual(w1_004.reused_from_result_id, "w1_003",
                         "w1_004 should reference w1_003")
        self.assertFalse(w1_003.observation_reused,
                         "w1_003 should NOT be reused")

    def test_w1_003_w1_004_identical_returns(self):
        router = self._make_router()
        now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        results = run_week1(router, now_maturity=now)
        w1_003 = next(r for r in results if r.sample_id == "w1_003")
        w1_004 = next(r for r in results if r.sample_id == "w1_004")

        for wn in ("return_1h", "return_4h", "return_24h"):
            fw = getattr(w1_003, wn); ew = getattr(w1_004, wn)
            if fw and ew:
                self.assertEqual(fw.return_decimal, ew.return_decimal,
                                 f"{wn}: w1_003 and w1_004 return_decimal differ")
                # Verify t0 snapshots match
                fts = fw.target_snapshot; ets = ew.target_snapshot
                if fts and ets:
                    self.assertEqual(fts.price, ets.price,
                                     f"{wn}: target price differs")

    def test_unique_observations_count(self):
        router = self._make_router()
        now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        results = run_week1(router, now_maturity=now)
        unique_poks = {r.price_observation_key for r in results}
        self.assertEqual(len(unique_poks), 5,
                         f"Expected 5 unique observations, got {len(unique_poks)}")


# ═══════════════════════════════════════════════════════════════════════════
# Consistency Validator
# ═══════════════════════════════════════════════════════════════════════════

class TestConsistency(unittest.TestCase):
    def setUp(self):
        self.hl = HyperliquidCandleProvider(use_fixture=True)
        self.bi = CountingProvider()
        self.router = ProviderRouter(hyperliquid_provider=self.hl, binance_provider=self.bi)
        self.now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        from research.validate_week1_price_dataset import validate
        self.validate_fn = validate

    def test_all_t0_basis_broadcast_time(self):
        for r in run_week1(self.router, self.now):
            self.assertEqual(r.t0_basis, "broadcast_time",
                             f"{r.result_id}: t0_basis must be 'broadcast_time'")

    def test_no_t0_unavailable_with_completed_window(self):
        for r in run_week1(self.router, self.now):
            t0 = r.t0_snapshot
            if t0 and t0.status != "completed":
                for wn in ("return_1h", "return_4h", "return_24h"):
                    w = getattr(r, wn)
                    if w:
                        self.assertNotEqual(w.status, "completed",
                                            f"{r.result_id}/{wn}: t0 not completed but window is")

    def test_completed_window_has_benchmark_snapshots(self):
        for r in run_week1(self.router, self.now):
            for wn in ("return_1h", "return_4h", "return_24h"):
                w = getattr(r, wn)
                if w and w.status == "completed":
                    self.assertIsNotNone(w.btc_benchmark_t0_snapshot)
                    self.assertIsNotNone(w.btc_benchmark_target_snapshot)
                    self.assertIsNotNone(w.eth_benchmark_t0_snapshot)

    def test_data_can_be_validated(self):
        results = run_week1(self.router, self.now)
        data = {
            "run_mode": "fixture",
            "observations_expected": 6, "observations_completed": 6,
            "observations_unavailable": 0, "observations_partial": 0,
            "samples_expected": 5,
            "network_errors": [],
            "results": [r.as_dict() for r in results],
        }
        passed, violations = self.validate_fn(data)
        if not passed:
            self.fail(f"Validator failed: {violations[:3]}")

    def test_validator_rejects_t0_unavailable_completed_window(self):
        bad_data = {
            "run_mode": "network",
            "samples_expected": 5, "observations_expected": 6,
            "observations_completed": 0, "observations_unavailable": 1,
            "observations_partial": 0,
            "network_errors": [],
            "results": [{
                "result_id": "bad_001",
                "t0_basis": "broadcast_time",
                "broadcast_time_utc": "2026-05-25T16:12:00Z",
                "t0_snapshot": {"symbol": "BTC", "status": "unavailable", "price": None},
                "return_1h": {"window": "1h", "status": "completed", "return_decimal": 0.01,
                              "target_snapshot": {"price": 100.0}},
                "return_4h": {"window": "4h", "status": "pending"},
                "return_24h": {"window": "24h", "status": "pending"},
                "price_observation_key": "test:bad",
                "observation_reused": False,
            }],
        }
        passed, violations = self.validate_fn(bad_data)
        self.assertFalse(passed, "Validator should reject t0 unavailable + completed window")
        self.assertTrue(any("impossible" in v for v in violations),
                        f"Expected impossible violation, got: {violations}")


# ═══════════════════════════════════════════════════════════════════════════
# Zero Value Handling
# ═══════════════════════════════════════════════════════════════════════════

class TestZeroValueHandling(unittest.TestCase):
    def test_signed_lag_zero(self):
        self.assertEqual(Week1WindowResult(window="1h", status="completed", signed_lag_seconds=0).as_dict()["signed_lag_seconds"], 0)

    def test_abnormal_zero(self):
        wr = Week1WindowResult(window="1h", status="completed", btc_abnormal_return_decimal=0.0)
        self.assertEqual(wr.as_dict()["btc_abnormal_return_decimal"], 0.0)

    def test_none_abnormal(self):
        wr = Week1WindowResult(window="1h", status="completed", btc_abnormal_return_decimal=None)
        self.assertIsNone(wr.as_dict()["btc_abnormal_return_decimal"])


# ═══════════════════════════════════════════════════════════════════════════
# Structures
# ═══════════════════════════════════════════════════════════════════════════

class TestStructures(unittest.TestCase):
    def test_observation_t0_basis(self):
        r = Week1ObservationResult(sample_id="w1_001", result_id="w1_001", subject_asset="HYPE",
            observed_asset="HYPE", broadcast_time_utc="2026-05-25T13:02:00Z",
            t0_basis="broadcast_time", provider="hyperliquid", interval="15m")
        self.assertEqual(r.t0_basis, "broadcast_time")

    def test_window_roundtrip(self):
        wr = Week1WindowResult(window="1h", status="completed", return_decimal=0.007353)
        self.assertEqual(wr.as_dict()["return_decimal"], 0.007353)

    def test_window_with_snapshot_roundtrip(self):
        snap = PriceSnapshot(symbol="BTCUSDT", price=100.0, status="completed", source="test",
                             requested_time="2026-05-25T12:00:00Z")
        wr = Week1WindowResult(window="1h", status="completed", target_snapshot=snap)
        self.assertEqual(wr.as_dict()["target_snapshot"]["price"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

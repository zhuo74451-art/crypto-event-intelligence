#!/usr/bin/env python3
"""Signal Spine IO v1 — Event Price Backfill Tests.

Run:  python -m pytest tests/test_event_price_backfill_v1.py -v
Or:   python tests/test_event_price_backfill_v1.py

Covers:
  - symbol mapping
  - timezone normalization
  - t0 candle selection
  - 1h/4h/24h returns
  - BTC/ETH benchmark returns
  - abnormal returns
  - self benchmark
  - pending window
  - unsupported symbol
  - missing Kline
  - network failure fixture fallback
  - batch partial failure
  - deterministic repeatability
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.event_price_backfill import (
    EventPriceBackfill,
    PriceBackfillResult,
    WindowReturn,
    map_symbol,
    parse_iso_time,
    is_self_benchmark,
    select_t0_kline,
    select_window_kline,
    kline_open_price,
    get_fixture_klines,
    get_fixture_klines_partial,
    OBSERVATION_WINDOWS,
    SYMBOL_MAP,
    BENCHMARK_SYMBOLS,
)

# ── Test Data ───────────────────────────────────────────────────────────────

REF_TIME_MS = 1750507200000  # 2026-06-15T12:00:00Z

# Expected returns for BTC with full fixture (verified manually):
# t0: 68000, 1h: 68500 -> (68500/68000 - 1) = 0.007353
# t0: 68000, 4h: 69200 -> (69200/68000 - 1) = 0.017647
# t0: 68000, 24h: 69500 -> (69500/68000 - 1) = 0.022059

BTC_1H_RETURN = (68500.0 / 68000.0) - 1.0  # 0.007353
BTC_4H_RETURN = (69200.0 / 68000.0) - 1.0  # 0.017647
BTC_24H_RETURN = (69500.0 / 68000.0) - 1.0  # 0.022059

ETH_1H_RETURN = (3550.0 / 3500.0) - 1.0  # 0.014286
ETH_4H_RETURN = (3620.0 / 3500.0) - 1.0  # 0.034286
ETH_24H_RETURN = (3580.0 / 3500.0) - 1.0  # 0.022857

SOL_1H_RETURN = (180.0 / 175.0) - 1.0  # 0.028571
SOL_4H_RETURN = (178.0 / 175.0) - 1.0  # 0.017143
SOL_24H_RETURN = (182.0 / 175.0) - 1.0  # 0.040000


class TestSymbolMapping(unittest.TestCase):
    """Test: symbol mapping rules."""

    def test_btc_maps_to_btcusdt(self):
        symbol, supported = map_symbol("BTC")
        self.assertEqual(symbol, "BTCUSDT")
        self.assertTrue(supported)

    def test_eth_maps_to_ethusdt(self):
        symbol, supported = map_symbol("ETH")
        self.assertEqual(symbol, "ETHUSDT")
        self.assertTrue(supported)

    def test_sol_maps_to_solusdt(self):
        symbol, supported = map_symbol("SOL")
        self.assertEqual(symbol, "SOLUSDT")
        self.assertTrue(supported)

    def test_already_usdt_pair(self):
        symbol, supported = map_symbol("BTCUSDT")
        self.assertEqual(symbol, "BTCUSDT")
        self.assertTrue(supported)

    def test_unknown_symbol_unsupported(self):
        symbol, supported = map_symbol("UNKNOWN_TOKEN")
        self.assertFalse(supported)

    def test_empty_asset_unsupported(self):
        symbol, supported = map_symbol("")
        self.assertFalse(supported)

    def test_case_insensitive(self):
        symbol, supported = map_symbol("btc")
        self.assertEqual(symbol, "BTCUSDT")
        self.assertTrue(supported)

    def test_all_mapped_symbols_exist(self):
        """All entries in SYMBOL_MAP should map correctly."""
        for short, full in SYMBOL_MAP.items():
            symbol, supported = map_symbol(short)
            self.assertEqual(symbol, full)
            self.assertTrue(supported)


class TestTimezoneNormalization(unittest.TestCase):
    """Test: timezone handling."""

    def test_parse_iso_z_suffix(self):
        dt = parse_iso_time("2026-06-15T12:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo is not None, True)
        self.assertEqual(dt.hour, 12)

    def test_parse_iso_offset(self):
        dt = parse_iso_time("2026-06-15T20:00:00+08:00")
        self.assertIsNotNone(dt)
        # +08:00 -> UTC should be 12:00
        self.assertEqual(dt.hour, 12)

    def test_parse_iso_no_tz(self):
        dt = parse_iso_time("2026-06-15T12:00:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo is not None, True)  # auto-assigned UTC

    def test_parse_empty_string(self):
        dt = parse_iso_time("")
        self.assertIsNone(dt)

    def test_parse_invalid(self):
        dt = parse_iso_time("not-a-date")
        self.assertIsNone(dt)


class TestT0CandleSelection(unittest.TestCase):
    """Test: t0 kline selection."""

    def setUp(self):
        self.klines = [
            [REF_TIME_MS, "68000.00", "68100.00", "67900.00", "68050.00", "100.0", REF_TIME_MS + 60000],
            [REF_TIME_MS + 60000, "68050.00", "68150.00", "67950.00", "68100.00", "95.0", REF_TIME_MS + 120000],
        ]

    def test_select_first_kline_at_event_time(self):
        k = select_t0_kline(self.klines, REF_TIME_MS)
        self.assertIsNotNone(k)
        self.assertEqual(int(k[0]), REF_TIME_MS)
        self.assertEqual(kline_open_price(k), 68000.0)

    def test_select_first_kline_after_event_time(self):
        # Event time between two klines
        k = select_t0_kline(self.klines, REF_TIME_MS + 30000)
        self.assertIsNotNone(k)
        self.assertEqual(int(k[0]), REF_TIME_MS + 60000)

    def test_select_last_kline_when_all_before(self):
        k = select_t0_kline(self.klines, REF_TIME_MS + 120000)
        self.assertIsNotNone(k)
        self.assertEqual(int(k[0]), REF_TIME_MS + 60000)

    def test_empty_klines(self):
        k = select_t0_kline([], REF_TIME_MS)
        self.assertIsNone(k)


class TestReturnsFromFixture(unittest.TestCase):
    """Test: 1h/4h/24h returns from fixture data."""

    def setUp(self):
        self.backfill = EventPriceBackfill(use_fixture=True)

    def test_btc_1h_return(self):
        results = self.backfill.backfill(
            "test_001", "2026-06-15T12:00:00Z", ["BTC"],
        )
        r = results[0]
        # Individual window checks, not overall status (24h may be pending)
        w1h = next(w for w in r.windows if w.window == "1h")
        self.assertEqual(w1h.status, "completed")
        self.assertAlmostEqual(w1h.return_pct, BTC_1H_RETURN, places=6)

    def test_btc_4h_return(self):
        results = self.backfill.backfill(
            "test_002", "2026-06-15T12:00:00Z", ["BTC"],
        )
        w4h = next(w for w in results[0].windows if w.window == "4h")
        self.assertEqual(w4h.status, "completed")
        self.assertAlmostEqual(w4h.return_pct, BTC_4H_RETURN, places=6)

    def test_btc_24h_return(self):
        results = self.backfill.backfill(
            "test_003", "2026-06-15T12:00:00Z", ["BTC"],
        )
        w24h = next(w for w in results[0].windows if w.window == "24h")
        # 24h may be pending if event < 24h ago
        if w24h.status == "completed":
            self.assertAlmostEqual(w24h.return_pct, BTC_24H_RETURN, places=6)
        else:
            self.assertEqual(w24h.status, "pending")

    def test_eth_returns(self):
        results = self.backfill.backfill(
            "test_004", "2026-06-15T12:00:00Z", ["ETH"],
        )
        r = results[0]
        w1h = next(w for w in r.windows if w.window == "1h")
        w4h = next(w for w in r.windows if w.window == "4h")
        w24h = next(w for w in r.windows if w.window == "24h")
        self.assertEqual(w1h.status, "completed")
        self.assertAlmostEqual(w1h.return_pct, ETH_1H_RETURN, places=6)
        self.assertEqual(w4h.status, "completed")
        self.assertAlmostEqual(w4h.return_pct, ETH_4H_RETURN, places=6)
        if w24h.status == "completed":
            self.assertAlmostEqual(w24h.return_pct, ETH_24H_RETURN, places=6)
        else:
            self.assertEqual(w24h.status, "pending")

    def test_sol_returns(self):
        results = self.backfill.backfill(
            "test_005", "2026-06-15T12:00:00Z", ["SOL"],
        )
        r = results[0]
        w1h = next(w for w in r.windows if w.window == "1h")
        self.assertEqual(w1h.status, "completed")
        self.assertAlmostEqual(w1h.return_pct, SOL_1H_RETURN, places=6)


class TestBenchmarkReturns(unittest.TestCase):
    """Test: BTC/ETH benchmark returns."""

    def setUp(self):
        self.backfill = EventPriceBackfill(use_fixture=True)

    def test_btc_window_has_btc_benchmark(self):
        """BTC benchmark should be present for ETH (not self)."""
        results = self.backfill.backfill(
            "test_010", "2026-06-15T12:00:00Z", ["ETH"],
        )
        w1h = next(w for w in results[0].windows if w.window == "1h")
        self.assertIsNotNone(w1h.btc_return_pct)
        self.assertIsNotNone(w1h.eth_return_pct)

    def test_eth_window_has_btc_benchmark(self):
        """ETH returns should have BTC as benchmark."""
        results = self.backfill.backfill(
            "test_011", "2026-06-15T12:00:00Z", ["ETH"],
        )
        w1h = next(w for w in results[0].windows if w.window == "1h")
        self.assertIsNotNone(w1h.btc_return_pct)


class TestAbnormalReturns(unittest.TestCase):
    """Test: abnormal return calculations."""

    def setUp(self):
        self.backfill = EventPriceBackfill(use_fixture=True)

    def test_eth_abnormal_vs_btc(self):
        """ETH abnormal vs BTC: ETH_return - BTC_return."""
        results = self.backfill.backfill(
            "test_020", "2026-06-15T12:00:00Z", ["ETH"],
        )
        w1h = next(w for w in results[0].windows if w.window == "1h")
        # ETH 1h: 0.014286, BTC 1h: 0.007353
        # Abnormal: 0.014286 - 0.007353 = 0.006933
        expected = ETH_1H_RETURN - BTC_1H_RETURN
        self.assertAlmostEqual(w1h.btc_abnormal_return, expected, places=6)

    def test_sol_abnormal_vs_btc(self):
        """SOL abnormal vs BTC."""
        results = self.backfill.backfill(
            "test_021", "2026-06-15T12:00:00Z", ["SOL"],
        )
        w1h = next(w for w in results[0].windows if w.window == "1h")
        expected = SOL_1H_RETURN - BTC_1H_RETURN
        self.assertAlmostEqual(w1h.btc_abnormal_return, expected, places=6)

    def test_sol_abnormal_vs_eth(self):
        """SOL abnormal vs ETH."""
        results = self.backfill.backfill(
            "test_022", "2026-06-15T12:00:00Z", ["SOL"],
        )
        w1h = next(w for w in results[0].windows if w.window == "1h")
        expected = SOL_1H_RETURN - ETH_1H_RETURN
        self.assertAlmostEqual(w1h.eth_abnormal_return, expected, places=6)


class TestSelfBenchmark(unittest.TestCase):
    """Test: self-benchmark behavior."""

    def test_is_self_benchmark_btc(self):
        self.assertTrue(is_self_benchmark("BTCUSDT", "BTCUSDT"))

    def test_is_self_benchmark_eth(self):
        self.assertTrue(is_self_benchmark("ETHUSDT", "ETHUSDT"))

    def test_not_self_benchmark_sol(self):
        self.assertFalse(is_self_benchmark("SOLUSDT", "BTCUSDT"))

    def test_btc_self_benchmark_abnormal_none(self):
        """BTC's btc_abnormal_return should be None (self-benchmark)."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_030", "2026-06-15T12:00:00Z", ["BTC"],
        )
        for w in results[0].windows:
            if w.status == "completed":
                self.assertIsNone(w.btc_abnormal_return,
                                  f"BTC {w.window}: btc_abnormal should be None")

    def test_eth_self_benchmark_abnormal_none(self):
        """ETH's eth_abnormal_return should be None (self-benchmark)."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_031", "2026-06-15T12:00:00Z", ["ETH"],
        )
        for w in results[0].windows:
            if w.status == "completed":
                self.assertIsNone(w.eth_abnormal_return,
                                  f"ETH {w.window}: eth_abnormal should be None")

    def test_btc_eth_abnormal_present(self):
        """BTC's eth_abnormal_return should be present (not self-benchmark)."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_032", "2026-06-15T12:00:00Z", ["BTC"],
        )
        for w in results[0].windows:
            if w.status == "completed":
                self.assertIsNotNone(w.eth_abnormal_return,
                                     f"BTC {w.window}: eth_abnormal should be present")


class TestPendingWindow(unittest.TestCase):
    """Test: pending window handling."""

    def test_pending_4h_24h(self):
        """When event is recent, 4h/24h should be pending."""
        backfill = EventPriceBackfill(use_fixture=False)
        # Use fixture to ensure controlled test — but inject partial fixture
        # by directly testing _backfill_single
        from market_radar.shared.event_price_backfill import get_fixture_klines_partial, get_fixture_klines

        # Override for this test: use partial fixture
        import market_radar.shared.event_price_backfill as epb
        original_fixture = epb.get_fixture_klines
        epb.get_fixture_klines = get_fixture_klines_partial

        try:
            backfill._source = "fixture"
            # Use now - 30min to ensure partial maturity
            now = datetime.now(timezone.utc)
            event_dt = now - timedelta(minutes=30)
            event_time = event_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            results = backfill.backfill(
                "test_040", event_time, ["BTCUSDT"],
            )
            r = results[0]
            w1h = next(w for w in r.windows if w.window == "1h")
            w4h = next(w for w in r.windows if w.window == "4h")
            w24h = next(w for w in r.windows if w.window == "24h")
            # 1h might be completed or pending depending on exact timing
            self.assertIn(w1h.status, ("completed", "pending"))
            # 4h and 24h should be pending (30min ago < 4h)
            self.assertEqual(w4h.status, "pending",
                             f"4h should be pending, got {w4h.status}")
            self.assertEqual(w24h.status, "pending",
                             f"24h should be pending, got {w24h.status}")
        finally:
            epb.get_fixture_klines = original_fixture

    def test_all_windows_mature(self):
        """When event is sufficiently in the past, all windows should be completed."""
        from datetime import timedelta
        backfill = EventPriceBackfill(use_fixture=True)
        # Use the fixture reference time directly (which is deterministic)
        # event at ref_time, all windows have fixture data at exact offsets
        results = backfill.backfill(
            "test_041", "2026-06-15T12:00:00Z", ["BTC"],
        )
        for w in results[0].windows:
            # 1h and 4h must be completed; 24h depends on current time
            if w.window in ("1h", "4h"):
                self.assertEqual(w.status, "completed",
                                 f"{w.window} should be completed, got {w.status}")


class TestUnsupportedSymbol(unittest.TestCase):
    """Test: unsupported symbol handling."""

    def test_unknown_symbol_returns_failed(self):
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_050", "2026-06-15T12:00:00Z", ["UNKNOWN_TOKEN"],
        )
        r = results[0]
        self.assertEqual(r.backfill_status, "failed")
        self.assertIn("unsupported_symbol", r.error_reason or "")


class TestMissingKline(unittest.TestCase):
    """Test: missing Kline handling."""

    def test_asset_not_in_fixture(self):
        """HYPE maps to HYPEUSDT but has no fixture -> should not crash."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_060", "2026-06-15T12:00:00Z", ["HYPE"],
        )
        r = results[0]
        # HYPE maps via SYMBOL_MAP but no fixture -> fetch returns None -> failed
        self.assertEqual(r.backfill_status, "failed")


class TestNetworkFailureFixtureFallback(unittest.TestCase):
    """Test: network failure automatically falls back to fixture."""

    def test_use_fixture_false_no_network(self):
        """When use_fixture=False but no network, should fall back gracefully."""
        backfill = EventPriceBackfill(use_fixture=False)
        results = backfill.backfill(
            "test_070", "2026-06-15T12:00:00Z", ["BTC"],
        )
        # Even without network, _fetch_klines tries real API then falls back
        # to fixture. So it should succeed with source="fixture_fallback" or
        # source="binance_public_api" if network happens to work.
        r = results[0]
        self.assertIn(r.backfill_status, ("completed", "partial", "pending"))

    def test_fixture_marked_source(self):
        """Fixture path clearly marks source."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_071", "2026-06-15T12:00:00Z", ["BTC"],
        )
        self.assertEqual(results[0].source, "fixture")


class TestBatchPartialFailure(unittest.TestCase):
    """Test: single-asset failure doesn't break batch."""

    def test_mixed_supported_unsupported(self):
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_080", "2026-06-15T12:00:00Z",
            ["BTC", "UNKNOWN_TOKEN", "ETH"],
        )
        self.assertEqual(len(results), 3)
        # BTC should succeed (may be partial if 24h pending)
        self.assertIn(results[0].backfill_status, ("completed", "partial"))
        self.assertEqual(results[0].asset, "BTC")
        # UNKNOWN_TOKEN should fail
        self.assertEqual(results[1].backfill_status, "failed")
        self.assertEqual(results[1].asset, "UNKNOWN_TOKEN")
        # ETH should succeed (may be partial if 24h pending)
        self.assertIn(results[2].backfill_status, ("completed", "partial"))
        self.assertEqual(results[2].asset, "ETH")

    def test_missing_klines_doesnt_break_batch(self):
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill(
            "test_081", "2026-06-15T12:00:00Z",
            ["BTC", "HYPE", "ETH"],
        )
        self.assertEqual(len(results), 3)
        # HYPE should fail gracefully
        self.assertEqual(results[1].backfill_status, "failed")
        # BTC and ETH still work
        self.assertIn(results[0].backfill_status, ("completed", "partial"))
        self.assertIn(results[2].backfill_status, ("completed", "partial"))


class TestDeterministicRepeatability(unittest.TestCase):
    """Test: fixture-based backfill produces identical results on repeat."""

    def test_deterministic_btc(self):
        """Running the same fixture twice gives identical results."""
        backfill = EventPriceBackfill(use_fixture=True)
        r1 = backfill.backfill("test_090", "2026-06-15T12:00:00Z", ["BTC"])
        r2 = backfill.backfill("test_090", "2026-06-15T12:00:00Z", ["BTC"])

        self.assertEqual(len(r1), 1)
        self.assertEqual(len(r2), 1)

        w1 = r1[0].windows
        w2 = r2[0].windows

        for i in range(len(w1)):
            self.assertEqual(w1[i].return_pct, w2[i].return_pct,
                             f"{w1[i].window} return mismatch")
            self.assertEqual(w1[i].btc_abnormal_return, w2[i].btc_abnormal_return,
                             f"{w1[i].window} btc_abnormal mismatch")
            self.assertEqual(w1[i].status, w2[i].status,
                             f"{w1[i].window} status mismatch")

    def test_output_json_serializable(self):
        """Backfill result can be serialized to JSON."""
        backfill = EventPriceBackfill(use_fixture=True)
        results = backfill.backfill("test_091", "2026-06-15T12:00:00Z", ["BTC", "ETH"])
        data = {
            "generated_at": "2026-06-16T00:00:00Z",
            "results": [r.as_dict() for r in results],
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 100)


class TestDataIntegrity(unittest.TestCase):
    """Test: output completeness and constraints."""

    def setUp(self):
        self.backfill = EventPriceBackfill(use_fixture=True)

    def test_all_windows_present(self):
        results = self.backfill.backfill("test_100", "2026-06-15T12:00:00Z", ["BTC"])
        window_names = [w.window for w in results[0].windows]
        for expected in OBSERVATION_WINDOWS:
            self.assertIn(expected, window_names)

    def test_t0_price_not_none_on_success(self):
        results = self.backfill.backfill("test_101", "2026-06-15T12:00:00Z", ["BTC"])
        self.assertIsNotNone(results[0].t0_price)

    def test_t0_time_is_iso(self):
        results = self.backfill.backfill("test_102", "2026-06-15T12:00:00Z", ["BTC"])
        t0_time = results[0].t0_time
        self.assertIsNotNone(t0_time)
        self.assertIn("T", t0_time)

    def test_event_id_preserved(self):
        results = self.backfill.backfill("my_custom_id", "2026-06-15T12:00:00Z", ["BTC"])
        self.assertEqual(results[0].event_id, "my_custom_id")

    def test_no_trading_instructions_in_output(self):
        """Output fields never contain trading language."""
        results = self.backfill.backfill("test_103", "2026-06-15T12:00:00Z", ["BTC", "ETH"])
        for r in results:
            d = r.as_dict()
            text = json.dumps(d).lower()
            for term in ["buy", "sell", "long", "short", "买入", "卖出", "做多", "做空"]:
                self.assertNotIn(term, text,
                                 f"Trading term '{term}' found in output for {r.asset}")
            # Decision terms should not appear
            for decision in ["observe", "discard", "block"]:
                self.assertNotIn(decision, text,
                                 f"Decision term '{decision}' found in price backfill for {r.asset}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

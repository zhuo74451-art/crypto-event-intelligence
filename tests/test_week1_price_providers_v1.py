#!/usr/bin/env python3
"""Week 1 RC — Price Provider Protocol Tests."""

import json
import sys
import unittest
from datetime import datetime, timezone, timedelta

PROJ = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from market_radar.shared.price_provider_protocol import (
    ProviderRouter, BinanceProvider, HyperliquidCandleProvider,
    parse_hl_candle, parse_hl_candles, HLCandle,
    select_nearest_candle, get_hl_candle_fixture,
    Week1ObservationResult, Week1WindowResult,
    run_week1, W1_SAMPLES, W1_WTI, ms_to_iso, iso_to_ms,
)
from market_radar.shared.event_price_backfill import PriceSnapshot

FB = 1779714000000

class TestHLCandleParsing(unittest.TestCase):
    def test_parse_valid(self):
        d = {"t": FB, "T": FB+899999, "s": "HYPE", "i": "15m",
             "o": "12.50", "c": "12.65", "h": "12.80", "l": "12.30", "v": "500000", "n": "125"}
        c = parse_hl_candle(d)
        self.assertIsNotNone(c)
        self.assertEqual(c.open_time_ms, FB)
        self.assertEqual(c.open, 12.50)
        self.assertEqual(c.trade_count, 125)

    def test_missing_t(self):
        self.assertIsNone(parse_hl_candle({"o": "12.50"}))

    def test_missing_o(self):
        self.assertIsNone(parse_hl_candle({"t": FB}))

    def test_bad_price(self):
        self.assertIsNone(parse_hl_candle({"t": FB, "o": "xyz"}))

    def test_not_dict(self):
        self.assertIsNone(parse_hl_candle("abc"))
        self.assertIsNone(parse_hl_candle(None))

    def test_parse_list(self):
        good = {"t": FB, "o": "12.50", "s": "HYPE", "i": "15m"}
        result = parse_hl_candles([good, {"o": "x"}, "bad"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].open, 12.50)

    def test_fixture_parses(self):
        candles = parse_hl_candles(get_hl_candle_fixture())
        self.assertEqual(len(candles), 3)


class TestNearestCandle(unittest.TestCase):
    def setUp(self):
        self.candles = [
            HLCandle(FB, FB+899999, "HYPE", "15m", 12.50, 12.80, 12.30, 12.65, 500000, 125),
            HLCandle(FB+900000, FB+1799999, "HYPE", "15m", 12.65, 12.90, 12.40, 12.75, 450000, 110),
            HLCandle(FB+1800000, FB+2699999, "HYPE", "15m", 12.75, 13.10, 12.60, 12.95, 520000, 135),
        ]

    def test_exact(self):
        c, info = select_nearest_candle(self.candles, FB)
        self.assertIsNotNone(c)
        self.assertEqual(c.open, 12.50)
        self.assertEqual(info["signed_lag_seconds"], 0)

    def test_1302_chooses_1300(self):
        c, info = select_nearest_candle(self.candles, iso_to_ms("2026-05-25T13:02:00Z"))
        self.assertIsNotNone(c)
        self.assertEqual(c.open, 12.50)
        self.assertEqual(info["signed_lag_seconds"], -120)

    def test_450s_accepted(self):
        c, info = select_nearest_candle(self.candles, FB+450000)
        self.assertIsNotNone(c)
        self.assertIsNone(info.get("error_reason"))

    def test_451s_rejected(self):
        # Target 500s before candle 0 -> nearest is 500s away > 450s
        c, info = select_nearest_candle(self.candles, FB-500000)
        self.assertIsNone(c)
        self.assertIn("max_lag_exceeded", info.get("error_reason", ""))

    def test_tie_chooses_earlier(self):
        c, info = select_nearest_candle(self.candles, FB+450000)
        self.assertIsNotNone(c)
        self.assertEqual(c.open, 12.50)

    def test_empty(self):
        c, info = select_nearest_candle([], FB)
        self.assertIsNone(c)

    def test_precision_900(self):
        _, info = select_nearest_candle(self.candles, FB)
        self.assertEqual(info["precision_seconds"], 900)


class TestHLFixture(unittest.TestCase):
    def test_completed(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        snap, info = hp.get_snapshot("HYPE", "2026-05-25T12:59:30Z")
        self.assertEqual(snap.status, "completed")
        self.assertEqual(snap.source, "hyperliquid_fixture")

    def test_1302_completed(self):
        hp = HyperliquidCandleProvider(use_fixture=True)
        snap, info = hp.get_snapshot("HYPE", "2026-05-25T13:02:00Z")
        self.assertEqual(snap.status, "completed")
        self.assertEqual(snap.price, 12.50)
        self.assertEqual(info["signed_lag_seconds"], -120)

    def test_no_network_not_fixture(self):
        hp = HyperliquidCandleProvider(use_fixture=False)
        snap, _ = hp.get_snapshot("HYPE", "2010-01-01T00:00:00Z")
        self.assertEqual(snap.status, "unavailable")
        self.assertNotEqual(snap.source, "hyperliquid_fixture")


class TestBinance(unittest.TestCase):
    def test_name(self):
        self.assertEqual(BinanceProvider().provider_name, "binance")

    def test_unsupported(self):
        snap, _ = BinanceProvider().get_snapshot("UNKNOWN", "2026-05-25T12:00:00Z")
        self.assertEqual(snap.status, "unavailable")

    def test_selection_policy(self):
        self.assertEqual(BinanceProvider().selection_policy, "first_after_target")

    def test_not_fixture(self):
        snap, _ = BinanceProvider().get_snapshot("BTC", "2010-01-01T00:00:00Z")
        self.assertNotEqual(snap.source, "fixture")

    def test_unsupported_symbol(self):
        snap, _ = BinanceProvider().get_snapshot("UNKNOWN", "2026-05-25T12:00:00Z")
        self.assertEqual(snap.status, "unavailable")

if __name__ == "__main__":
    unittest.main(verbosity=2)

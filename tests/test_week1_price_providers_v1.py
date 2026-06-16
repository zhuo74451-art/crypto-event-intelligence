#!/usr/bin/env python3
"""Week 1 RC — Price Provider Protocol Tests."""

import json
import sys
import unittest
from datetime import datetime, timezone

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
             "o": "12.50", "c": "12.65", "h": "12.80", "l": "12.30",
             "v": "500000", "n": "125"}
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

    def test_parse_list_filters_bad(self):
        good = {"t": FB, "o": "12.50", "s": "HYPE", "i": "15m"}
        result = parse_hl_candles([good, {"o": "x"}, "bad"])
        self.assertEqual(len(result), 1)

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


class TestBinance(unittest.TestCase):
    def test_name(self):
        self.assertEqual(BinanceProvider().provider_name, "binance")

    def test_unsupported(self):
        snap, _ = BinanceProvider().get_snapshot("UNKNOWN", "2026-05-25T12:00:00Z")
        self.assertEqual(snap.status, "unavailable")

    def test_not_fixture(self):
        snap, _ = BinanceProvider().get_snapshot("BTC", "2010-01-01T00:00:00Z")
        self.assertNotEqual(snap.source, "fixture")


class TestWeek1Results(unittest.TestCase):
    @unittest.skip("network")
    def setUp(self):
        self.hl = HyperliquidCandleProvider(use_fixture=True)
        self.router = ProviderRouter(hyperliquid_provider=self.hl)
        self.now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)

    def test_all_produced(self):
        results = run_week1(self.router, self.now)
        self.assertEqual(len(results), 6)

    def test_sample_ids(self):
        sids = {r.sample_id for r in run_week1(self.router, self.now)}
        for e in ("w1_001", "w1_002", "w1_003", "w1_004", "w1_005"):
            self.assertIn(e, sids)

    def test_wti_result_ids(self):
        wti = [r for r in run_week1(self.router, self.now) if r.subject_asset == "WTI"]
        self.assertEqual(len(wti), 2)
        self.assertEqual({r.result_id for r in wti}, {"w1_005__BTC", "w1_005__ETH"})

    def test_t0_basis_is_broadcast_time_string(self):
        for r in run_week1(self.router, self.now):
            self.assertEqual(r.t0_basis, "broadcast_time",
                             f"{r.result_id}: t0_basis must be 'broadcast_time'")

    def test_t0_basis_no_date_string(self):
        for r in run_week1(self.router, self.now):
            self.assertNotIn("T", r.t0_basis, f"{r.result_id}: t0_basis contains T")
            self.assertNotIn("Z", r.t0_basis, f"{r.result_id}: t0_basis contains Z")

    def test_broadcast_time_valid_iso(self):
        for r in run_week1(self.router, self.now):
            self.assertTrue(r.broadcast_time_utc.endswith("Z"),
                            f"{r.result_id}: broadcast_time must end with Z")

    def test_hype_signed_lag(self):
        h = next(r for r in run_week1(self.router, self.now) if r.sample_id == "w1_001")
        self.assertEqual(h.signed_lag_seconds, -120)

    def test_completed_window_has_target_snapshot(self):
        for r in run_week1(self.router, self.now):
            for wn in ("1h", "4h", "24h"):
                w = getattr(r, f"return_{wn}")
                if w and w.status == "completed":
                    self.assertIsNotNone(w.target_snapshot,
                        f"{r.result_id}/{wn}: missing target_snapshot")
                    self.assertIsNotNone(w.target_snapshot.price)

    def test_completed_window_has_benchmark_snapshots(self):
        for r in run_week1(self.router, self.now):
            for wn in ("1h", "4h", "24h"):
                w = getattr(r, f"return_{wn}")
                if w and w.status == "completed":
                    self.assertIsNotNone(w.btc_benchmark_t0_snapshot,
                        f"{r.result_id}/{wn}: missing btc_benchmark_t0")
                    self.assertIsNotNone(w.btc_benchmark_target_snapshot,
                        f"{r.result_id}/{wn}: missing btc_benchmark_target")
                    self.assertIsNotNone(w.eth_benchmark_t0_snapshot,
                        f"{r.result_id}/{wn}: missing eth_benchmark_t0")

    def test_no_attribution(self):
        for r in run_week1(self.router, self.now):
            text = json.dumps(r.as_dict()).lower()
            for t in ("attribution", "confidence", "causality", "causal",
                      "buy_signal", "sell_signal", "win_rate", "strategy"):
                self.assertNotIn(t, text, f"'{t}' in {r.result_id}")

    def test_json_serializable(self):
        json.dumps({"results": [r.as_dict() for r in run_week1(self.router, self.now)]},
                   ensure_ascii=False)


class TestZeroValueHandling(unittest.TestCase):
    def test_signed_lag_zero_displays_zero(self):
        wr = Week1WindowResult(window="1h", status="completed", signed_lag_seconds=0)
        self.assertEqual(wr.as_dict()["signed_lag_seconds"], 0)

    def test_abnormal_zero_displays_zero(self):
        wr = Week1WindowResult(window="1h", status="completed",
                               btc_abnormal_return_decimal=0.0,
                               btc_abnormal_return_percent=0.0)
        d = wr.as_dict()
        self.assertEqual(d["btc_abnormal_return_decimal"], 0.0)
        self.assertEqual(d["btc_abnormal_return_percent"], 0.0)

    def test_none_abnormal_self_benchmark(self):
        wr = Week1WindowResult(window="1h", status="completed",
                               btc_abnormal_return_decimal=None,
                               btc_abnormal_return_percent=None)
        d = wr.as_dict()
        self.assertIsNone(d["btc_abnormal_return_decimal"])
        self.assertIsNone(d["btc_abnormal_return_percent"])

    def test_none_signed_lag(self):
        wr = Week1WindowResult(window="1h", status="pending", signed_lag_seconds=None)
        self.assertIsNone(wr.as_dict()["signed_lag_seconds"])


class TestStructures(unittest.TestCase):
    def test_observation_t0_basis(self):
        r = Week1ObservationResult(
            sample_id="w1_001", result_id="w1_001",
            subject_asset="HYPE", observed_asset="HYPE",
            broadcast_time_utc="2026-05-25T13:02:00Z",
            t0_basis="broadcast_time", provider="hyperliquid", interval="15m",
        )
        self.assertEqual(r.t0_basis, "broadcast_time")

    def test_window_roundtrip(self):
        wr = Week1WindowResult(window="1h", status="completed",
                               return_decimal=0.007353, return_percent=0.7353)
        d = wr.as_dict()
        self.assertEqual(d["return_decimal"], 0.007353)
        self.assertEqual(d["return_percent"], 0.7353)

    def test_window_with_snapshot_roundtrip(self):
        snap = PriceSnapshot(symbol="BTCUSDT", price=100.0, status="completed",
                             source="test", requested_time="2026-05-25T12:00:00Z")
        wr = Week1WindowResult(window="1h", status="completed", target_snapshot=snap)
        d = wr.as_dict()
        self.assertEqual(d["target_snapshot"]["price"], 100.0)
        self.assertEqual(d["target_snapshot"]["symbol"], "BTCUSDT")


if __name__ == "__main__":
    unittest.main(verbosity=2)

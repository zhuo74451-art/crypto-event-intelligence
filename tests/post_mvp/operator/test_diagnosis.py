"""Operator Diagnosis tests."""
from __future__ import annotations

import unittest
from market_radar.integration.operator_diagnosis import (
    diagnose_curated_api_unavailable,
    diagnose_normal_empty_feed,
    diagnose_cursor_corrupt,
    diagnose_cursor_rollback,
    diagnose_hyperliquid_unavailable,
    diagnose_ccxt_unavailable,
    diagnose_db_locked,
    diagnose_stop_marker,
    diagnose_schema_mismatch,
    diagnose_report_missing,
    diagnose_parent_child_mismatch,
    diagnose_stale_market_snapshot,
    diagnose_whale_empty_positions,
)


class TestDiagnoses(unittest.TestCase):
    def test_curated_api_unavailable(self):
        d = diagnose_curated_api_unavailable("timeout")
        self.assertEqual(d.code, "CURATED_API_UNAVAILABLE")
        self.assertEqual(d.severity, "error")
        self.assertTrue(d.retry_safe)
        self.assertTrue(d.data_may_be_incomplete)

    def test_normal_empty_feed(self):
        d = diagnose_normal_empty_feed()
        self.assertEqual(d.code, "NORMAL_EMPTY_FEED")
        self.assertEqual(d.severity, "info")
        self.assertTrue(d.retry_safe)

    def test_cursor_corrupt(self):
        d = diagnose_cursor_corrupt()
        self.assertEqual(d.code, "CURSOR_CORRUPT")
        self.assertEqual(d.severity, "warning")

    def test_cursor_rollback(self):
        d = diagnose_cursor_rollback()
        self.assertEqual(d.code, "CURSOR_ROLLBACK")
        self.assertEqual(d.severity, "warning")

    def test_hyperliquid_unavailable(self):
        d = diagnose_hyperliquid_unavailable("rate limited")
        self.assertEqual(d.code, "HYPERLIQUID_UNAVAILABLE")
        self.assertEqual(d.severity, "error")

    def test_ccxt_unavailable(self):
        d = diagnose_ccxt_unavailable("binance", "timeout")
        self.assertEqual(d.code, "CCXT_UNAVAILABLE")
        self.assertEqual(d.severity, "error")

    def test_db_locked(self):
        d = diagnose_db_locked()
        self.assertEqual(d.code, "DB_LOCKED")
        self.assertEqual(d.severity, "error")
        self.assertTrue(d.retry_safe)

    def test_stop_marker(self):
        d = diagnose_stop_marker()
        self.assertEqual(d.code, "STOP_MARKER_SET")
        self.assertEqual(d.severity, "warning")

    def test_schema_mismatch(self):
        d = diagnose_schema_mismatch(2, 1)
        self.assertEqual(d.code, "SCHEMA_MISMATCH")
        self.assertEqual(d.severity, "critical")
        self.assertFalse(d.retry_safe)

    def test_report_missing(self):
        d = diagnose_report_missing("/tmp/report.json")
        self.assertEqual(d.code, "REPORT_MISSING")
        self.assertEqual(d.severity, "error")

    def test_parent_child_mismatch(self):
        d = diagnose_parent_child_mismatch()
        self.assertEqual(d.code, "PARENT_CHILD_MISMATCH")

    def test_stale_market_snapshot(self):
        d = diagnose_stale_market_snapshot("BTC")
        self.assertIn("BTC", d.summary)

    def test_whale_empty_positions(self):
        d = diagnose_whale_empty_positions()
        self.assertEqual(d.code, "WHALE_EMPTY_POSITIONS")
        self.assertEqual(d.severity, "info")

    def test_as_dict_contains_keys(self):
        d = diagnose_db_locked()
        dd = d.as_dict()
        for key in ("code", "severity", "summary", "explanation", "likely_cause",
                    "safe_next_action", "retry_safe", "data_may_be_incomplete"):
            self.assertIn(key, dd)

    def test_severity_valid(self):
        for d in [diagnose_curated_api_unavailable(), diagnose_normal_empty_feed(),
                   diagnose_cursor_corrupt()]:
            self.assertIn(d.severity, ("info", "warning", "error", "critical"))


if __name__ == "__main__":
    unittest.main()

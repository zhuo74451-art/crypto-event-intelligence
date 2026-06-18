"""Portfolio configuration — immutable thresholds, validation, hash.

All deterministic. No network, no random, no clock.
"""

from __future__ import annotations

import unittest
import math

from market_radar.whale_domain.portfolio_config import (
    PortfolioThresholds, DEFAULT_THRESHOLDS,
)


class TestPortfolioThresholds(unittest.TestCase):

    def test_default_creation(self):
        t = PortfolioThresholds()
        self.assertEqual(t.high_gross_exposure_usd, 10_000_000)
        self.assertEqual(t.net_concentration_ratio, 0.8)
        self.assertEqual(t.single_coin_concentration, 0.5)
        self.assertEqual(t.single_address_concentration, 0.7)
        self.assertEqual(t.high_weighted_leverage, 10.0)
        self.assertEqual(t.liq_cluster_2pct, 2.0)
        self.assertEqual(t.liq_cluster_5pct, 5.0)
        self.assertEqual(t.coordination_window_hours, 6.0)
        self.assertEqual(t.rapid_expansion_pct, 20.0)
        self.assertEqual(t.stale_data_hours, 48.0)

    def test_custom_values(self):
        t = PortfolioThresholds(
            high_gross_exposure_usd=5_000_000,
            net_concentration_ratio=0.9,
            coordination_window_hours=12.0,
        )
        self.assertEqual(t.high_gross_exposure_usd, 5_000_000)
        self.assertEqual(t.net_concentration_ratio, 0.9)
        self.assertEqual(t.coordination_window_hours, 12.0)
        # Others remain default
        self.assertEqual(t.liq_cluster_2pct, 2.0)

    def test_frozen_immutable(self):
        t = PortfolioThresholds()
        with self.assertRaises(Exception):
            t.high_gross_exposure_usd = 20_000_000  # type: ignore

    def test_rejects_nan(self):
        with self.assertRaises(ValueError):
            PortfolioThresholds(high_gross_exposure_usd=float("nan"))

    def test_rejects_infinity(self):
        with self.assertRaises(ValueError):
            PortfolioThresholds(high_gross_exposure_usd=float("inf"))

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            PortfolioThresholds(high_gross_exposure_usd=-1000)

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            PortfolioThresholds(rapid_expansion_pct=0.0)

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            PortfolioThresholds(high_gross_exposure_usd="not_a_number")  # type: ignore

    def test_config_hash_deterministic(self):
        h1 = PortfolioThresholds().config_hash
        h2 = PortfolioThresholds().config_hash
        self.assertEqual(h1, h2)
        self.assertTrue(h1.startswith("pcfg:"))

    def test_config_hash_differs_on_change(self):
        h1 = PortfolioThresholds().config_hash
        h2 = PortfolioThresholds(high_gross_exposure_usd=20_000_000).config_hash
        self.assertNotEqual(h1, h2)

    def test_default_singleton(self):
        self.assertIsInstance(DEFAULT_THRESHOLDS, PortfolioThresholds)
        self.assertEqual(DEFAULT_THRESHOLDS.config_hash,
                         PortfolioThresholds().config_hash)

    def test_to_dict(self):
        d = PortfolioThresholds().to_dict()
        self.assertIn("high_gross_exposure_usd", d)
        self.assertEqual(d["high_gross_exposure_usd"], 10_000_000)
        self.assertEqual(len(d), 10)


class TestConfigEdgeCases(unittest.TestCase):

    def test_minimal_valid_values(self):
        t = PortfolioThresholds(
            high_gross_exposure_usd=0.01,
            net_concentration_ratio=0.01,
            single_coin_concentration=0.01,
            single_address_concentration=0.01,
            high_weighted_leverage=0.01,
            liq_cluster_2pct=0.01,
            liq_cluster_5pct=0.01,
            coordination_window_hours=0.01,
            rapid_expansion_pct=0.01,
            stale_data_hours=0.01,
        )
        self.assertAlmostEqual(t.high_gross_exposure_usd, 0.01)

    def test_large_values(self):
        t = PortfolioThresholds(high_gross_exposure_usd=1e12)
        self.assertEqual(t.high_gross_exposure_usd, 1e12)

    def test_float_precision(self):
        t = PortfolioThresholds(liq_cluster_2pct=2.5000001)
        self.assertAlmostEqual(t.liq_cluster_2pct, 2.5000001)

    def test_hash_length(self):
        h = PortfolioThresholds().config_hash
        self.assertEqual(len(h), 21)  # "pcfg:" + 16 hex chars

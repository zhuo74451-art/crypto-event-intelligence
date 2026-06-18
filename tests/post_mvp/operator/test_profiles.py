"""Operator Profile tests — validation, builtins, hashes."""
from __future__ import annotations

import unittest
from market_radar.integration.operator_profiles import (
    get_profile, OperatorProfile, BUILTIN_PROFILES,
)


class TestProfileValidation(unittest.TestCase):
    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            get_profile("nonexistent")

    def test_no_send_false_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="bad", no_send=False)

    def test_max_runs_over_2_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="too_many", max_runs=5)

    def test_max_runs_2_allowed(self):
        p = OperatorProfile(name="ok_two", max_runs=2)
        self.assertEqual(p.max_runs, 2)

    def test_timeout_zero_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="bad", timeout=0)

    def test_timeout_negative_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="bad", timeout=-1)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="")

    def test_live_public_requires_network(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="bad", mode="live-public")

    def test_live_public_with_network_ok(self):
        p = OperatorProfile(name="live_ok", mode="live-public", network_allowed=True)
        self.assertTrue(p.network_allowed)

    def test_invalid_verbosity_rejected(self):
        with self.assertRaises(ValueError):
            OperatorProfile(name="bad", output_verbosity="silent")

    def test_profile_hash_deterministic(self):
        p1 = OperatorProfile(name="h1", mode="fixture")
        p2 = OperatorProfile(name="h2", mode="fixture")
        self.assertEqual(p1.profile_hash(), p2.profile_hash())

    def test_profile_hash_differs_with_config(self):
        p1 = OperatorProfile(name="a", mode="fixture")
        p2 = OperatorProfile(name="b", mode="live-public", network_allowed=True)
        self.assertNotEqual(p1.profile_hash(), p2.profile_hash())


class TestBuiltinProfiles(unittest.TestCase):
    def test_all_profiles_accessible(self):
        for name in BUILTIN_PROFILES:
            p = get_profile(name)
            self.assertEqual(p.name, name)

    def test_fixture_smoke_no_network(self):
        p = get_profile("fixture-smoke")
        self.assertFalse(p.network_allowed)
        self.assertEqual(p.mode, "fixture")
        self.assertTrue(p.no_send)

    def test_live_one_shot_network(self):
        p = get_profile("live-one-shot")
        self.assertTrue(p.network_allowed)
        self.assertEqual(p.mode, "live-public")

    def test_live_shadow_2_max_runs(self):
        p = get_profile("live-shadow-2")
        self.assertEqual(p.max_runs, 2)

    def test_feed_diagnostic_disabled_whale(self):
        p = get_profile("feed-diagnostic")
        self.assertFalse(p.whale_enabled)
        self.assertTrue(p.feed_enabled)

    def test_market_diagnostic_only_markets(self):
        p = get_profile("market-diagnostic")
        self.assertTrue(p.markets_enabled)
        self.assertFalse(p.feed_enabled)
        self.assertFalse(p.whale_enabled)

    def test_whale_diagnostic_only_whale(self):
        p = get_profile("whale-diagnostic")
        self.assertTrue(p.whale_enabled)
        self.assertFalse(p.markets_enabled)

    def test_all_profiles_no_send(self):
        for name in BUILTIN_PROFILES:
            self.assertTrue(BUILTIN_PROFILES[name].no_send, f"{name} has no_send=False")

    def test_all_profiles_max_runs_acceptable(self):
        for name in BUILTIN_PROFILES:
            self.assertLessEqual(BUILTIN_PROFILES[name].max_runs, 2)

    def test_risk_levels_assigned(self):
        for name in BUILTIN_PROFILES:
            self.assertIn(BUILTIN_PROFILES[name].risk_level, ("low", "medium", "high"))

    def test_expected_runtime_positive(self):
        for name in BUILTIN_PROFILES:
            self.assertGreater(BUILTIN_PROFILES[name].expected_max_runtime_seconds, 0)

    def test_profile_hash_present(self):
        for name in BUILTIN_PROFILES:
            h = BUILTIN_PROFILES[name].profile_hash()
            self.assertEqual(len(h), 16)

    def test_eight_profiles(self):
        self.assertGreaterEqual(len(BUILTIN_PROFILES), 7)


if __name__ == "__main__":
    unittest.main()

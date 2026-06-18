"""Alert state tracker tests — state transitions, persistence, thresholds.

All deterministic. No network, no random, no system clock dependency
(uses fixed timestamps where possible).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from market_radar.operations.alert_state import (
    AlertStateTracker, make_alert_key,
    STATE_NEW, STATE_PERSISTENT, STATE_CHANGED, STATE_RESOLVED,
    SIZE_CHANGE_RATIO, LEVERAGE_CHANGE_ABS, COOLDOWN_HOURS,
)


TEST_ADDR = "0x6c8512516ce5669d35113a11ca8b8de322fd84f6"
TEST_COIN = "ETH"
TEST_DIR = "long"


def _make_alert(
    alert_type: str = "high_leverage",
    address: str = TEST_ADDR,
    coin: str = TEST_COIN,
    direction: str = TEST_DIR,
    severity: str = "medium",
    observed: float = 15.0,
    label: str = "Test Whale",
    pnl: float = -5000000.0,
    liq_dist: float = 33.4,
    size: float = 40000.0,
    lev: float = 15.0,
    pos_value: float = 70_000_000.0,
) -> dict:
    return {
        "alert_id": f"w2:test_{alert_type}_{direction}",
        "alert_type": alert_type,
        "severity": severity,
        "coin": coin,
        "label": label,
        "address": address,
        "address_short": address[:10],
        "direction": direction,
        "message": f"Test {alert_type}",
        "observed_value": observed,
        "generated_at_utc": "2026-06-18T12:00:00Z",
        "current": {
            "position_value_usd": pos_value,
            "signed_size": size,
            "leverage": lev,
            "unrealized_pnl_usd": pnl,
        },
        "liquidation_distance_pct": liq_dist,
    }


class TestAlertKey(unittest.TestCase):
    """alert_key stability and composition."""

    def test_same_inputs_same_key(self):
        k1 = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        k2 = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        self.assertEqual(k1, k2)

    def test_different_address_different_key(self):
        k1 = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        k2 = make_alert_key("0xother", "ETH", "long", "high_leverage")
        self.assertNotEqual(k1, k2)

    def test_different_type_different_key(self):
        k1 = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        k2 = make_alert_key(TEST_ADDR, "ETH", "long", "concentrated_exposure")
        self.assertNotEqual(k1, k2)

    def test_key_no_timestamp(self):
        """alert_key must NOT contain timestamp, run_id, price, or PnL."""
        k = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        self.assertFalse(k.endswith("Z"))
        self.assertNotIn("run", k)
        self.assertNotIn("2026", k)
        self.assertTrue(k.startswith("ask:"))

    def test_case_insensitive_address(self):
        k1 = make_alert_key("0xABC", "ETH", "long", "high_leverage")
        k2 = make_alert_key("0xabc", "ETH", "long", "high_leverage")
        self.assertEqual(k1, k2)

    def test_coin_uppercase(self):
        k1 = make_alert_key(TEST_ADDR, "eth", "long", "high_leverage")
        k2 = make_alert_key(TEST_ADDR, "ETH", "long", "high_leverage")
        self.assertEqual(k1, k2)


class TestAlertStateFirstRound(unittest.TestCase):
    """First run → all new."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = AlertStateTracker(self.tmpdir)

    def tearDown(self):
        self.tracker.close()

    def test_first_alert_is_new(self):
        alert = _make_alert()
        state, rec = self.tracker.classify_alert(alert)
        self.assertEqual(state, STATE_NEW)
        self.assertEqual(rec.state, STATE_NEW)

    def test_first_batch_all_new(self):
        alerts = [_make_alert("high_leverage"), _make_alert("concentrated_exposure")]
        result = self.tracker.classify_batch(alerts, set())
        self.assertGreater(len(result["new"]), 0)
        self.assertEqual(len(result["persistent"]), 0)

    def test_first_batch_delivery_candidates(self):
        alerts = [_make_alert("high_leverage")]
        result = self.tracker.classify_batch(alerts, set())
        self.assertGreater(len(result["delivery_candidates"]), 0)

    def test_alert_key_in_output(self):
        alert = _make_alert()
        state, rec = self.tracker.classify_alert(alert)
        self.assertTrue(rec.alert_key.startswith("ask:"))


class TestAlertStateSecondRound(unittest.TestCase):
    """Second run with identical data → persistent."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = AlertStateTracker(self.tmpdir)
        self.alert = _make_alert()
        # First round
        self.tracker.classify_alert(self.alert)

    def tearDown(self):
        self.tracker.close()

    def test_identical_second_round_is_persistent(self):
        state, rec = self.tracker.classify_alert(self.alert)
        self.assertEqual(state, STATE_PERSISTENT)

    def test_identical_second_round_not_delivered(self):
        result = self.tracker.classify_batch([self.alert], set())
        self.assertEqual(len(result["delivery_candidates"]), 0)
        self.assertGreater(len(result["persistent"]), 0)

    def test_small_pnl_change_is_persistent(self):
        alert2 = _make_alert(pnl=-5001000.0)  # $1K change < $5M threshold
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_PERSISTENT)


class TestAlertStateChanged(unittest.TestCase):
    """Significant changes → changed."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = AlertStateTracker(self.tmpdir)
        self.alert = _make_alert(size=40000.0, lev=15.0)
        self.tracker.classify_alert(self.alert)

    def tearDown(self):
        self.tracker.close()

    def test_size_change_10pct_becomes_changed(self):
        alert2 = _make_alert(size=45000.0)  # 12.5% increase > 10%
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_CHANGED)

    def test_small_size_change_persistent(self):
        alert2 = _make_alert(size=40400.0)  # 1% < 10%
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_PERSISTENT)

    def test_leverage_change_2x_becomes_changed(self):
        alert2 = _make_alert(lev=18.0)  # +3x > 2x
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_CHANGED)

    def test_liquidation_distance_change_5pp_becomes_changed(self):
        alert2 = _make_alert(liq_dist=25.0)  # 33.4→25 = 8.4pp > 5pp
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_CHANGED)

    def test_severity_upgrade_changed(self):
        alert2 = _make_alert(severity="high")  # medium→high
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_CHANGED)

    def test_changed_with_improvement_suppressed(self):
        """Changed but severity dropped → suppressed."""
        alert2 = _make_alert(severity="low")  # medium→low
        state, rec = self.tracker.classify_alert(alert2)
        self.assertEqual(state, STATE_CHANGED)
        result = self.tracker.classify_batch([alert2], set())
        self.assertIn(alert2["alert_id"],
                      [a.get("alert_id") for a in result["suppressed"]])

    def test_changed_with_worsening_delivered(self):
        """Changed with severity increase → delivery candidate."""
        alert2 = _make_alert(severity="high")
        result = self.tracker.classify_batch([alert2], set())
        self.assertIn(alert2["alert_id"],
                      [a.get("alert_id") for a in result["delivery_candidates"]])


class TestAlertStateCritical(unittest.TestCase):
    """Critical severity bypasses cooldown."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = AlertStateTracker(self.tmpdir)
        self.alert = _make_alert(alert_type="liquidation_critical", severity="critical")

    def tearDown(self):
        self.tracker.close()

    def test_critical_always_delivered(self):
        self.tracker.classify_alert(self.alert)
        result = self.tracker.classify_batch([self.alert], set())
        self.assertIn(self.alert["alert_id"],
                      [a.get("alert_id") for a in result["delivery_candidates"]])


class TestAlertStateResolved(unittest.TestCase):
    """Alert keys missing from current batch → resolved."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = AlertStateTracker(self.tmpdir)
        self.alert = _make_alert()
        self.tracker.classify_alert(self.alert)

    def tearDown(self):
        self.tracker.close()

    def test_alert_key_not_in_batch_resolved(self):
        result = self.tracker.classify_batch([], {self.alert["alert_id"]})
        self.assertGreater(len(result["resolved"]), 0)

    def test_resolved_not_in_next_delivery(self):
        # First batch with alert
        result1 = self.tracker.classify_batch([self.alert], set())
        # Second batch without it — resolved
        result2 = self.tracker.classify_batch([], {"some_key"})
        result3 = self.tracker.classify_batch([], set())
        self.assertEqual(len(result3["delivery_candidates"]), 0)


class TestAlertStatePersistence(unittest.TestCase):
    """SQLite persistence across tracker instances."""

    def test_state_survives_tracker_restart(self):
        tmpdir = tempfile.mkdtemp()
        alert = _make_alert()

        tracker1 = AlertStateTracker(tmpdir)
        state1, rec1 = tracker1.classify_alert(alert)
        tracker1.close()

        tracker2 = AlertStateTracker(tmpdir)
        state2, rec2 = tracker2.classify_alert(alert)
        tracker2.close()

        self.assertEqual(state1, STATE_NEW)
        self.assertEqual(state2, STATE_PERSISTENT)


class TestCooldown(unittest.TestCase):
    """Cooldown prevents repeated delivery."""

    def test_cooldown_hours_constant(self):
        self.assertEqual(COOLDOWN_HOURS, 4.0)

    def test_fresh_alert_no_cooldown(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        alert = _make_alert()
        state, rec = tracker.classify_alert(alert)
        remaining = tracker.get_cooldown_remaining(rec.alert_key)
        self.assertEqual(remaining, 0.0)
        tracker.close()


class TestCooldownReal(unittest.TestCase):
    def test_cooldown_blocks_delivery(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        alert = _make_alert()
        result1 = tracker.classify_batch([alert], set())
        self.assertGreater(len(result1["delivery_candidates"]), 0)
        # Mark as delivered to start cooldown
        for a in result1["delivery_candidates"]:
            tracker.mark_delivered(a["alert_key"])
        # Second identical round should be suppressed by cooldown
        result2 = tracker.classify_batch([alert], set())
        self.assertEqual(len(result2["delivery_candidates"]), 0)
        self.assertGreater(len(result2["suppressed"]), 0)
        tracker.close()

    def test_delivery_updates_last_delivery_at(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        alert = _make_alert()
        _, rec = tracker.classify_alert(alert)
        self.assertIsNone(rec.last_delivery_at)
        tracker.mark_delivered(rec.alert_key)
        rec2 = tracker._load(rec.alert_key)
        self.assertIsNotNone(rec2.last_delivery_at)
        self.assertEqual(rec2.delivery_count, 1)
        tracker.close()


class TestDirectionFlip(unittest.TestCase):
    def test_direction_flip_resolves_old(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        long_alert = _make_alert(direction="long")
        short_alert = _make_alert(direction="short")
        tracker.classify_alert(long_alert)
        long_key = make_alert_key(TEST_ADDR, TEST_COIN, "long", "high_leverage")
        short_key = make_alert_key(TEST_ADDR, TEST_COIN, "short", "high_leverage")
        self.assertNotEqual(long_key, short_key)
        # classify_batch with empty args reads active keys from SQLite
        # The long key should be active, short batch is new
        result = tracker.classify_batch([short_alert])
        resolved_keys = [r["alert_key"] for r in result["resolved"]]
        self.assertIn(long_key, resolved_keys)
        tracker.close()


class TestLiquidationDistanceJSON(unittest.TestCase):
    def test_liq_distance_in_alert_metrics(self):
        alert = _make_alert(liq_dist=33.4)
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        _, rec = tracker.classify_alert(alert)
        snap = json.loads(rec.snapshot_json)
        self.assertEqual(snap.get("liquidation_distance_pct"), 33.4)
        tracker.close()

    def test_liq_distance_none(self):
        alert = _make_alert(liq_dist=None)
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        _, rec = tracker.classify_alert(alert)
        snap = json.loads(rec.snapshot_json)
        self.assertEqual(snap.get("liquidation_distance_pct"), 0.0)
        tracker.close()


class TestFirstRoundBaseline(unittest.TestCase):
    def test_first_round_establishes_state(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        alert = _make_alert()
        # First round - simulate baseline
        state1, rec1 = tracker.classify_alert(alert)
        self.assertEqual(state1, STATE_NEW)
        # Second round - should be persistent
        state2, _ = tracker.classify_alert(alert)
        self.assertEqual(state2, STATE_PERSISTENT)
        tracker.close()


class TestDeliveryCount(unittest.TestCase):
    def test_delivery_count_increments(self):
        tmpdir = tempfile.mkdtemp()
        tracker = AlertStateTracker(tmpdir)
        alert = _make_alert()
        _, rec = tracker.classify_alert(alert)
        self.assertEqual(rec.delivery_count, 0)
        tracker.mark_delivered(rec.alert_key)
        rec2 = tracker._load(rec.alert_key)
        self.assertEqual(rec2.delivery_count, 1)
        tracker.mark_delivered(rec.alert_key)
        rec3 = tracker._load(rec.alert_key)
        self.assertEqual(rec3.delivery_count, 2)
        tracker.close()

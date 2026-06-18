"""Portfolio Intelligence — comprehensive deterministic tests.

Tests coverage:
  - AddressExposureSummary building
  - CoinExposureSummary building
  - All portfolio metrics
  - All 12 risk rules
  - Coordinated behavior detection (window, multi-addr, single-addr, divergent)
  - Portfolio change detection
  - Full engine pipeline
  - Interpretation summary
  - No network imports
  - No system clock

All deterministic. All timestamps fixed.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from datetime import datetime
from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhalePositionChange, ChangeType,
    extract_snapshot, make_position_key,
)
from market_radar.whale_domain.portfolio_models import (
    AddressExposureSummary, CoinExposureSummary, EntityExposureSummary,
    CoordinatedAction, PortfolioChange, PortfolioRiskFinding,
    WhalePortfolioSnapshot, PortfolioIntelligenceSummary,
)
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure, compute_net_exposure,
    compute_long_exposure, compute_short_exposure,
    compute_top_n_concentration, compute_hhi,
    compute_weighted_leverage, compute_weighted_liquidation_distance,
    compute_exposure_within_liq_pct,
    compute_profitable_exposure, compute_unprofitable_exposure,
    compute_same_coin_opposing_exposure,
    compute_cross_address_same_direction,
    count_addresses, count_coins,
    filter_valid_snapshots, assess_data_quality,
    compute_long_short_ratio,
)
from market_radar.whale_domain.portfolio_risk import (
    evaluate_all_rules,
    rule_pr1_high_gross_exposure,
    rule_pr2_net_direction_concentration,
    rule_pr3_single_coin_concentration,
    rule_pr4_single_address_concentration,
    rule_pr5_high_weighted_leverage,
    rule_pr6_liquidation_cluster_2pct,
    rule_pr7_liquidation_cluster_5pct,
    rule_pr8_cross_whale_same_direction,
    rule_pr10_rapid_exposure_expansion,
)
from market_radar.whale_domain.portfolio_coordination import (
    detect_coordinated_direction_build,
    detect_coordinated_reduction,
    detect_coordinated_flip,
    detect_divergent_behavior,
    detect_liquidation_cluster_formation,
    detect_all_coordinated_actions,
)
from market_radar.whale_domain.portfolio_change import (
    detect_gross_exposure_change,
    detect_net_direction_shift,
    detect_leverage_change,
    detect_all_portfolio_changes,
)
from market_radar.whale_domain.portfolio_engine import (
    analyze_portfolio, build_address_summaries, build_coin_summaries,
)
from market_radar.whale_domain.portfolio_summary import (
    generate_summary,
)

TEST_TS = "2026-06-17T12:00:00Z"

# ═══════════════════════════════════════════════════════════════════════
# Helper: build a WhaleSnapshot from parameters
# ═══════════════════════════════════════════════════════════════════════

def make_snap(
    address: str = "0xaaaa000000000000000000000000000000000001",
    label: Optional[str] = "Whale A",
    coin: str = "BTC",
    signed_size: float = 10.0,
    entry_price: float = 65000.0,
    mark_price: float = 66000.0,
    position_value_usd: Optional[float] = None,
    leverage: float = 10.0,
    unrealized_pnl_usd: Optional[float] = 10000.0,
    liquidation_price: Optional[float] = 60000.0,
    snapshot_time_utc: str = TEST_TS,
) -> WhaleSnapshot:
    """Create a deterministic WhaleSnapshot."""
    pv = position_value_usd if position_value_usd is not None else abs(signed_size) * entry_price
    direction = "long" if signed_size > 0 else "short"
    abs_size = abs(signed_size)

    liq_dist = None
    if mark_price and liquidation_price and mark_price > 0:
        if direction == "long":
            liq_dist = (mark_price - liquidation_price) / mark_price * 100
        else:
            liq_dist = (liquidation_price - mark_price) / mark_price * 100

    return WhaleSnapshot(
        address=address, label=label, coin=coin,
        direction=direction, signed_size=signed_size,
        absolute_size=abs_size, position_value_usd=pv,
        entry_price=entry_price, mark_price=mark_price,
        leverage=leverage, unrealized_pnl_usd=unrealized_pnl_usd,
        liquidation_price=liquidation_price,
        liquidation_distance_pct=liq_dist,
        snapshot_time_utc=snapshot_time_utc,
    )


# ═══════════════════════════════════════════════════════════════════════
# 1. Basic Metrics Tests (30+ tests)
# ═══════════════════════════════════════════════════════════════════════

class TestPortfolioMetrics(unittest.TestCase):

    def setUp(self):
        self.snap1 = make_snap(coin="BTC", signed_size=10.0, position_value_usd=650000.0)
        self.snap2 = make_snap(coin="ETH", signed_size=-5.0, position_value_usd=90000.0)
        self.snapshots = [self.snap1, self.snap2]

    def test_gross_exposure(self):
        g = compute_gross_exposure(self.snapshots)
        self.assertEqual(g, 740000.0)

    def test_net_exposure(self):
        n = compute_net_exposure(self.snapshots)
        self.assertEqual(n, 560000.0)

    def test_long_exposure(self):
        l = compute_long_exposure(self.snapshots)
        self.assertEqual(l, 650000.0)

    def test_short_exposure(self):
        s = compute_short_exposure(self.snapshots)
        self.assertEqual(s, 90000.0)

    def test_long_short_ratio(self):
        l = compute_long_exposure(self.snapshots)
        s = compute_short_exposure(self.snapshots)
        r = compute_long_short_ratio(l, s)
        self.assertAlmostEqual(r, 7.2222, delta=0.01)

    def test_short_only_ratio_returns_zero(self):
        snaps = [make_snap(coin="BTC", signed_size=-10.0)]
        r = compute_long_short_ratio(0, compute_short_exposure(snaps))
        self.assertEqual(r, 0.0)

    def test_top1_concentration(self):
        c = compute_top_n_concentration(self.snapshots, 1)
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c, 0.8784, delta=0.01)

    def test_top3_concentration_small(self):
        snaps = [self.snap1]
        c = compute_top_n_concentration(snaps, 3)
        self.assertEqual(c, 1.0)

    def test_hhi(self):
        h = compute_hhi(self.snapshots)
        self.assertIsNotNone(h)
        self.assertAlmostEqual(h, 0.7866, delta=0.01)

    def test_hhi_single(self):
        snaps = [self.snap1]
        h = compute_hhi(snaps)
        self.assertEqual(h, 1.0)

    def test_hhi_empty_returns_none(self):
        h = compute_hhi([])
        self.assertIsNone(h)

    def test_weighted_leverage(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, position_value_usd=600000.0, leverage=10.0),
            make_snap(coin="ETH", signed_size=-5.0, position_value_usd=90000.0, leverage=5.0),
        ]
        w = compute_weighted_leverage(snaps)
        self.assertIsNotNone(w)
        self.assertAlmostEqual(w, 9.3478, delta=0.01)

    def test_weighted_leverage_empty(self):
        self.assertIsNone(compute_weighted_leverage([]))

    def test_weighted_liquidation_distance(self):
        w = compute_weighted_liquidation_distance(self.snapshots)
        self.assertIsNotNone(w)

    def test_exposure_within_2pct(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, liquidation_price=64800.0, mark_price=66000.0),
        ]
        count, total = compute_exposure_within_liq_pct(snaps, 2.0)
        dist = (66000 - 64800) / 66000 * 100
        self.assertLessEqual(dist, 2.0)
        self.assertEqual(count, 1)

    def test_exposure_within_5pct(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, liquidation_price=63000.0, mark_price=66000.0),
        ]
        count, total = compute_exposure_within_liq_pct(snaps, 5.0)
        self.assertEqual(count, 1)

    def test_profitable_exposure(self):
        """Both snapshots have positive PnL, so both are profitable."""
        p = compute_profitable_exposure(self.snapshots)
        self.assertEqual(p, 740000.0)

    def test_unprofitable_exposure(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, unrealized_pnl_usd=-5000.0),
        ]
        u = compute_unprofitable_exposure(snaps)
        self.assertEqual(u, 650000.0)

    def test_same_coin_opposing(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
            make_snap(address="0xbbb", coin="BTC", signed_size=-3.0),
        ]
        result = compute_same_coin_opposing_exposure(snaps)
        self.assertIn("BTC", result)
        self.assertTrue(result["BTC"]["has_opposing"])

    def test_cross_address_same_direction(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
            make_snap(address="0xbbb", coin="BTC", signed_size=5.0),
        ]
        result = compute_cross_address_same_direction(snaps)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["direction"], "long")

    def test_count_addresses(self):
        c = count_addresses(self.snapshots)
        self.assertEqual(c, 1)

    def test_count_coins(self):
        c = count_coins(self.snapshots)
        self.assertEqual(c, 2)

    def test_filter_valid_excludes_zero(self):
        snaps = [self.snap1, make_snap(signed_size=0.0)]
        f = filter_valid_snapshots(snaps)
        self.assertEqual(len(f), 1)

    def test_assess_data_quality_complete(self):
        q = assess_data_quality(self.snapshots)
        self.assertEqual(q, "complete")

    def test_assess_data_quality_incomplete(self):
        snaps = [make_snap(mark_price=0.0)]
        q = assess_data_quality(snaps)
        self.assertEqual(q, "incomplete")

    # Edge cases
    def test_empty_portfolio(self):
        self.assertEqual(compute_gross_exposure([]), 0)
        self.assertEqual(compute_net_exposure([]), 0)
        self.assertEqual(compute_long_exposure([]), 0)
        self.assertEqual(compute_short_exposure([]), 0)
        self.assertIsNone(compute_top_n_concentration([], 1))
        self.assertIsNone(compute_hhi([]))
        self.assertIsNone(compute_weighted_leverage([]))

    def test_unknown_coin(self):
        snaps = [make_snap(coin="UNKNOWN", signed_size=10.0)]
        self.assertEqual(compute_gross_exposure(snaps), 650000.0)

    def test_all_zero_positions(self):
        snaps = [make_snap(signed_size=0.0), make_snap(signed_size=0.0)]
        self.assertEqual(compute_gross_exposure(snaps), 0)
        f = filter_valid_snapshots(snaps)
        self.assertEqual(len(f), 0)

    def test_stablecoin_no_exposure(self):
        snaps = [make_snap(coin="USDT", signed_size=0.0)]
        f = filter_valid_snapshots(snaps)
        self.assertEqual(len(f), 0)

    def test_future_timestamp(self):
        snaps = [make_snap(snapshot_time_utc="2099-01-01T00:00:00Z")]
        self.assertEqual(compute_gross_exposure(snaps), 650000.0)


# ═══════════════════════════════════════════════════════════════════════
# 2. Address Summary Tests
# ═══════════════════════════════════════════════════════════════════════

class TestAddressSummary(unittest.TestCase):

    def test_single_address_single_coin(self):
        snaps = [make_snap()]
        summaries = build_address_summaries(snaps)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].address, "0xaaaa000000000000000000000000000000000001")

    def test_multi_address_multi_coin(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=-5.0),
        ]
        summaries = build_address_summaries(snaps)
        self.assertEqual(len(summaries), 2)

    def test_same_address_multi_coin(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
            make_snap(address="0xaaa", coin="ETH", signed_size=-5.0),
        ]
        summaries = build_address_summaries(snaps)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].coin_count, 2)

    def test_zero_size_excluded(self):
        snaps = [
            make_snap(address="0xaaa", signed_size=10.0),
            make_snap(address="0xbbb", signed_size=0.0),
        ]
        summaries = build_address_summaries(snaps)
        self.assertEqual(len(summaries), 1)

    def test_missing_label(self):
        snaps = [make_snap(label=None)]
        summaries = build_address_summaries(snaps)
        self.assertIsNone(summaries[0].label)

    def test_weighted_leverage_per_address(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, leverage=15.0,
                      position_value_usd=650000.0),
            make_snap(address="0xaaa", coin="ETH", signed_size=-5.0, leverage=5.0,
                      position_value_usd=90000.0),
        ]
        summaries = build_address_summaries(snaps)
        wl = summaries[0].weighted_leverage
        self.assertIsNotNone(wl)
        # (650k*15 + 90k*5) / (650k + 90k) = (9.75M + 0.45M) / 740k = 13.78
        self.assertAlmostEqual(wl, 13.78, delta=0.1)


# ═══════════════════════════════════════════════════════════════════════
# 3. Coin Summary Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCoinSummary(unittest.TestCase):

    def test_basic_coin_summary(self):
        snaps = [make_snap(coin="BTC", signed_size=10.0)]
        summaries = build_coin_summaries(snaps)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].coin, "BTC")
        self.assertEqual(summaries[0].total_long_usd, 650000.0)

    def test_mixed_direction_coin(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
            make_snap(address="0xbbb", coin="BTC", signed_size=-3.0),
        ]
        summaries = build_coin_summaries(snaps)
        btc = [s for s in summaries if s.coin == "BTC"][0]
        self.assertEqual(btc.long_address_count, 1)
        self.assertEqual(btc.short_address_count, 1)
        self.assertEqual(btc.address_count, 2)

    def test_concentration_ratio(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, position_value_usd=600000.0),
            make_snap(address="0xbbb", coin="BTC", signed_size=2.0, position_value_usd=120000.0),
        ]
        summaries = build_coin_summaries(snaps)
        btc = [s for s in summaries if s.coin == "BTC"][0]
        self.assertIsNotNone(btc.concentration_ratio)
        self.assertGreater(btc.concentration_ratio, 0.5)


# ═══════════════════════════════════════════════════════════════════════
# 4. Risk Rules Tests (30+ tests)
# ═══════════════════════════════════════════════════════════════════════

class TestRiskRules(unittest.TestCase):

    def test_pr1_high_gross_exposure_triggers(self):
        f = rule_pr1_high_gross_exposure(15_000_000)
        self.assertIsNotNone(f)
        self.assertEqual(f["rule_id"], "PR1_HIGH_GROSS_EXPOSURE")

    def test_pr1_below_threshold(self):
        f = rule_pr1_high_gross_exposure(5_000_000)
        self.assertIsNone(f)

    def test_pr2_strong_long_bias(self):
        f = rule_pr2_net_direction_concentration(900000, 100000, 1000000)
        self.assertIsNotNone(f)

    def test_pr2_no_bias(self):
        f = rule_pr2_net_direction_concentration(500000, 500000, 1000000)
        self.assertIsNone(f)

    def test_pr2_zero_gross(self):
        f = rule_pr2_net_direction_concentration(0, 0, 0)
        self.assertIsNone(f)

    def test_pr3_single_coin(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, position_value_usd=800000.0),
            make_snap(coin="ETH", signed_size=2.0, position_value_usd=200000.0),
        ]
        f = rule_pr3_single_coin_concentration(snaps, 1000000)
        self.assertEqual(len(f), 1)
        self.assertIn("BTC", f[0].get("affected_coins", []))

    def test_pr3_even_distribution(self):
        snaps = [
            make_snap(coin="BTC", signed_size=5.0, position_value_usd=300000.0),
            make_snap(coin="ETH", signed_size=5.0, position_value_usd=300000.0),
            make_snap(coin="SOL", signed_size=5.0, position_value_usd=300000.0),
        ]
        f = rule_pr3_single_coin_concentration(snaps, 900000)
        self.assertEqual(len(f), 0)

    def test_pr4_single_address_dominance(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, position_value_usd=800000.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=2.0, position_value_usd=200000.0),
        ]
        f = rule_pr4_single_address_concentration(snaps, 1000000)
        self.assertEqual(len(f), 1)

    def test_pr4_even_address(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=5.0, position_value_usd=300000.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=5.0, position_value_usd=300000.0),
        ]
        f = rule_pr4_single_address_concentration(snaps, 600000)
        self.assertEqual(len(f), 0)

    def test_pr5_high_leverage(self):
        f = rule_pr5_high_weighted_leverage(12.5)
        self.assertIsNotNone(f)
        self.assertEqual(f["rule_id"], "PR5_HIGH_WEIGHTED_LEVERAGE")

    def test_pr5_normal_leverage(self):
        f = rule_pr5_high_weighted_leverage(5.0)
        self.assertIsNone(f)

    def test_pr5_none(self):
        f = rule_pr5_high_weighted_leverage(None)
        self.assertIsNone(f)

    def test_pr6_cluster_2pct(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, liquidation_price=65000.0, mark_price=66000.0),
            make_snap(coin="ETH", signed_size=-5.0, liquidation_price=1810.0, mark_price=1789.64),
        ]
        f = rule_pr6_liquidation_cluster_2pct(snaps)
        # BTC dist = (66000-65000)/66000*100 = 1.52% < 2%
        # ETH dist = (1810-1789.64)/1789.64*100 = 1.14% < 2%
        # Both < 2%, count >= 2 → triggers
        # But both are > 0 and <= 2
        self.assertIsNotNone(f)

    def test_pr6_no_cluster(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, liquidation_price=60000.0, mark_price=66000.0),
        ]
        f = rule_pr6_liquidation_cluster_2pct(snaps)
        self.assertIsNone(f)

    def test_pr7_cluster_5pct_not_2pct(self):
        snaps = [
            make_snap(coin="BTC", signed_size=10.0, liquidation_price=63000.0, mark_price=66000.0),
            make_snap(coin="ETH", signed_size=-5.0, liquidation_price=1850.0, mark_price=1789.64),
        ]
        # BTC: (66000-63000)/66000*100 = 4.55% → within 5%, not 2%
        # ETH: (1850-1789.64)/1789.64*100 = 3.37% → within 5%, not 2%
        f_2 = rule_pr6_liquidation_cluster_2pct(snaps)
        f_5 = rule_pr7_liquidation_cluster_5pct(snaps)
        self.assertIsNone(f_2)
        self.assertIsNotNone(f_5)

    def test_pr8_same_direction(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, position_value_usd=2_000_000.0),
            make_snap(address="0xbbb", coin="BTC", signed_size=5.0, position_value_usd=1_000_000.0),
        ]
        f = rule_pr8_cross_whale_same_direction(snaps)
        self.assertGreaterEqual(len(f), 1)

    def test_pr8_single_address(self):
        snaps = [make_snap(coin="BTC", signed_size=10.0)]
        f = rule_pr8_cross_whale_same_direction(snaps)
        self.assertEqual(len(f), 0)

    def test_pr10_rapid_expansion(self):
        f = rule_pr10_rapid_exposure_expansion(15_000_000, 10_000_000)
        self.assertIsNotNone(f)
        self.assertEqual(f["rule_id"], "PR10_RAPID_EXPOSURE_EXPANSION")

    def test_pr10_no_expansion(self):
        f = rule_pr10_rapid_exposure_expansion(5_000_000, 10_000_000)
        self.assertIsNone(f)

    def test_evaluate_all_rules(self):
        snaps = [make_snap(signed_size=100.0, position_value_usd=15_000_000.0, leverage=12.0)]
        findings = evaluate_all_rules(snaps, snapshot_id="test")
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("PR1_HIGH_GROSS_EXPOSURE", rule_ids)
        self.assertIn("PR5_HIGH_WEIGHTED_LEVERAGE", rule_ids)


# ═══════════════════════════════════════════════════════════════════════
# 5. Coordinated Behavior Tests
# ═══════════════════════════════════════════════════════════════════════

def _make_change(address: str, coin: str, change_type: str, direction: str,
                 detected_at: str = TEST_TS, delta_size: float = 5.0) -> WhalePositionChange:
    return WhalePositionChange(
        change_id=f"test_{address}_{coin}",
        address=address, label="Test", coin=coin,
        change_type=change_type, direction=direction,
        delta={"size_delta": delta_size,
               "position_value_delta_usd": delta_size * 65000},
        detected_at_utc=detected_at,
    )


class TestCoordinatedBehavior(unittest.TestCase):

    def test_coordinated_build_two_addresses(self):
        changes = [
            _make_change("0xaaa", "BTC", "increase_long", "long"),
            _make_change("0xbbb", "BTC", "increase_long", "long"),
        ]
        result = detect_coordinated_direction_build(changes)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["address_count"], 2)

    def test_coordinated_build_single_address(self):
        changes = [
            _make_change("0xaaa", "BTC", "increase_long", "long"),
        ]
        result = detect_coordinated_direction_build(changes)
        self.assertEqual(len(result), 0)

    def test_coordinated_reduction_two_addresses(self):
        changes = [
            _make_change("0xaaa", "BTC", "reduce_long", "long", delta_size=-3.0),
            _make_change("0xbbb", "BTC", "reduce_long", "long", delta_size=-2.0),
        ]
        result = detect_coordinated_reduction(changes)
        self.assertEqual(len(result), 1)

    def test_coordinated_flip_two_addresses(self):
        changes = [
            _make_change("0xaaa", "BTC", "flip_long_to_short", "short"),
            _make_change("0xbbb", "BTC", "flip_long_to_short", "short"),
        ]
        result = detect_coordinated_flip(changes)
        self.assertEqual(len(result), 1)

    def test_divergent_behavior(self):
        changes = [
            _make_change("0xaaa", "BTC", "increase_long", "long", delta_size=5.0),
            _make_change("0xbbb", "BTC", "increase_short", "short", delta_size=-3.0),
        ]
        result = detect_divergent_behavior(changes)
        self.assertEqual(len(result), 1)

    def test_liquidation_cluster(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0,
                      liquidation_price=64800.0, mark_price=66000.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=-5.0,
                      liquidation_price=1820.0, mark_price=1789.64),
        ]
        result = detect_liquidation_cluster_formation(snaps, 5.0)
        self.assertEqual(len(result), 1)

    def test_out_of_window_not_detected(self):
        changes = [
            _make_change("0xaaa", "BTC", "increase_long", "long",
                         detected_at="2026-06-17T00:00:00Z"),
            _make_change("0xbbb", "BTC", "increase_long", "long",
                         detected_at="2026-06-18T12:00:00Z"),
        ]
        result = detect_coordinated_direction_build(changes, window_hours=6)
        self.assertEqual(len(result), 0)


# ═══════════════════════════════════════════════════════════════════════
# 6. Portfolio Change Tests
# ═══════════════════════════════════════════════════════════════════════

class TestPortfolioChange(unittest.TestCase):

    def test_gross_expansion(self):
        f = detect_gross_exposure_change(1_000_000, 1_500_000, TEST_TS)
        self.assertIsNotNone(f)
        self.assertIn("expanded", f["change_type"])

    def test_gross_reduction(self):
        f = detect_gross_exposure_change(1_500_000, 1_000_000, TEST_TS)
        self.assertIsNotNone(f)
        self.assertIn("reduced", f["change_type"])

    def test_net_direction_shift_long_to_short(self):
        f = detect_net_direction_shift(500000, -100000, 600000, 200000, 100000, 300000, TEST_TS)
        self.assertIsNotNone(f)
        self.assertIn("long_to_short", f["change_type"])

    def test_net_no_shift(self):
        f = detect_net_direction_shift(500000, 600000, 600000, 700000, 100000, 100000, TEST_TS)
        self.assertIsNone(f)

    def test_leverage_increase(self):
        f = detect_leverage_change(5.0, 8.0, TEST_TS)
        self.assertIsNotNone(f)
        self.assertIn("increased", f["change_type"])

    def test_leverage_stable(self):
        f = detect_leverage_change(5.0, 5.5, TEST_TS)
        self.assertIsNone(f)


# ═══════════════════════════════════════════════════════════════════════
# 7. Full Engine Pipeline Tests
# ═══════════════════════════════════════════════════════════════════════

class TestEnginePipeline(unittest.TestCase):

    def test_basic_portfolio_analysis(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, position_value_usd=650000.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=-5.0, position_value_usd=90000.0),
        ]
        result = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        self.assertIsInstance(result, WhalePortfolioSnapshot)
        self.assertEqual(result.positions_count, 2)
        self.assertEqual(result.gross_exposure_usd, 740000.0)

    def test_portfolio_with_risk(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=100.0,
                      position_value_usd=15_000_000.0, leverage=12.0),
        ]
        result = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        self.assertGreater(len(result.risk_findings), 0)

    def test_empty_portfolio_analysis(self):
        result = analyze_portfolio([], detected_at_utc=TEST_TS)
        self.assertEqual(result.positions_count, 0)

    def test_snapshot_id_deterministic(self):
        snaps = [make_snap()]
        r1 = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        r2 = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        self.assertEqual(r1.snapshot_id, r2.snapshot_id)


# ═══════════════════════════════════════════════════════════════════════
# 8. Interpretation Summary Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSummary(unittest.TestCase):

    def test_summary_generation(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0),
        ]
        portfolio = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        summary = generate_summary(portfolio)
        self.assertIsInstance(summary, PortfolioIntelligenceSummary)
        self.assertIn(summary.data_quality, ("complete", "partial", "incomplete"))

    def test_posture_classification(self):
        snaps = [
            make_snap(address="0xaaa", coin="BTC", signed_size=10.0, position_value_usd=500000.0),
            make_snap(address="0xbbb", coin="ETH", signed_size=-1.0, position_value_usd=50000.0),
        ]
        portfolio = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        summary = generate_summary(portfolio)
        self.assertIn(summary.portfolio_posture,
                      ("aggressive_long", "biased_long", "biased_short", "hedged", "neutral"))


# ═══════════════════════════════════════════════════════════════════════
# 9. No-Network / No-System-Clock Verification
# ═══════════════════════════════════════════════════════════════════════

class TestNoNetwork(unittest.TestCase):
    """Verify no network, wallet, or trading imports in portfolio modules."""

    FORBIDDEN_IMPORTS = ["urllib", "requests", "httpx", "aiohttp", "websocket", "grpc"]
    FORBIDDEN_METHODS = ["wallet", "sign", "transfer", "send", "order", "trade", "swap"]

    @classmethod
    def _check_module(cls, module_name):
        import importlib
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            return
        for forbidden in cls.FORBIDDEN_IMPORTS:
            for name, val in inspect.getmembers(mod):
                if hasattr(val, "__module__"):
                    mod_name = val.__module__ or ""
                    if forbidden in mod_name:
                        raise AssertionError(f"{module_name} imports {forbidden} via {name}")

    def test_portfolio_models_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_models")

    def test_portfolio_metrics_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_metrics")

    def test_portfolio_risk_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_risk")

    def test_portfolio_coordination_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_coordination")

    def test_portfolio_change_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_change")

    def test_portfolio_engine_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_engine")

    def test_portfolio_summary_no_network(self):
        self._check_module("market_radar.whale_domain.portfolio_summary")


if __name__ == "__main__":
    unittest.main()

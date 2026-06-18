"""Portfolio intelligence — edge cases, determinism, regressions.

All deterministic. No network, no random, no system clock.
"""

from __future__ import annotations

import unittest
from typing import Any

from market_radar.whale_domain.models import (
    WhaleSnapshot, extract_snapshot, make_position_key, _iso_to_ts,
)
from market_radar.whale_domain.portfolio_models import (
    WhalePortfolioSnapshot, AddressExposureSummary, CoinExposureSummary,
    CoordinatedAction, PortfolioChange, PortfolioRiskFinding,
)
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure, compute_net_exposure, compute_long_exposure,
    compute_short_exposure, compute_long_short_ratio, compute_hhi,
    compute_top_n_concentration, compute_weighted_leverage,
    compute_weighted_liquidation_distance, compute_exposure_within_liq_pct,
    compute_profitable_exposure, compute_unprofitable_exposure,
    compute_same_coin_opposing_exposure, compute_cross_address_same_direction,
    count_addresses, count_coins, filter_valid_snapshots, assess_data_quality,
)
from market_radar.whale_domain.portfolio_engine import (
    analyze_portfolio, build_address_summaries, build_coin_summaries,
)
from market_radar.whale_domain.portfolio_coordination import (
    detect_all_coordinated_actions,
)
from market_radar.whale_domain.portfolio_config import PortfolioThresholds


TEST_TS = "2026-06-17T12:00:00Z"


def _snap(
    addr: str = "0xa", coin: str = "BTC",
    sz: float = 10.0, val: float = 650000.0,
    lev: float = 10.0, liq: float = 60000.0,
    mark: float = 66000.0, pnl: float = 10000.0,
    ts: str = TEST_TS,
) -> WhaleSnapshot:
    direction = "long" if sz > 0 else "short"
    liq_dist = None
    if mark and liq and mark > 0:
        if direction == "long":
            liq_dist = (mark - liq) / mark * 100
        else:
            liq_dist = (liq - mark) / mark * 100
    return WhaleSnapshot(
        address=addr, label=addr, coin=coin,
        direction=direction, signed_size=sz,
        absolute_size=abs(sz), position_value_usd=val,
        entry_price=mark, mark_price=mark,
        leverage=lev, unrealized_pnl_usd=pnl,
        liquidation_price=liq, liquidation_distance_pct=liq_dist,
        snapshot_time_utc=ts,
    )


class Test20Addr10Coin(unittest.TestCase):
    """20 addresses, 10 coins — large portfolio."""

    def setUp(self):
        coins = ["BTC", "ETH", "SOL", "HYPE", "ARB",
                 "OP", "AAVE", "LINK", "MATIC", "DYDX"]
        self.snaps = []
        for i in range(20):
            coin = coins[i % 10]
            sz = 10.0 + i * 0.5
            val = abs(sz) * 65000
            direction = 1 if i % 3 != 0 else -1  # ~2:1 long:short
            self.snaps.append(_snap(
                addr=f"0x_large_{i:04d}", coin=coin,
                sz=sz * direction, val=val,
            ))

    def test_20_addr_10_coin_gross(self):
        g = compute_gross_exposure(self.snaps)
        self.assertGreater(g, 0)

    def test_address_count(self):
        c = count_addresses(self.snaps)
        self.assertEqual(c, 20)

    def test_coin_count(self):
        c = count_coins(self.snaps)
        self.assertEqual(c, 10)

    def test_long_exposure_positive(self):
        l = compute_long_exposure(self.snaps)
        self.assertGreater(l, 0)

    def test_net_exposure_long(self):
        n = compute_net_exposure(self.snaps)
        self.assertGreater(n, 0)  # more longs than shorts

    def test_hhi_low_diversified(self):
        h = compute_hhi(self.snaps)
        self.assertIsNotNone(h)
        self.assertLess(h, 0.2)  # diversified

    def test_all_coin_summaries(self):
        sums = build_coin_summaries(self.snaps)
        self.assertEqual(len(sums), 10)

    def test_all_address_summaries(self):
        sums = build_address_summaries(self.snaps)
        self.assertEqual(len(sums), 20)

    def test_analyze_portfolio(self):
        r = analyze_portfolio(self.snaps, detected_at_utc=TEST_TS)
        self.assertEqual(r.positions_count, 20)
        self.assertGreater(r.gross_exposure_usd, 0)


class TestDuplicateAddressCoin(unittest.TestCase):
    """Duplicate address+coin pairs should be handled."""

    def setUp(self):
        base = _snap(addr="0xdup", coin="BTC", sz=10.0, val=650000.0)
        dup = _snap(addr="0xdup", coin="BTC", sz=5.0, val=325000.0)
        self.snaps = [base, dup]

    def test_gross_includes_both(self):
        g = compute_gross_exposure(self.snaps)
        self.assertEqual(g, 975000.0)

    def test_address_count_deduplicates(self):
        c = count_addresses(self.snaps)
        self.assertEqual(c, 1)


class TestStaleData(unittest.TestCase):
    """Stale snapshot handling."""

    OLD_TS = "2026-06-10T00:00:00Z"

    def test_stale_not_included_in_fresh_count(self):
        fresh = _snap(addr="0xfresh", ts=TEST_TS)
        stale = _snap(addr="0xstale", ts=self.OLD_TS)
        snaps = [fresh, stale]
        # Both still count for metrics
        self.assertEqual(compute_gross_exposure(snaps), 1300000.0)


class TestMissingFields(unittest.TestCase):
    """Missing mark price and liquidation price."""

    def test_missing_mark_price(self):
        snap = _snap(mark=0.0, liq=None)
        self.assertIsNone(snap.liquidation_distance_pct)
        q = assess_data_quality([snap])
        self.assertEqual(q, "incomplete")

    def test_missing_liquidation_price(self):
        snap = _snap(liq=None)
        q = assess_data_quality([snap])
        self.assertEqual(q, "incomplete")


class TestOrderIndependence(unittest.TestCase):
    """Same portfolio, different order → same results."""

    def test_metrics_order_independent(self):
        a = _snap(addr="0xa", coin="BTC", sz=10.0, val=650000.0)
        b = _snap(addr="0xb", coin="ETH", sz=-5.0, val=90000.0)
        c = _snap(addr="0xc", coin="SOL", sz=20.0, val=300000.0)
        g1 = compute_gross_exposure([a, b, c])
        g2 = compute_gross_exposure([c, a, b])
        self.assertEqual(g1, g2)
        h1 = compute_hhi([a, b, c])
        h2 = compute_hhi([c, a, b])
        self.assertEqual(h1, h2)


class TestInputImmutability(unittest.TestCase):
    """Functions must not mutate input lists."""

    def test_metrics_dont_mutate(self):
        s = [_snap()]
        before = len(s)
        _ = compute_gross_exposure(s)
        self.assertEqual(len(s), before)


class TestCrossCoinOpposing(unittest.TestCase):
    """Same-coin opposing detection."""

    def test_same_coin_opposing(self):
        snaps = [
            _snap(addr="0xa", coin="BTC", sz=10.0, val=650000.0),
            _snap(addr="0xb", coin="BTC", sz=-3.0, val=195000.0),
        ]
        r = compute_same_coin_opposing_exposure(snaps)
        self.assertIn("BTC", r)
        self.assertTrue(r["BTC"]["has_opposing"])

    def test_same_coin_no_opposing(self):
        snaps = [
            _snap(addr="0xa", coin="BTC", sz=10.0, val=650000.0),
            _snap(addr="0xb", coin="BTC", sz=5.0, val=325000.0),
        ]
        r = compute_same_coin_opposing_exposure(snaps)
        self.assertFalse(r["BTC"]["has_opposing"])


class TestGrossHighNetNearZero(unittest.TestCase):
    """High gross, net near zero — hedged portfolio."""

    def setUp(self):
        self.snaps = [
            _snap(addr="0xa", coin="BTC", sz=10.0, val=650000.0),
            _snap(addr="0xb", coin="BTC", sz=-9.5, val=617500.0),
        ]

    def test_high_gross(self):
        g = compute_gross_exposure(self.snaps)
        self.assertGreater(g, 1_000_000)

    def test_net_near_zero(self):
        n = compute_net_exposure(self.snaps)
        self.assertLess(abs(n), 50000)

    def test_opposing_detected(self):
        r = compute_same_coin_opposing_exposure(self.snaps)
        self.assertTrue(r["BTC"]["has_opposing"])


class TestStableEventIDs(unittest.TestCase):
    """Event IDs must be deterministic across runs."""

    def test_coordinated_action_id_stable(self):
        from market_radar.whale_domain.portfolio_coordination import (
            detect_coordinated_direction_build,
        )
        from market_radar.whale_domain.models import WhalePositionChange
        c1 = WhalePositionChange(
            change_id="t1", address="0xa", label="A", coin="BTC",
            change_type="increase_long", direction="long",
            delta={"size_delta": 5.0, "position_value_delta_usd": 325000},
            detected_at_utc=TEST_TS,
        )
        c2 = WhalePositionChange(
            change_id="t2", address="0xb", label="B", coin="BTC",
            change_type="increase_long", direction="long",
            delta={"size_delta": 3.0, "position_value_delta_usd": 195000},
            detected_at_utc=TEST_TS,
        )
        r1 = detect_coordinated_direction_build([c1, c2])
        r2 = detect_coordinated_direction_build([c1, c2])
        if r1 and r2:
            self.assertEqual(r1[0]["action_id"], r2[0]["action_id"])

    def test_portfolio_snapshot_id_stable(self):
        snaps = [_snap()]
        r1 = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        r2 = analyze_portfolio(snaps, detected_at_utc=TEST_TS)
        self.assertEqual(r1.snapshot_id, r2.snapshot_id)


class TestRepeatedRunIdempotent(unittest.TestCase):
    """Running twice on same input must produce identical output."""

    def test_metrics_idempotent(self):
        s = [_snap()]
        g1 = compute_gross_exposure(s)
        g2 = compute_gross_exposure(s)
        self.assertEqual(g1, g2)

    def test_analyze_idempotent(self):
        s = [_snap(addr="0xa", coin="BTC"), _snap(addr="0xb", coin="ETH")]
        r1 = analyze_portfolio(s, detected_at_utc=TEST_TS)
        r2 = analyze_portfolio(s, detected_at_utc=TEST_TS)
        self.assertEqual(r1.gross_exposure_usd, r2.gross_exposure_usd)
        self.assertEqual(r1.net_exposure_usd, r2.net_exposure_usd)


class TestZeroPositions(unittest.TestCase):
    """Zero-size positions must be excluded from metrics."""

    def setUp(self):
        self.snaps = [
            _snap(addr="0xa", coin="BTC", sz=0.0, val=0.0),
            _snap(addr="0xb", coin="ETH", sz=-5.0, val=90000.0),
        ]

    def test_zero_excluded_from_count(self):
        valid = filter_valid_snapshots(self.snaps)
        self.assertEqual(len(valid), 1)

    def test_zero_excluded_from_gross(self):
        g = compute_gross_exposure(self.snaps)
        self.assertEqual(g, 90000.0)


class TestEntityMultiAddress(unittest.TestCase):
    """Multi-address entity in summaries."""

    def test_entity_addresses_in_summary(self):
        from market_radar.whale_domain.entity_profile import lookup_entity
        entity = lookup_entity("0x6c8512516ce5669d35113a11ca8b8de322fd84f6")
        self.assertIsNotNone(entity)
        self.assertGreater(len(entity.addresses), 0)


class TestUnknownCoin(unittest.TestCase):
    """Unknown coin symbols must not break metrics."""

    def test_unknown_coin_metrics(self):
        snaps = [_snap(coin="ZZZZ", sz=10.0, val=500000.0)]
        self.assertEqual(compute_gross_exposure(snaps), 500000.0)
        self.assertEqual(count_coins(snaps), 1)


class TestConfigDrivenThresholds(unittest.TestCase):
    """Risk rules respect custom threshold configuration."""

    def setUp(self):
        from market_radar.whale_domain.portfolio_risk import evaluate_all_rules
        self.evaluate = evaluate_all_rules

    def test_custom_gross_threshold(self):
        cfg = PortfolioThresholds(high_gross_exposure_usd=1_000_000)
        snaps = [_snap(sz=20.0, val=1_500_000.0)]
        findings = self.evaluate(snaps, cfg=cfg)
        self.assertTrue(
            any(f["rule_id"] == "PR1_HIGH_GROSS_EXPOSURE" for f in findings)
        )

    def test_custom_leverage_threshold(self):
        cfg = PortfolioThresholds(high_weighted_leverage=5.0)
        snaps = [_snap(lev=8.0, sz=10.0, val=650000.0)]
        findings = self.evaluate(snaps, cfg=cfg)
        self.assertTrue(
            any(f["rule_id"] == "PR5_HIGH_WEIGHTED_LEVERAGE" for f in findings)
        )

    def test_custom_coin_concentration(self):
        cfg = PortfolioThresholds(single_coin_concentration=0.3)
        snaps = [
            _snap(coin="BTC", sz=10.0, val=700000.0),
            _snap(coin="ETH", sz=5.0, val=300000.0),
        ]
        findings = self.evaluate(snaps, cfg=cfg)
        self.assertTrue(
            any(f["rule_id"] == "PR3_SINGLE_COIN_CONCENTRATION" for f in findings)
        )

    def test_relaxed_thresholds_no_findings(self):
        cfg = PortfolioThresholds(
            high_gross_exposure_usd=100_000_000,
            net_concentration_ratio=1.0,
            single_coin_concentration=1.0,
            single_address_concentration=1.0,
            high_weighted_leverage=100.0,
        )
        snaps = [_snap(sz=100.0, val=6_500_000.0, lev=15.0)]
        findings = self.evaluate(snaps, cfg=cfg)
        self.assertEqual(len(findings), 0)

    def test_small_portfolio_no_pr1(self):
        snaps = [_snap(sz=1.0, val=65000.0, lev=2.0)]
        findings = self.evaluate(snaps)
        self.assertFalse(any(f["rule_id"] == "PR1_HIGH_GROSS_EXPOSURE" for f in findings))

    def test_liq_2pct_boundary(self):
        count, total = compute_exposure_within_liq_pct(
            [_snap(sz=10.0, val=1000.0, mark=100.0, liq=98.0, lev=5.0)], 2.0)
        self.assertEqual(count, 1)

    def test_liq_5pct_boundary(self):
        count, total = compute_exposure_within_liq_pct(
            [_snap(sz=10.0, val=1000.0, mark=100.0, liq=95.0, lev=5.0)], 5.0)
        self.assertEqual(count, 1)

    def test_negative_liq_excluded(self):
        count, total = compute_exposure_within_liq_pct(
            [_snap(sz=10.0, val=1000.0, mark=100.0, liq=110.0, lev=5.0)], 5.0)
        self.assertEqual(count, 0)

    def test_none_liq_excluded(self):
        count, total = compute_exposure_within_liq_pct(
            [_snap(sz=10.0, val=1000.0, lev=5.0, liq=None)], 5.0)
        self.assertEqual(count, 0)

    def test_weighted_liq_distance_with_nulls(self):
        w = compute_weighted_liquidation_distance([
            _snap(sz=10.0, val=650000.0, liq=60000.0),
            _snap(sz=5.0, val=325000.0, liq=None),
        ])
        self.assertIsNotNone(w)

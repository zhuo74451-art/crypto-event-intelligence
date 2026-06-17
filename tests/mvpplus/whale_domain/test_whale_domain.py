"""Whale Domain — comprehensive deterministic tests.

All tests are pure, no network, no I/O, no random.
Tests cover:
  - all 14 change types
  - liquidation distance formulas (long/short)
  - null/invalid mark/liq
  - stale snapshot detection
  - deterministic IDs
  - exposure aggregation
  - entity profiles
  - watchlist
  - alert candidates
  - no network imports
  - no trading/signing methods
  - property tests for direction/size transitions
"""

from __future__ import annotations

import inspect
import sys
from datetime import datetime
from typing import Any, Optional

import pytest

from market_radar.whale_domain.models import (
    WhalePositionInput, WhaleSnapshot, WhalePositionChange,
    WhaleExposure, WhaleEntityProfile, WhaleAlertCandidate,
    WhaleDomainResult, ChangeType,
    compute_liquidation_distance, make_position_key,
    extract_snapshot, snapshot_to_dict, dict_to_snapshot,
    SIZE_CHANGE_THRESHOLD, LIQ_DISTANCE_CRITICAL,
    LARGE_POSITION_USD, MASSIVE_POSITION_USD,
)
from market_radar.whale_domain.change_detector import (
    detect_change, detect_all_changes, compute_risk_flags,
)
from market_radar.whale_domain.exposure import aggregate_exposure
from market_radar.whale_domain.watchlist import apply_watchlist
from market_radar.whale_domain.entity_profile import (
    lookup_entity, get_entity_summary, KNOWN_ENTITIES,
)
from market_radar.whale_domain.alert_candidate import (
    generate_alert_candidates, ALERT_RULES,
)

TEST_TS = "2026-06-17T00:00:00Z"
TEST_ADDR = "0x" + "a" * 40


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

def make_input(
    coin: str = "BTC",
    signed_size: float = 10.0,
    entry_price: float = 65000.0,
    mark_price: float = 66000.0,
    position_value_usd: float = 650000.0,
    leverage: float = 10.0,
    liquidation_price: Optional[float] = 60000.0,
    unrealized_pnl_usd: Optional[float] = 10000.0,
    snapshot_time_utc: str = TEST_TS,
    address: str = TEST_ADDR,
    label: Optional[str] = "Test Whale",
) -> WhalePositionInput:
    return WhalePositionInput(
        address=address, label=label, coin=coin,
        signed_size=signed_size, entry_price=entry_price,
        mark_price=mark_price, position_value_usd=position_value_usd,
        leverage=leverage, unrealized_pnl_usd=unrealized_pnl_usd,
        liquidation_price=liquidation_price,
        snapshot_time_utc=snapshot_time_utc,
    )


@pytest.fixture
def long_input() -> WhalePositionInput:
    return make_input()


@pytest.fixture
def short_input() -> WhalePositionInput:
    return make_input(signed_size=-10.0, position_value_usd=650000.0)


@pytest.fixture
def long_snapshot(long_input) -> WhaleSnapshot:
    return extract_snapshot(long_input)


@pytest.fixture
def short_snapshot(short_input) -> WhaleSnapshot:
    return extract_snapshot(short_input)


# ═══════════════════════════════════════════════════════════════════════
# 1. Liquidation Distance Formulas
# ═══════════════════════════════════════════════════════════════════════

class TestLiquidationDistance:
    """Verify both formulas per specification.

    Long:  (mark - liq) / mark * 100
    Short: (liq - mark) / mark * 100
    """

    def test_long_normal(self):
        """Long: mark=100, liq=80 → (100-80)/100*100 = 20.0"""
        d = compute_liquidation_distance("long", 100.0, 80.0)
        assert d == pytest.approx(20.0, abs=0.01)

    def test_short_normal(self):
        """Short: mark=100, liq=120 → (120-100)/100*100 = 20.0"""
        d = compute_liquidation_distance("short", 100.0, 120.0)
        assert d == pytest.approx(20.0, abs=0.01)

    def test_long_liq_above_mark_negative(self):
        """Anomalous long with liq above mark: (100-120)/100*100 = -20.0"""
        d = compute_liquidation_distance("long", 100.0, 120.0)
        assert d == pytest.approx(-20.0, abs=0.01)

    def test_null_on_none_liquidation(self):
        assert compute_liquidation_distance("long", 100.0, None) is None
        assert compute_liquidation_distance("short", 100.0, None) is None

    def test_null_on_none_mark(self):
        assert compute_liquidation_distance("long", None, 80.0) is None

    def test_null_on_zero_mark(self):
        assert compute_liquidation_distance("long", 0.0, 80.0) is None
        assert compute_liquidation_distance("short", 0.0, 80.0) is None

    def test_null_on_negative_mark(self):
        assert compute_liquidation_distance("long", -10.0, 80.0) is None

    def test_negative_preserved_not_absd(self):
        """Negative values must NOT be silently abs'd."""
        d = compute_liquidation_distance("short", 100.0, 80.0)
        assert d is not None
        assert d < 0  # Short with liq below mark is anomalous

    def test_critical_threshold(self):
        """Distance <= 5% is critical."""
        d = compute_liquidation_distance("long", 100.0, 96.0)
        assert d is not None
        assert 0 < d <= LIQ_DISTANCE_CRITICAL

    def test_not_critical_when_safe(self):
        """Distance > 5% is not critical."""
        d = compute_liquidation_distance("long", 100.0, 50.0)
        assert d is not None
        assert d > LIQ_DISTANCE_CRITICAL


# ═══════════════════════════════════════════════════════════════════════
# 2. Snapshot Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestSnapshotExtraction:
    def test_long_snapshot(self, long_input):
        snap = extract_snapshot(long_input)
        assert snap.direction == "long"
        assert snap.signed_size == 10.0
        assert snap.absolute_size == 10.0
        assert snap.coin == "BTC"
        assert snap.liquidation_distance_pct is not None

    def test_short_snapshot(self, short_input):
        snap = extract_snapshot(short_input)
        assert snap.direction == "short"
        assert snap.signed_size == -10.0
        assert snap.absolute_size == 10.0

    def test_null_liquidation(self):
        inp = make_input(liquidation_price=None)
        snap = extract_snapshot(inp)
        assert snap.liquidation_price is None
        assert snap.liquidation_distance_pct is None

    def test_snapshot_id_deterministic(self):
        id1 = WhaleSnapshot.compute_id(TEST_ADDR, "BTC", TEST_TS)
        id2 = WhaleSnapshot.compute_id(TEST_ADDR, "BTC", TEST_TS)
        assert id1 == id2
        assert id1.startswith("w2:")

    def test_snapshot_id_different_inputs(self):
        id1 = WhaleSnapshot.compute_id(TEST_ADDR, "BTC", TEST_TS)
        id2 = WhaleSnapshot.compute_id("0x" + "b" * 40, "ETH", TEST_TS)
        assert id1 != id2

    def test_round_trip_dict(self, long_input):
        snap = extract_snapshot(long_input)
        d = snapshot_to_dict(snap)
        snap2 = dict_to_snapshot(d)
        assert snap2.address == snap.address
        assert snap2.coin == snap.coin
        assert snap2.direction == snap.direction
        assert snap2.signed_size == snap.signed_size

    def test_make_position_key(self):
        key = make_position_key("0xABC123", "BTC")
        assert key == "0xabc123:BTC"


# ═══════════════════════════════════════════════════════════════════════
# 3. Change Detection — Baseline Semantics
# ═══════════════════════════════════════════════════════════════════════

class TestChangeDetectionBaseline:
    def test_first_snapshot_long_is_baseline(self, long_snapshot):
        """Existing position on first run must be baseline, not open."""
        ct, direction, prev, curr, delta = detect_change(
            long_snapshot, previous=None, is_baseline_run=True,
        )
        assert ct == ChangeType.BASELINE_OPEN_POSITION
        assert ct != ChangeType.OPEN_LONG

    def test_first_snapshot_short_is_baseline(self, short_snapshot):
        """Existing short on first run must be baseline."""
        ct, direction, prev, curr, delta = detect_change(
            short_snapshot, previous=None, is_baseline_run=True,
        )
        assert ct == ChangeType.BASELINE_OPEN_POSITION
        assert ct != ChangeType.OPEN_SHORT

    def test_no_previous_is_open_long(self, long_snapshot):
        """No previous snapshot on non-first run = open_long."""
        ct, direction, prev, curr, delta = detect_change(
            long_snapshot, previous=None, is_baseline_run=False,
        )
        assert ct == ChangeType.OPEN_LONG

    def test_no_previous_is_open_short(self, short_snapshot):
        ct, direction, prev, curr, delta = detect_change(
            short_snapshot, previous=None, is_baseline_run=False,
        )
        assert ct == ChangeType.OPEN_SHORT

    def test_baseline_zero_position_no_open(self):
        """Zero-size position on baseline must not become baseline_open_position."""
        zero = make_input(signed_size=0.0, position_value_usd=0.0)
        snap = extract_snapshot(zero)
        ct, direction, prev, curr, delta = detect_change(
            snap, previous=None, is_baseline_run=True,
        )
        assert ct == ChangeType.NO_CHANGE


# ═══════════════════════════════════════════════════════════════════════
# 4. Change Detection — Change Types
# ═══════════════════════════════════════════════════════════════════════

class TestChangeDetectionTypes:

    def make_prev(self, signed_size=10.0, **kw) -> WhaleSnapshot:
        # Allow **kw to override defaults, but always set snapshot_time
        params = dict(
            signed_size=signed_size,
            position_value_usd=abs(signed_size) * 65000.0,
            snapshot_time_utc="2026-06-17T00:00:00Z",
        )
        params.update(kw)
        inp = make_input(**params)
        return extract_snapshot(inp)

    def test_increase_long(self, long_snapshot):
        prev = self.make_prev(signed_size=5.0, position_value_usd=325000.0)
        ct, direction, p, c, d = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.INCREASE_LONG

    def test_reduce_long(self, long_snapshot):
        prev = self.make_prev(signed_size=15.0, position_value_usd=975000.0)
        ct, direction, p, c, d = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.REDUCE_LONG

    def test_increase_short(self, short_snapshot):
        prev = self.make_prev(signed_size=-5.0, position_value_usd=325000.0)
        ct, direction, p, c, d = detect_change(
            short_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.INCREASE_SHORT
        assert direction == "short"

    def test_reduce_short(self, short_snapshot):
        prev = self.make_prev(signed_size=-15.0, position_value_usd=975000.0)
        ct, direction, p, c, d = detect_change(
            short_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.REDUCE_SHORT

    def test_close_long(self, long_snapshot):
        closed = make_input(signed_size=0.0001, position_value_usd=6.5)
        snap = extract_snapshot(closed)
        prev = self.make_prev(signed_size=10.0)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.CLOSE_LONG

    def test_close_short(self, short_snapshot):
        closed = make_input(signed_size=-0.0001, position_value_usd=6.5)
        snap = extract_snapshot(closed)
        prev = self.make_prev(signed_size=-10.0)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.CLOSE_SHORT

    def test_close_long_exact_zero(self):
        """signed_size == 0 must use previous direction for long."""
        prev = self.make_prev(signed_size=10.0, position_value_usd=650000.0)
        closed = make_input(signed_size=0.0, position_value_usd=0.0)
        snap = extract_snapshot(closed)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.CLOSE_LONG
        assert direction == "long"

    def test_close_short_exact_zero(self):
        """signed_size == 0 must use previous direction for short."""
        prev = self.make_prev(signed_size=-10.0, position_value_usd=650000.0)
        closed = make_input(signed_size=0.0, position_value_usd=0.0)
        snap = extract_snapshot(closed)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.CLOSE_SHORT
        assert direction == "short"

    def test_flip_long_to_short(self, long_snapshot):
        flipped = make_input(signed_size=-5.0, position_value_usd=325000.0)
        snap = extract_snapshot(flipped)
        prev = self.make_prev(signed_size=10.0)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.FLIP_LONG_TO_SHORT
        assert direction == "short"

    def test_flip_short_to_long(self, short_snapshot):
        flipped = make_input(signed_size=5.0, position_value_usd=325000.0)
        snap = extract_snapshot(flipped)
        prev = self.make_prev(signed_size=-10.0)
        ct, direction, p, c, d = detect_change(
            snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.FLIP_SHORT_TO_LONG
        assert direction == "long"

    def test_liquidation_narrowed(self, long_snapshot):
        """Liq distance narrowed by > 0.5% while size unchanged.

        Prev: liq=58000 → dist=(66000-58000)/66000*100 = 12.12%
        Curr: liq=60000 → dist=(66000-60000)/66000*100 = 9.09%
        Delta = 9.09 - 12.12 = -3.03 < -0.5 → narrowed
        """
        prev = self.make_prev(
            signed_size=10.0, liquidation_price=58000.0,
        )
        ct, direction, p, c, d = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.LIQUIDATION_DISTANCE_NARROWED

    def test_liquidation_widened_is_no_change(self, long_snapshot):
        """Liq distance widened must be no_change, not narrowed.

        Prev: liq=62000 → dist=(66000-62000)/66000*100 = 6.06%
        Curr: liq=60000 → dist=(66000-60000)/66000*100 = 9.09%
        Delta = 9.09 - 6.06 = 3.03 > 0.5 but widened → no_change
        """
        prev = self.make_prev(
            signed_size=10.0, liquidation_price=62000.0,
        )
        ct, direction, p, c, d = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.NO_CHANGE

    def test_liquidation_narrowed_short(self, short_snapshot):
        """Short position liq distance narrowed.

        Prev: liq=120000 → dist=(120000-66000)/66000*100 = 81.82%
        Curr: liq=68000 → dist=(68000-66000)/66000*100 = 3.03%
        Delta = 3.03 - 81.82 = -78.79 < -0.5 → narrowed
        """
        prev = self.make_prev(
            signed_size=-10.0, liquidation_price=120000.0,
            mark_price=66000.0,
        )
        curr_input = make_input(
            signed_size=-10.0, liquidation_price=68000.0,
            mark_price=66000.0,
        )
        curr_snap = extract_snapshot(curr_input)
        ct, direction, p, c, d = detect_change(
            curr_snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.LIQUIDATION_DISTANCE_NARROWED
        assert direction == "short"

    def test_liquidation_widened_short_is_no_change(self, short_snapshot):
        """Short position liq distance widened → no_change."""
        prev = self.make_prev(
            signed_size=-10.0, liquidation_price=68000.0,
            mark_price=66000.0,
        )
        curr_input = make_input(
            signed_size=-10.0, liquidation_price=120000.0,
            mark_price=66000.0,
        )
        curr_snap = extract_snapshot(curr_input)
        ct, direction, p, c, d = detect_change(
            curr_snap, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.NO_CHANGE
        assert direction == "short"

    def test_no_change(self, long_snapshot):
        """Same size and same liq distance → no_change."""
        prev = self.make_prev(
            signed_size=10.0, liquidation_price=60000.0,
        )
        ct, direction, p, c, d = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.NO_CHANGE

    def test_stale_snapshot_rejected(self):
        """Current older than previous → rejected."""
        older = make_input(
            snapshot_time_utc="2026-06-16T00:00:00Z",
            signed_size=10.0,
        )
        older_snap = extract_snapshot(older)
        newer = make_input(
            snapshot_time_utc="2026-06-17T00:00:00Z",
            signed_size=5.0,
        )
        newer_snap = extract_snapshot(newer)
        # Pass older as current, newer as previous
        ct, direction, p, c, d = detect_change(
            older_snap, newer_snap, is_baseline_run=False,
        )
        assert ct == ChangeType.STALE_SNAPSHOT_REJECTED

    def test_deterministic_rerun(self, long_snapshot):
        """Same inputs → same output."""
        prev = self.make_prev(signed_size=5.0)
        ct1, _, _, _, _ = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        ct2, _, _, _, _ = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct1 == ct2

    def test_delta_computation(self, long_snapshot):
        prev = self.make_prev(signed_size=5.0, position_value_usd=325000.0,
                               entry_price=64000.0, unrealized_pnl_usd=5000.0)
        ct, _, _, _, delta = detect_change(
            long_snapshot, prev, is_baseline_run=False,
        )
        assert ct == ChangeType.INCREASE_LONG
        assert delta["size_delta"] == pytest.approx(5.0, abs=0.001)
        assert delta["position_value_delta_usd"] is not None


# ═══════════════════════════════════════════════════════════════════════
# 5. detect_all_changes Integration
# ═══════════════════════════════════════════════════════════════════════

class TestDetectAllChanges:
    def test_baseline_run(self):
        """All existing positions must be baseline_open_position."""
        inputs = [
            make_input(coin="BTC", signed_size=10.0),
            make_input(coin="ETH", signed_size=-5.0),
        ]
        changes = detect_all_changes(
            inputs, previous_snapshots={}, is_baseline_run=True,
            detected_at_utc=TEST_TS,
        )
        assert len(changes) == 2
        for c in changes:
            assert c.change_type == "baseline_open_position"

    def test_baseline_run_skips_zero_positions(self):
        """Zero-size positions on baseline must not generate baseline_open_position."""
        inputs = [
            make_input(coin="BTC", signed_size=10.0),
            make_input(coin="ETH", signed_size=0.0, position_value_usd=0.0),
        ]
        changes = detect_all_changes(
            inputs, previous_snapshots={}, is_baseline_run=True,
            detected_at_utc=TEST_TS,
        )
        assert len(changes) == 1
        assert changes[0].change_type == "baseline_open_position"
        assert changes[0].coin == "BTC"

    def test_detect_disappeared_position(self):
        """Position in previous but not current must be detected as close."""
        prev_snap = extract_snapshot(make_input(coin="BTC", signed_size=10.0))
        prev_state = {make_position_key(TEST_ADDR, "BTC"): prev_snap}
        changes = detect_all_changes(
            [], previous_snapshots=prev_state, is_baseline_run=False,
            detected_at_utc=TEST_TS,
        )
        assert len(changes) == 1
        assert "close" in changes[0].change_type

    def test_change_ids_deterministic(self):
        """Same inputs → same change IDs."""
        inputs = [make_input(coin="BTC", signed_size=10.0)]
        changes1 = detect_all_changes(
            inputs, {}, is_baseline_run=False, detected_at_utc=TEST_TS,
        )
        changes2 = detect_all_changes(
            inputs, {}, is_baseline_run=False, detected_at_utc=TEST_TS,
        )
        for c1, c2 in zip(changes1, changes2):
            assert c1.change_id == c2.change_id

    def test_partial_updates(self):
        """Mixed changes in one run."""
        addr_a = "0x" + "a" * 40
        addr_b = "0x" + "b" * 40
        prev_a = extract_snapshot(make_input(
            address=addr_a, coin="BTC", signed_size=5.0,
            snapshot_time_utc="2026-06-16T00:00:00Z",
        ))
        prev_state = {make_position_key(addr_a, "BTC"): prev_a}

        current = [
            make_input(address=addr_a, coin="BTC", signed_size=10.0),  # increase
            make_input(address=addr_b, coin="ETH", signed_size=-3.0),  # open
        ]
        changes = detect_all_changes(
            current, prev_state, is_baseline_run=False,
            detected_at_utc=TEST_TS,
        )
        types = {c.change_type for c in changes}
        assert ChangeType.INCREASE_LONG.value in types
        assert "open" in types or ChangeType.OPEN_SHORT.value in types


# ═══════════════════════════════════════════════════════════════════════
# 6. Risk Flags
# ═══════════════════════════════════════════════════════════════════════

class TestRiskFlags:
    def test_liquidation_critical(self):
        snap = extract_snapshot(make_input(
            liquidation_price=64000.0,  # distance = (66000-64000)/66000*100 = 3.03%
            mark_price=66000.0, entry_price=65000.0,
            position_value_usd=100000.0,
        ))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        assert any(f["rule_id"] == "R1_LIQ_DISTANCE_CRITICAL" for f in flags)

    def test_not_critical_when_safe(self):
        snap = extract_snapshot(make_input(liquidation_price=50000.0))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        assert not any(f["rule_id"] == "R1_LIQ_DISTANCE_CRITICAL" for f in flags)

    def test_high_leverage(self):
        snap = extract_snapshot(make_input(leverage=15.0))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        assert any(f["rule_id"] == "R2_HIGH_LEVERAGE" for f in flags)

    def test_large_open(self):
        snap = extract_snapshot(make_input(position_value_usd=2_000_000.0))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        assert any(f["rule_id"] == "R3_LARGE_POSITION_OPEN" for f in flags)

    def test_concentrated_asset(self):
        snap = extract_snapshot(make_input(position_value_usd=10_000_000.0))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        assert any(f["rule_id"] == "R6_CONCENTRATED_ASSET" for f in flags)

    def test_baseline_does_not_trigger_R3(self):
        """baseline_open_position must not trigger R3_LARGE_POSITION_OPEN."""
        snap = extract_snapshot(make_input(position_value_usd=2_000_000.0))
        flags = compute_risk_flags(ChangeType.BASELINE_OPEN_POSITION, snap)
        r3 = [f for f in flags if f["rule_id"] == "R3_LARGE_POSITION_OPEN"]
        assert len(r3) == 0

    def test_direction_flip_flag(self):
        snap = extract_snapshot(make_input())
        flags = compute_risk_flags(ChangeType.FLIP_LONG_TO_SHORT, snap)
        assert any(f["rule_id"] == "R5_DIRECTION_FLIP" for f in flags)

    def test_risk_flag_structure(self):
        snap = extract_snapshot(make_input(
            liquidation_price=64000.0, position_value_usd=2_000_000.0,
        ))
        flags = compute_risk_flags(ChangeType.OPEN_LONG, snap)
        for f in flags:
            assert "rule_id" in f
            assert "threshold" in f
            assert "observed_value" in f


# ═══════════════════════════════════════════════════════════════════════
# 7. Exposure Aggregation
# ═══════════════════════════════════════════════════════════════════════

class TestExposure:
    def test_basic_aggregation(self):
        snapshots = [
            extract_snapshot(make_input(
                coin="BTC", signed_size=10.0, position_value_usd=650000.0,
                unrealized_pnl_usd=10000.0,
            )),
            extract_snapshot(make_input(
                coin="ETH", signed_size=-50.0, position_value_usd=90000.0,
                unrealized_pnl_usd=-2000.0,
            )),
        ]
        exp = aggregate_exposure(snapshots, generated_at_utc=TEST_TS)
        assert exp.total_positions == 2
        assert exp.total_long_value_usd == 650000.0
        assert exp.total_short_value_usd == 90000.0
        assert exp.net_exposure_usd == 560000.0
        assert exp.total_unrealized_pnl_usd == 8000.0
        assert exp.unique_addresses == 1
        assert exp.unique_coins == 2

    def test_per_coin_exposure(self):
        snapshots = [
            extract_snapshot(make_input(
                coin="BTC", signed_size=10.0, position_value_usd=650000.0,
            )),
            extract_snapshot(make_input(
                coin="BTC", signed_size=-2.0, position_value_usd=130000.0,
            )),
        ]
        exp = aggregate_exposure(snapshots, generated_at_utc=TEST_TS)
        assert len(exp.per_coin_exposure) == 1
        btc = exp.per_coin_exposure[0]
        assert btc["long_value_usd"] == 650000.0
        assert btc["short_value_usd"] == 130000.0
        assert btc["net_exposure_usd"] == 520000.0

    def test_liquidation_bands(self):
        snapshots = []
        for liq_dist in [2.0, 10.0, 20.0, None]:
            liq_price = 66000.0 * (1 - liq_dist / 100) if liq_dist else None
            inp = make_input(liquidation_price=liq_price)
            snapshots.append(extract_snapshot(inp))
        exp = aggregate_exposure(snapshots, generated_at_utc=TEST_TS)
        bands = exp.liquidation_distance_bands
        assert bands is not None
        assert bands["critical_under_5pct"] == 1
        assert bands["warning_5_15pct"] >= 0
        assert bands["unknown"] == 1

    def test_biggest_positions_ordered(self):
        snapshots = [
            extract_snapshot(make_input(
                position_value_usd=300000.0,
            )),
            extract_snapshot(make_input(
                position_value_usd=500000.0, signed_size=8.0,
            )),
        ]
        exp = aggregate_exposure(snapshots, generated_at_utc=TEST_TS)
        assert exp.biggest_positions[0]["position_value_usd"] == 500000.0

    def test_high_leverage_list(self):
        snapshots = [
            extract_snapshot(make_input(leverage=15.0)),
            extract_snapshot(make_input(leverage=5.0, coin="ETH")),
        ]
        exp = aggregate_exposure(snapshots, generated_at_utc=TEST_TS)
        assert len(exp.high_leverage_positions) >= 1


# ═══════════════════════════════════════════════════════════════════════
# 8. Entity Profiles
# ═══════════════════════════════════════════════════════════════════════

class TestEntityProfile:
    def test_known_entity(self):
        entity = lookup_entity("0x6c8512516ce5669d35113a11ca8b8de322fd84f6")
        assert entity is not None
        assert entity.entity_label == "Matrixport Related"

    def test_unknown_address(self):
        entity = lookup_entity("0x" + "z" * 40)
        assert entity is None

    def test_entity_summary(self):
        snapshots = [
            extract_snapshot(make_input(
                address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
                coin="ETH", signed_size=40000.0,
                position_value_usd=72000000.0,
                unrealized_pnl_usd=-18000000.0,
            )),
            extract_snapshot(make_input(
                coin="BTC", signed_size=1.0,
                position_value_usd=66000.0,
            )),
        ]
        entities, unassociated = get_entity_summary(snapshots)
        assert len(entities) >= 1  # Matrixport
        matrixport = [e for e in entities if "matrixport" in e.entity_id]
        if matrixport:
            assert matrixport[0].total_value_usd == 72000000.0
            assert matrixport[0].total_pnl_usd == -18000000.0
        assert len(unassociated) >= 1  # BTC position

    def test_known_entities_list(self):
        entities = KNOWN_ENTITIES
        assert len(entities) >= 4
        for e in entities:
            assert e.entity_id
            assert e.addresses


# ═══════════════════════════════════════════════════════════════════════
# 9. Watchlist
# ═══════════════════════════════════════════════════════════════════════

class TestWatchlist:
    def test_watchlist_basic(self):
        snapshots = [
            extract_snapshot(make_input(
                address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
                position_value_usd=72000000.0,
            )),
            extract_snapshot(make_input(
                position_value_usd=1000.0,
            )),
        ]
        result = apply_watchlist(
            snapshots, [], generated_at_utc=TEST_TS,
        )
        assert result["total_positions_monitored"] == 2
        assert result["priority_whale_positions"] == 1
        assert result["significant_positions_count"] == 1

    def test_watchlist_custom_filters(self):
        snapshots = [
            extract_snapshot(make_input(
                liquidation_price=64000.0,  # 3.03% from liq
            )),
        ]
        result = apply_watchlist(
            snapshots, [], generated_at_utc=TEST_TS,
            max_liq_distance=5.0,
        )
        assert result["liquidation_watch_count"] == 1


# ═══════════════════════════════════════════════════════════════════════
# 10. Alert Candidates
# ═══════════════════════════════════════════════════════════════════════

class TestAlertCandidates:
    def test_empty_no_alerts(self):
        alerts = generate_alert_candidates([], [], generated_at_utc=TEST_TS)
        assert alerts == []

    def test_direction_flip_alert(self):
        snapshots = [extract_snapshot(make_input())]
        change = WhalePositionChange(
            change_id="test",
            address=TEST_ADDR, label="Test", coin="BTC",
            change_type="flip_long_to_short", direction="short",
            detected_at_utc=TEST_TS,
        )
        alerts = generate_alert_candidates(
            snapshots, [change], generated_at_utc=TEST_TS,
        )
        assert len(alerts) >= 1
        flip = [a for a in alerts if a.alert_type == "direction_flip"]
        assert len(flip) >= 1

    def test_high_leverage_alert(self):
        snapshots = [extract_snapshot(make_input(leverage=15.0))]
        alerts = generate_alert_candidates(
            snapshots, [], generated_at_utc=TEST_TS,
        )
        hl = [a for a in alerts if a.alert_type == "high_leverage"]
        assert len(hl) >= 1

    def test_concentrated_exposure_alert(self):
        snapshots = [extract_snapshot(make_input(
            position_value_usd=MASSIVE_POSITION_USD + 1_000_000,
        ))]
        alerts = generate_alert_candidates(
            snapshots, [], generated_at_utc=TEST_TS,
        )
        ce = [a for a in alerts if a.alert_type == "concentrated_exposure"]
        assert len(ce) >= 1

    def test_no_liquidation_critical_when_safe(self):
        snapshots = [extract_snapshot(make_input(liquidation_price=50000.0))]
        change = WhalePositionChange(
            change_id="test",
            address=TEST_ADDR, label="Test", coin="BTC",
            change_type="open_long", direction="long",
            current={"liquidation_distance_pct": 24.24},
            detected_at_utc=TEST_TS,
        )
        alerts = generate_alert_candidates(
            snapshots, [change], generated_at_utc=TEST_TS,
        )
        lc = [a for a in alerts if a.alert_type == "liquidation_critical"]
        assert len(lc) == 0

    def test_baseline_does_not_trigger_large_new_position(self):
        """baseline_open_position must not generate large_new_position alert."""
        snapshots = [extract_snapshot(make_input(position_value_usd=2_000_000.0))]
        change = WhalePositionChange(
            change_id="test",
            address=TEST_ADDR, label="Test", coin="BTC",
            change_type="baseline_open_position", direction="long",
            current={"position_value_usd": 2_000_000.0},
            detected_at_utc=TEST_TS,
        )
        alerts = generate_alert_candidates(
            snapshots, [change], generated_at_utc=TEST_TS,
        )
        lnp = [a for a in alerts if a.alert_type == "large_new_position"]
        assert len(lnp) == 0

    def test_alert_ids_deterministic(self):
        snapshots = [extract_snapshot(make_input(leverage=15.0))]
        alerts1 = generate_alert_candidates(
            snapshots, [], generated_at_utc=TEST_TS,
        )
        alerts2 = generate_alert_candidates(
            snapshots, [], generated_at_utc=TEST_TS,
        )
        for a1, a2 in zip(alerts1, alerts2):
            assert a1.alert_id == a2.alert_id


# ═══════════════════════════════════════════════════════════════════════
# 11. No-Network Verification
# ═══════════════════════════════════════════════════════════════════════

class TestNoNetwork:
    """Verify no network, trading, or SDK imports in the domain."""

    FORBIDDEN_IMPORTS = [
        "urllib", "requests", "httpx", "aiohttp",
        "websocket", "grpc",
    ]
    FORBIDDEN_METHODS = [
        "wallet", "sign", "transfer", "send", "order",
        "trade", "swap",
    ]

    @pytest.mark.parametrize("module_name", [
        "market_radar.whale_domain.models",
        "market_radar.whale_domain.change_detector",
        "market_radar.whale_domain.exposure",
        "market_radar.whale_domain.watchlist",
        "market_radar.whale_domain.entity_profile",
        "market_radar.whale_domain.alert_candidate",
    ])
    def test_no_forbidden_imports(self, module_name):
        """All domain modules must not import network libraries."""
        import importlib
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            pytest.skip(f"Cannot import {module_name} in test env")

        for forbidden in self.FORBIDDEN_IMPORTS:
            for name, val in inspect.getmembers(mod):
                if hasattr(val, "__module__"):
                    mod_name = val.__module__ or ""
                    if forbidden in mod_name:
                        pytest.fail(
                            f"{module_name} imports {forbidden} via {name}: {mod_name}"
                        )

    def test_no_trading_methods(self):
        """Domain module source must not contain trading/signing strings."""
        import os
        domain_dir = os.path.join(
            os.path.dirname(__file__),
            *[os.pardir] * 2, "market_radar", "whale_domain",
        )
        if not os.path.isdir(domain_dir):
            pytest.skip(f"Domain dir not found: {domain_dir}")
        for fname in os.listdir(domain_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(domain_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
            for method in self.FORBIDDEN_METHODS:
                if method in source:
                    pytest.fail(
                        f"Found forbidden method '{method}' in {fname}"
                    )


# ═══════════════════════════════════════════════════════════════════════
# 12. Property Tests — Direction/Size Transitions
# ═══════════════════════════════════════════════════════════════════════

class TestPropertyTransitions:
    """Property-based tests for direction and size transitions."""

    def test_all_direction_transitions_valid(self):
        """Every valid pair of (prev_direction, curr_direction) must
        produce the correct change type."""
        cases = [
            (10.0, 15.0, ChangeType.INCREASE_LONG),
            (10.0, 5.0, ChangeType.REDUCE_LONG),
            (10.0, 0.0001, ChangeType.CLOSE_LONG),
            (10.0, -5.0, ChangeType.FLIP_LONG_TO_SHORT),
            (-10.0, -15.0, ChangeType.INCREASE_SHORT),
            (-10.0, -5.0, ChangeType.REDUCE_SHORT),
            (-10.0, -0.0001, ChangeType.CLOSE_SHORT),
            (-10.0, 5.0, ChangeType.FLIP_SHORT_TO_LONG),
        ]
        for prev_sz, curr_sz, expected_ct in cases:
            prev_snap = extract_snapshot(make_input(
                signed_size=prev_sz,
                position_value_usd=abs(prev_sz) * 65000.0,
                snapshot_time_utc="2026-06-16T00:00:00Z",
            ))
            curr_snap = extract_snapshot(make_input(
                signed_size=curr_sz,
                position_value_usd=abs(curr_sz) * 65000.0,
                snapshot_time_utc=TEST_TS,
            ))
            ct, direction, p, c, d = detect_change(
                curr_snap, prev_snap, is_baseline_run=False,
            )
            assert ct == expected_ct, (
                f"prev={prev_sz} curr={curr_sz}: expected {expected_ct.value}, "
                f"got {ct.value}"
            )

    def test_no_change_identical_state(self):
        """Identical snapshots must produce no_change."""
        snap = extract_snapshot(make_input())
        ct, _, _, _, _ = detect_change(snap, snap, is_baseline_run=False)
        assert ct == ChangeType.NO_CHANGE


# ═══════════════════════════════════════════════════════════════════════
# 13. WhaleDomainResult
# ═══════════════════════════════════════════════════════════════════════

class TestWhaleDomainResult:
    def test_result_to_dict(self):
        result = WhaleDomainResult(snapshot_time_utc=TEST_TS, is_baseline=True)
        d = result.to_dict()
        assert d["snapshot_time_utc"] == TEST_TS
        assert d["is_baseline"] is True
        assert d["version"] == "v2"
        assert d["changes"] == []
        assert d["exposure"] is None

    def test_result_with_changes(self):
        change = WhalePositionChange(
            change_id="test", address=TEST_ADDR, label="T", coin="BTC",
            change_type="open_long", direction="long",
            detected_at_utc=TEST_TS,
        )
        result = WhaleDomainResult(
            snapshot_time_utc=TEST_TS,
            changes=[change],
        )
        d = result.to_dict()
        assert len(d["changes"]) == 1
        assert d["changes"][0]["change_type"] == "open_long"


# ═══════════════════════════════════════════════════════════════════════
# 14. Serialization Round Trip
# ═══════════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_change_to_dict(self, long_snapshot):
        change = WhalePositionChange(
            change_id="test",
            address=long_snapshot.address,
            label=long_snapshot.label,
            coin=long_snapshot.coin,
            change_type="baseline_open_position",
            direction=long_snapshot.direction,
            previous=None,
            current=snapshot_to_dict(long_snapshot),
            delta={"size_delta": 10.0},
            risk_flags=[],
            detected_at_utc=TEST_TS,
        )
        d = change.to_dict()
        assert d["change_type"] == "baseline_open_position"
        assert d["coin"] == "BTC"
        assert d["delta"]["size_delta"] == 10.0

    def test_exposure_to_dict(self):
        exp = WhaleExposure(total_positions=5, generated_at_utc=TEST_TS)
        d = exp.to_dict()
        assert d["total_positions"] == 5
        assert d["generated_at_utc"] == TEST_TS

    def test_alert_to_dict(self):
        alert = WhaleAlertCandidate(
            alert_id="w2:test", alert_type="high_leverage",
            severity="medium", coin="BTC", label="Test",
            address_short="0xtest", message="Test alert",
            generated_at_utc=TEST_TS,
        )
        d = alert.to_dict()
        assert d["alert_type"] == "high_leverage"
        assert d["severity"] == "medium"

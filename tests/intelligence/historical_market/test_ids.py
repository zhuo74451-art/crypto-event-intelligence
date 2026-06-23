"""Test deterministic ID generation.

Same inputs = same ID; different inputs = different ID; ordering does not change ID.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    make_bar_id,
    make_snapshot_id,
    make_window_id,
    make_label_id,
    make_source_snapshot_id,
)


class TestMakeBarId:
    def test_same_inputs_same_id(self):
        id1 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "binance")
        assert id1 == id2
        assert len(id1) == 24

    def test_different_instrument_different_id(self):
        id1 = make_bar_id("inst_a", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("inst_b", "1h", "2026-06-15T12:00:00Z", "binance")
        assert id1 != id2

    def test_different_interval_different_id(self):
        id1 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("inst1", "5m", "2026-06-15T12:00:00Z", "binance")
        assert id1 != id2

    def test_different_time_different_id(self):
        id1 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("inst1", "1h", "2026-06-16T12:00:00Z", "binance")
        assert id1 != id2

    def test_different_source_different_id(self):
        id1 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("inst1", "1h", "2026-06-15T12:00:00Z", "fred")
        assert id1 != id2

    def test_ordering_does_not_matter(self):
        """Even though bar_id uses ordered params, same tuple should match."""
        id1 = make_bar_id("a", "1h", "2026-06-15T12:00:00Z", "binance")
        id2 = make_bar_id("a", "1h", "2026-06-15T12:00:00Z", "binance")
        assert id1 == id2

    def test_id_length(self):
        bar_id = make_bar_id("x", "x", "x", "x")
        assert len(bar_id) == 24
        assert isinstance(bar_id, str)


class TestMakeSnapshotId:
    def test_same_inputs_same_id(self):
        id1 = make_snapshot_id("inst1", "2026-06-15T12:00:00Z", "binance")
        id2 = make_snapshot_id("inst1", "2026-06-15T12:00:00Z", "binance")
        assert id1 == id2

    def test_different_time_different_id(self):
        id1 = make_snapshot_id("inst1", "2026-06-15T12:00:00Z", "binance")
        id2 = make_snapshot_id("inst1", "2026-06-16T12:00:00Z", "binance")
        assert id1 != id2


class TestMakeWindowId:
    def test_same_inputs_same_id(self):
        id1 = make_window_id("evt1", "inst1", "2026-06-15T12:00:00Z", "5m")
        id2 = make_window_id("evt1", "inst1", "2026-06-15T12:00:00Z", "5m")
        assert id1 == id2

    def test_different_event_different_id(self):
        id1 = make_window_id("evt_a", "inst1", "2026-06-15T12:00:00Z", "5m")
        id2 = make_window_id("evt_b", "inst1", "2026-06-15T12:00:00Z", "5m")
        assert id1 != id2

    def test_different_version_different_id(self):
        id1 = make_window_id("evt1", "inst1", "2026-06-15T12:00:00Z", "5m", window_version="1.0.0")
        id2 = make_window_id("evt1", "inst1", "2026-06-15T12:00:00Z", "5m", window_version="2.0.0")
        assert id1 != id2


class TestMakeLabelId:
    def test_same_inputs_same_id(self):
        id1 = make_label_id("evt1", "inst1", "2026-06-15T12:00:00Z")
        id2 = make_label_id("evt1", "inst1", "2026-06-15T12:00:00Z")
        assert id1 == id2

    def test_different_version_different_id(self):
        id1 = make_label_id("evt1", "inst1", "2026-06-15T12:00:00Z", calculation_version="1.0.0")
        id2 = make_label_id("evt1", "inst1", "2026-06-15T12:00:00Z", calculation_version="2.0.0")
        assert id1 != id2


class TestMakeSourceSnapshotId:
    def test_same_inputs_same_id(self):
        id1 = make_source_snapshot_id("binance", "https://example.com/data", "2026-06-15T12:00:00Z")
        id2 = make_source_snapshot_id("binance", "https://example.com/data", "2026-06-15T12:00:00Z")
        assert id1 == id2

    def test_different_url_different_id(self):
        id1 = make_source_snapshot_id("binance", "https://url1.com", "2026-06-15T12:00:00Z")
        id2 = make_source_snapshot_id("binance", "https://url2.com", "2026-06-15T12:00:00Z")
        assert id1 != id2

    def test_no_randomness(self):
        """Multiple calls with same args should always yield same ID."""
        ids = [
            make_source_snapshot_id("provider", "url", "2026-06-15T12:00:00Z")
            for _ in range(10)
        ]
        assert all(i == ids[0] for i in ids)

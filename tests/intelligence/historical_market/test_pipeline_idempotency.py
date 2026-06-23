"""Test that running the pipeline twice produces no duplicate records.

This test validates ID determinism: if the same data is processed twice,
the resulting IDs will be identical, so downstream deduplication can
rely on the ID as a natural primary key.
"""

import sys
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    make_bar_id,
    make_snapshot_id,
    make_window_id,
    make_label_id,
    make_source_snapshot_id,
)


class TestBarIdIdempotency:
    def test_same_bar_twice_same_id(self):
        """Building the same bar twice yields the same bar_id."""
        def build():
            return MarketBarV1(
                instrument_id="binance_spot_btcusdt",
                interval="1h",
                open_time_utc="2026-06-15T12:00:00Z",
                close_time_utc="2026-06-15T13:00:00Z",
                open=68000.0,
                high=68100.0,
                low=67900.0,
                close=68050.0,
                volume=100.0,
                source_provider="binance_public_archive",
            )
        bar1 = build()
        bar2 = build()
        # Assign IDs externally (same as the provider would do)
        bar1.bar_id = make_bar_id(
            bar1.instrument_id, bar1.interval, bar1.open_time_utc, bar1.source_provider
        )
        bar2.bar_id = make_bar_id(
            bar2.instrument_id, bar2.interval, bar2.open_time_utc, bar2.source_provider
        )
        assert bar1.bar_id == bar2.bar_id

    def test_to_json_identical(self):
        """Two bars with same data produce identical JSON."""
        def make():
            bar = MarketBarV1(
                instrument_id="binance_spot_ethusdt",
                interval="5m",
                open_time_utc="2026-06-15T12:00:00Z",
                close_time_utc="2026-06-15T12:05:00Z",
                open=3500.0,
                high=3510.0,
                low=3490.0,
                close=3505.0,
                volume=500.0,
                source_provider="binance_public_archive",
            )
            bar.bar_id = make_bar_id(
                bar.instrument_id, bar.interval, bar.open_time_utc, bar.source_provider
            )
            return bar

        j1 = json.dumps(make().to_json(), sort_keys=True)
        j2 = json.dumps(make().to_json(), sort_keys=True)
        assert j1 == j2

    def test_idempotent_serialization_round_trip(self):
        """Serializing and deserializing preserves the bar_id."""
        bar = MarketBarV1(
            instrument_id="test_inst",
            interval="1h",
            open_time_utc="2026-06-15T12:00:00Z",
            source_provider="test_provider",
        )
        bar.bar_id = make_bar_id(
            bar.instrument_id, bar.interval, bar.open_time_utc, bar.source_provider
        )
        original_id = bar.bar_id
        restored = MarketBarV1.from_json(bar.to_json())
        assert restored.bar_id == original_id


class TestNoDuplicateIds:
    def test_different_bars_different_ids(self):
        """Different bars should never collide."""
        id1 = make_bar_id("inst_a", "1h", "2026-06-15T12:00:00Z", "src1")
        id2 = make_bar_id("inst_b", "1h", "2026-06-15T12:00:00Z", "src1")
        id3 = make_bar_id("inst_a", "5m", "2026-06-15T12:00:00Z", "src1")
        id4 = make_bar_id("inst_a", "1h", "2026-06-16T12:00:00Z", "src1")
        id5 = make_bar_id("inst_a", "1h", "2026-06-15T12:00:00Z", "src2")
        ids = {id1, id2, id3, id4, id5}
        assert len(ids) == 5

    def test_source_snapshot_id_idempotent(self):
        id1 = make_source_snapshot_id("binance", "url", "2026-06-15T12:00:00Z")
        id2 = make_source_snapshot_id("binance", "url", "2026-06-15T12:00:00Z")
        assert id1 == id2

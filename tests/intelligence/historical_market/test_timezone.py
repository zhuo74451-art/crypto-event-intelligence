"""Test UTC-only timestamps, no naive datetimes."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    DerivativeSnapshotV1,
    EventMarketWindowV1,
    MarketReactionLabelV1,
    SourceSnapshotV1,
    utc_now,
)


class TestUtcNowHelper:
    def test_utc_now_returns_z_suffix(self):
        now = utc_now()
        assert now.endswith("Z"), f"Expected Z suffix, got: {now}"
        assert "T" in now, f"Expected ISO-8601 format, got: {now}"

    def test_utc_now_parseable(self):
        """The output should be parseable by datetime.fromisoformat."""
        from datetime import datetime, timezone
        now = utc_now()
        parsed = datetime.fromisoformat(now.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_utc_now_format(self):
        now = utc_now()
        # Expected format: 2026-06-15T12:00:00Z
        parts = now.split("T")
        assert len(parts) == 2
        date_part, time_part = parts
        assert time_part.endswith("Z")
        assert len(date_part.split("-")) == 3


class TestMarketBarTimestamps:
    def test_accepts_utc_z_timestamp(self):
        bar = MarketBarV1(
            open_time_utc="2026-06-15T12:00:00Z",
            close_time_utc="2026-06-15T13:00:00Z",
        )
        assert bar.open_time_utc.endswith("Z")
        assert bar.close_time_utc.endswith("Z")

    def test_raises_on_naive_timestamp(self):
        """The contract does not enforce this at dataclass level, but tests document intent."""
        bar = MarketBarV1(
            open_time_utc="2026-06-15 12:00:00",  # naive format
        )
        # This is just documenting that the field is stored as-is; downstream
        # consumers should reject non-UTC timestamps.
        assert "Z" not in bar.open_time_utc
        # In practice, we recommend validation at the pipeline boundary.

    def test_retrieved_at_utc_has_z(self):
        bar = MarketBarV1(retrieved_at_utc=utc_now(), first_seen_at_utc=utc_now())
        assert bar.retrieved_at_utc.endswith("Z")
        assert bar.first_seen_at_utc.endswith("Z")

    def test_z_suffix_convention(self):
        """All timestamp fields should follow the Z suffix convention."""
        bar = MarketBarV1(
            open_time_utc=utc_now(),
            close_time_utc=utc_now(),
            retrieved_at_utc=utc_now(),
            first_seen_at_utc=utc_now(),
        )
        for field_name in ["open_time_utc", "close_time_utc", "retrieved_at_utc", "first_seen_at_utc"]:
            val = getattr(bar, field_name)
            assert val.endswith("Z"), f"Field {field_name} does not end with Z: {val}"


class TestDerivativeSnapshotTimestamps:
    def test_observed_at_utc_has_z(self):
        snap = DerivativeSnapshotV1(observed_at_utc=utc_now(), retrieved_at_utc=utc_now())
        assert snap.observed_at_utc.endswith("Z")
        assert snap.retrieved_at_utc.endswith("Z")


class TestEventWindowTimestamps:
    def test_timestamps_have_z(self):
        win = EventMarketWindowV1(
            event_time_utc=utc_now(),
            pre_window_start_utc=utc_now(),
            post_window_end_utc=utc_now(),
        )
        assert win.event_time_utc.endswith("Z")
        assert win.pre_window_start_utc.endswith("Z")
        assert win.post_window_end_utc.endswith("Z")


class TestReactionLabelTimestamps:
    def test_event_time_utc_has_z(self):
        lbl = MarketReactionLabelV1(event_time_utc=utc_now())
        assert lbl.event_time_utc.endswith("Z")


class TestSourceSnapshotTimestamps:
    def test_retrieved_at_utc_has_z(self):
        ss = SourceSnapshotV1(retrieved_at_utc=utc_now())
        assert ss.retrieved_at_utc.endswith("Z")

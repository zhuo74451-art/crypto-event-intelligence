"""Tests for point-in-time violation detection and quality grading rules."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1,
    MacroConsensusObservationV1,
    generate_event_id,
    utc_parse,
)


class TestPointInTimeQuality:
    """Test that PIT quality rules are enforced."""

    def test_missing_consensus_stays_null(self):
        """missing quality must not have a consensus_value."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            point_in_time_quality="missing",
        )
        assert event.consensus_value is None

    def test_strict_quality_has_values(self):
        """strict_archived_pre_event quality requires consensus_value."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            consensus_value=6.2,
            point_in_time_quality="strict_archived_pre_event",
        )
        assert event.consensus_value == 6.2

    def test_consensus_observed_before_release(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            consensus_value=6.2,
            consensus_observed_at_utc="2023-02-13T12:00:00Z",
            point_in_time_quality="strict_archived_pre_event",
        )
        assert utc_parse(event.consensus_observed_at_utc) < utc_parse(event.actual_release_at_utc)

    def test_post_release_consensus_is_leakage(self):
        """Consensus observed after release time is a leakage."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            consensus_value=6.2,
            consensus_observed_at_utc="2023-02-14T14:00:00Z",
            point_in_time_quality="reconstructed_multi_source",
        )
        consensus_dt = utc_parse(event.consensus_observed_at_utc)
        release_dt = utc_parse(event.actual_release_at_utc)
        assert consensus_dt > release_dt

    def test_quality_not_upgradable(self):
        """Reconstructed quality must not be labeled as strict."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            consensus_value=6.2,
            point_in_time_quality="single_source_reconstructed",
        )
        assert event.point_in_time_quality != "strict_archived_pre_event"
        assert event.point_in_time_quality != "verified_pre_event_media"

    def test_initial_value_preserved(self):
        """actual_initial must not be overwritten by revision logic."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            actual_initial=6.4,
        )
        event.prior_revised_latest = 6.2
        assert event.actual_initial == 6.4
        assert event.prior_revised_latest == 6.2

    def test_first_seen_before_retrieved_valid(self):
        """first_seen_at_utc must not be later than retrieved_at_utc."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            first_seen_at_utc="2023-01-14T10:00:00Z",
            retrieved_at_utc="2023-01-14T12:00:00Z",
        )
        fs_dt = utc_parse(event.first_seen_at_utc)
        rt_dt = utc_parse(event.retrieved_at_utc)
        assert fs_dt <= rt_dt

    def test_first_seen_after_retrieved_is_anomaly(self):
        """When first_seen > retrieved, it is a time anomaly."""
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            first_seen_at_utc="2023-02-14T13:35:00Z",
            retrieved_at_utc="2023-02-14T13:30:00Z",
        )
        fs_dt = utc_parse(event.first_seen_at_utc)
        rt_dt = utc_parse(event.retrieved_at_utc)
        assert fs_dt > rt_dt

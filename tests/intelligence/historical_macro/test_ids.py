"""Tests for deterministic ID generation rules."""
import hashlib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    generate_event_id,
    generate_consensus_observation_id,
    generate_revision_id,
    generate_snapshot_id,
)


class TestEventID:
    def test_same_input_same_id(self):
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        assert id1 == id2

    def test_input_order_independence(self):
        # Same payload in different order is caught by the function signature
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("us", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        # Country normalization: US vs us -> both become US
        assert id1 == id2

    def test_different_release_time_different_id(self):
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-15T13:30:00Z")
        assert id1 != id2

    def test_different_period_different_id(self):
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("US", "us_cpi", "2023-02", "2023-03-14T13:30:00Z")
        assert id1 != id2

    def test_different_family_different_id(self):
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("US", "us_core_cpi", "2023-01", "2023-02-14T13:30:00Z")
        assert id1 != id2

    def test_output_is_24_hex_chars(self):
        eid = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        assert len(eid) == 24
        assert all(c in "0123456789abcdef" for c in eid)

    def test_country_case_insensitive(self):
        id1 = generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        id2 = generate_event_id("us", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")
        assert id1 == id2


class TestConsensusObservationID:
    def test_same_input_same_id(self):
        id1 = generate_consensus_observation_id("abc123", "ForexFactory", "2023-02-13T12:00:00Z", 6.2)
        id2 = generate_consensus_observation_id("abc123", "ForexFactory", "2023-02-13T12:00:00Z", 6.2)
        assert id1 == id2

    def test_different_value_different_id(self):
        id1 = generate_consensus_observation_id("abc123", "ForexFactory", "2023-02-13T12:00:00Z", 6.2)
        id2 = generate_consensus_observation_id("abc123", "ForexFactory", "2023-02-13T12:00:00Z", 6.3)
        assert id1 != id2

    def test_different_source_different_id(self):
        id1 = generate_consensus_observation_id("abc123", "ForexFactory", "2023-02-13T12:00:00Z", 6.2)
        id2 = generate_consensus_observation_id("abc123", "Bloomberg", "2023-02-13T12:00:00Z", 6.2)
        assert id1 != id2


class TestRevisionID:
    def test_same_input_same_id(self):
        id1 = generate_revision_id("abc123", "2023-03-14T13:30:00Z", 6.4, 6.3)
        id2 = generate_revision_id("abc123", "2023-03-14T13:30:00Z", 6.4, 6.3)
        assert id1 == id2

    def test_different_values_different_id(self):
        id1 = generate_revision_id("abc123", "2023-03-14T13:30:00Z", 6.4, 6.3)
        id2 = generate_revision_id("abc123", "2023-03-14T13:30:00Z", 6.5, 6.3)
        assert id1 != id2


class TestSnapshotID:
    def test_same_input_same_id(self):
        id1 = generate_snapshot_id("bls", "https://www.bls.gov/cpi", "2025-01-01T00:00:00Z")
        id2 = generate_snapshot_id("bls", "https://www.bls.gov/cpi", "2025-01-01T00:00:00Z")
        assert id1 == id2

    def test_different_provider_different_id(self):
        id1 = generate_snapshot_id("bls", "https://www.bls.gov/cpi", "2025-01-01T00:00:00Z")
        id2 = generate_snapshot_id("fred", "https://www.bls.gov/cpi", "2025-01-01T00:00:00Z")
        assert id1 != id2

    def test_different_time_different_id(self):
        id1 = generate_snapshot_id("bls", "https://www.bls.gov/cpi", "2025-01-01T00:00:00Z")
        id2 = generate_snapshot_id("bls", "https://www.bls.gov/cpi", "2025-01-02T00:00:00Z")
        assert id1 != id2

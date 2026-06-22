"""Tests for macro evidence contracts: serialization, validation, and default behavior."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1,
    MacroConsensusObservationV1,
    MacroRevisionRecordV1,
    MacroSourceSnapshotV1,
    EventFamily,
    PointInTimeQuality,
    RevisionStatus,
    generate_event_id,
    utc_now,
)


class TestMacroReleaseEventV1:
    def test_default_creation(self):
        event = MacroReleaseEventV1()
        assert event.country == "US"
        assert event.currency == "USD"
        assert event.point_in_time_quality == "missing"
        assert event.revision_status == "initial"

    def test_event_id_generation(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
        )
        assert len(event.event_id) == 24
        assert all(c in "0123456789abcdef" for c in event.event_id)

    def test_deterministic_id(self):
        e1 = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            country="US",
        )
        e2 = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            country="US",
        )
        assert e1.event_id == e2.event_id

    def test_different_period_different_id(self):
        e1 = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
        )
        e2 = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-02",
            actual_release_at_utc="2023-03-14T13:30:00Z",
        )
        assert e1.event_id != e2.event_id

    def test_different_family_different_id(self):
        e1 = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
        )
        e2 = MacroReleaseEventV1(
            event_family="us_nonfarm_payrolls",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-03T13:30:00Z",
        )
        assert e1.event_id != e2.event_id

    def test_surprise_computation(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            actual_initial=6.4,
            consensus_value=6.2,
        )
        import pytest; assert event.surprise_raw == pytest.approx(0.2)

    def test_missing_consensus_null_surprise(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            actual_initial=6.4,
            consensus_value=None,
        )
        assert event.surprise_raw is None

    def test_to_dict_roundtrip(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            actual_initial=6.4,
        )
        d = event.to_dict()
        assert d["event_family"] == "us_cpi"
        assert d["actual_initial"] == 6.4
        assert d["country"] == "US"
        assert "event_id" in d

    def test_serialize_json(self):
        event = MacroReleaseEventV1(
            event_family="us_cpi",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
        )
        json_str = json.dumps(event.to_dict())
        loaded = json.loads(json_str)
        assert loaded["event_family"] == "us_cpi"


class TestMacroConsensusObservationV1:
    def test_default_creation(self):
        obs = MacroConsensusObservationV1(
            event_id="a" * 24,
            source_name="ForexFactory",
            source_url="https://example.com",
            published_at_utc="2023-02-13T12:00:00Z",
            consensus_value=6.2,
            consensus_unit="percent",
        )
        assert len(obs.consensus_observation_id) == 24
        assert obs.estimate_type == "consensus_median"


class TestMacroRevisionRecordV1:
    def test_default_creation(self):
        rev = MacroRevisionRecordV1(
            event_id="a" * 24,
            series_id="CUUR0000SA0",
            reference_period="2023-01",
            revision_published_at_utc="2023-03-14T13:30:00Z",
            previous_value=6.4,
            revised_value=6.3,
            revision_sequence=1,
            source_url="https://example.com",
        )
        assert len(rev.revision_id) == 24
        assert rev.revision_sequence == 1


class TestMacroSourceSnapshotV1:
    def test_default_creation(self):
        snap = MacroSourceSnapshotV1(
            provider="bls",
            source_url="https://www.bls.gov/news.release/cpi.nr0.htm",
            retrieved_at_utc="2025-01-01T00:00:00Z",
            published_at_utc="2025-01-01T00:00:00Z",
            content_type="text/html",
            sha256="abc123",
            http_status=200,
        )
        assert len(snap.snapshot_id) == 24
        assert snap.parse_status == "pending"

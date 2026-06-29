"""Tests for evidence manifest builder."""
from market_radar.acquisition.evidence import build_evidence_entries
from market_radar.acquisition.contracts import ObservationStub


def test_build_evidence_entries():
    obs = ObservationStub(
        observation_id="o1",
        source_id="s1",
        title="Test",
        description="",
        event_time="2026-01-01T00:00:00+00:00",
        observed_at="2026-01-01T00:00:01+00:00",
        raw_provenance={"record_key": "CVE-2026-0001", "source_id": "s1"},
    )
    entries = build_evidence_entries("s1", [obs], "sources/s1/raw.json", "abc123")
    assert len(entries) == 1
    assert entries[0]["observation_id"] == "o1"
    assert entries[0]["raw_artifact_sha256"] == "abc123"
    assert entries[0]["record_key"] == "CVE-2026-0001"


def test_build_evidence_entries_empty():
    entries = build_evidence_entries("s1", [], "sources/s1/raw.json", "abc123")
    assert len(entries) == 0

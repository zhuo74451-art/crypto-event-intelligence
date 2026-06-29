"""Tests for storage module."""
import json
import hashlib
from pathlib import Path

from market_radar.acquisition.storage import (
    write_evidence_manifest,
    write_fetch_metadata,
    write_observations,
    write_raw_evidence,
    write_run_manifest,
    write_source_health,
    write_telemetry,
)
from market_radar.acquisition.contracts import (
    ObservationStub,
    RawEvidenceArtifact,
)


def test_write_raw_evidence(tmp_path):
    art = RawEvidenceArtifact(
        source_id="test",
        relative_path="sources/test/raw.json",
        bytes_written=6,
        content_sha256=hashlib.sha256(b"hello!").hexdigest(),
        content_type="application/json",
        retrieved_at="2026-01-01T00:00:00+00:00",
    )
    result = write_raw_evidence(tmp_path, "test", b"hello!", art)
    assert result == "sources/test/raw.json"
    assert (tmp_path / result).exists()
    assert (tmp_path / result).read_bytes() == b"hello!"


def test_write_raw_evidence_hash_mismatch(tmp_path):
    art = RawEvidenceArtifact(
        source_id="test",
        relative_path="sources/test/raw.json",
        bytes_written=6,
        content_sha256="badhash",
        content_type="application/json",
        retrieved_at="2026-01-01T00:00:00+00:00",
    )
    import pytest
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        write_raw_evidence(tmp_path, "test", b"hello!", art)


def test_write_raw_evidence_none(tmp_path):
    art = RawEvidenceArtifact(
        source_id="test",
        relative_path="sources/test/raw.json",
        bytes_written=0,
        content_sha256="",
        content_type="",
        retrieved_at="",
    )
    result = write_raw_evidence(tmp_path, "test", None, art)
    assert result == ""


def test_write_fetch_metadata(tmp_path):
    meta = {"source_id": "test", "http_status": 200, "latency_ms": 10.5}
    result = write_fetch_metadata(tmp_path, meta)
    assert "test" in result
    assert (tmp_path / result).exists()


def test_write_source_health(tmp_path):
    h1 = {"source_id": "s1", "status": "healthy"}
    h2 = {"source_id": "s1", "status": "degraded"}
    write_source_health(tmp_path, h1)
    write_source_health(tmp_path, h2)
    data = json.loads((tmp_path / "source_health.json").read_text())
    assert len(data) == 2
    assert data[0]["status"] == "healthy"
    assert data[1]["status"] == "degraded"


def test_write_observations(tmp_path):
    obs = ObservationStub(
        observation_id="o1",
        source_id="s1",
        title="Test",
        description="",
        event_time="2026-01-01T00:00:00+00:00",
        observed_at="2026-01-01T00:00:01+00:00",
    )
    write_observations(tmp_path, [obs])
    lines = (tmp_path / "observations.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
    assert "o1" in lines[0]


def test_write_evidence_manifest(tmp_path):
    entry = {"observation_id": "o1", "source_id": "s1", "title": "Test"}
    write_evidence_manifest(tmp_path, [entry])
    lines = (tmp_path / "evidence_manifest.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1


def test_write_run_manifest(tmp_path):
    write_run_manifest(tmp_path, "run1", ["cisa"], "t1", "t2", "ok")
    manifest = json.loads((tmp_path / "run_manifest.json").read_text())
    assert manifest["run_id"] == "run1"
    assert manifest["status"] == "ok"


def test_write_telemetry(tmp_path):
    write_telemetry(tmp_path, "run_started", {"mode": "replay"})
    write_telemetry(tmp_path, "run_completed", {"status": "ok"})
    lines = (tmp_path / "RUN_TELEMETRY.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2
    assert "run_started" in lines[0]
    assert "run_completed" in lines[1]

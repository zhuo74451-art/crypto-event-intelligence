"""Integrated tests: CLI replay, zero-network, partial failure, disk hash."""

import json
import hashlib
from pathlib import Path
from unittest import mock

import pytest

from market_radar.acquisition.pilot_runner import run_pilot, create_pilot_runner
from market_radar.acquisition.cli import main as cli_main, resolve_sources
from market_radar.acquisition.contracts import SourceStatus
from market_radar.acquisition.storage import verify_file_sha256, write_raw_evidence
from market_radar.acquisition.contracts import RawEvidenceArtifact

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "acquisition"


def test_cli_replay_all_zero_network(tmp_path):
    with mock.patch("requests.get") as mg:
        with mock.patch("requests.post") as mp:
            exit_code = cli_main([
                "--mode", "replay",
                "--sources", "cisa,sec,congress,bls,github_releases",
                "--limit", "3",
                "--output", str(tmp_path),
            ])
            mg.assert_not_called()
            mp.assert_not_called()
    assert exit_code == 0


def test_cli_replay_cisa_zero_network(tmp_path):
    with mock.patch("requests.get") as mg:
        exit_code = cli_main([
            "--mode", "replay",
            "--sources", "cisa",
            "--limit", "3",
            "--output", str(tmp_path),
        ])
        mg.assert_not_called()

def test_disk_hash_recomputation(tmp_path):
    import hashlib
    data = b"test evidence data for hash verification"
    expected_hash = hashlib.sha256(data).hexdigest()
    art = RawEvidenceArtifact(
        source_id="test", relative_path="sources/test/evidence.bin",
        bytes_written=len(data), content_sha256=expected_hash,
        content_type="application/octet-stream", retrieved_at="2026-01-01T00:00:00+00:00",
    )
    write_raw_evidence(tmp_path, "test", data, art)
    disk_hash = verify_file_sha256(tmp_path / "sources/test/evidence.bin", expected_hash)
    assert disk_hash == expected_hash


def test_disk_hash_mismatch_raises(tmp_path):
    art = RawEvidenceArtifact(
        source_id="test", relative_path="sources/test/evidence.bin",
        bytes_written=6, content_sha256="badhash",
        content_type="application/octet-stream", retrieved_at="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        write_raw_evidence(tmp_path, "test", b"hello!", art)


def test_partial_source_failure(tmp_path):
    with open(FIXTURE_DIR / "cisa_kev_sample.json", "rb") as f:
        sample = f.read()
    def side_effect(url, *args, **kwargs):
        resp = mock.MagicMock()
        if "cisa.gov" in url or "github" in url:
            resp.status_code = 200
            resp.content = sample
            resp.headers = {"Content-Type": "application/json"}
        else:
            resp.status_code = 500
            resp.content = b"server error"
            resp.headers = {"Content-Type": "text/html"}
        return resp
    with mock.patch("requests.get", side_effect=side_effect):
        result = run_pilot({
            "run_id": "partial_test",
            "config": {
                "sources": ["cisa", "sec"],
                "limit": 3,
                "output_dir": str(tmp_path),
                "mode": "live",
                "sec_user_agent": "TestBot/1.0",
            }
        })
    assert result["status"] != "ok"
    assert result["total_observations"] > 0


def test_congress_per_feed_artifacts(tmp_path):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = (FIXTURE_DIR / "congress_sample.xml").read_bytes()
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = run_pilot({
            "run_id": "congress_artifacts_test",
            "config": {
                "sources": ["congress"],
                "limit": 3,
                "output_dir": str(tmp_path),
                "mode": "live",
            }
        })
    assert result["status"] == "ok"
    for feed_id in ["presented_to_president", "house_floor_today", "senate_floor_today"]:
        path = tmp_path / "sources" / "congress_legislation_activity" / f"{feed_id}_raw_response.xml"
        assert path.exists(), f"Missing per-feed artifact: {path}"
        assert path.stat().st_size > 0, f"Empty per-feed artifact: {path}"


def test_event_dedup_key_source_independent():
    from market_radar.acquisition.pilot_runner import observation_stub_to_observation
    from market_radar.acquisition.contracts import ObservationStub
    stub1 = ObservationStub(
        observation_id="o1", source_id="cisa",
        title="CVE-2026-0001", description="Test",
        event_time="2026-01-01T00:00:00+00:00",
        observed_at="2026-01-01T00:00:01+00:00",
        raw_provenance={"record_key": "CVE-2026-0001"},
    )
    stub2 = ObservationStub(
        observation_id="o2", source_id="sec",
        title="CVE-2026-0001", description="Test",
        event_time="2026-01-01T00:00:00+00:00",
        observed_at="2026-01-01T00:00:02+00:00",
        raw_provenance={"record_key": "SEC-001"},
    )
    obs1 = observation_stub_to_observation(stub1)
    obs2 = observation_stub_to_observation(stub2)
    assert obs1.observation_id != obs2.observation_id
    assert obs1.event_dedup_key == obs2.event_dedup_key


def test_windows_chinese_path(tmp_path):
    chinese_dir = tmp_path / "test 目录 with spaces"
    chinese_dir.mkdir(parents=True, exist_ok=True)
    data = b"test data for chinese path"
    import hashlib
    h = hashlib.sha256(data).hexdigest()
    art = RawEvidenceArtifact(
        source_id="test", relative_path="chinese 测试文件.bin",
        bytes_written=len(data), content_sha256=h,
        content_type="application/octet-stream", retrieved_at="2026-01-01T00:00:00+00:00",
    )
    result = write_raw_evidence(chinese_dir, "test", data, art)
    assert result == "chinese 测试文件.bin"
    assert (chinese_dir / "chinese 测试文件.bin").exists()
    assert (chinese_dir / "chinese 测试文件.bin").read_bytes() == data


# Congress Evidence Manifest linkage


def test_congress_manifest_per_feed_paths(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from unittest import mock
    import json, hashlib
    fixture_path = FIXTURE_DIR / "congress_sample.xml"
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = fixture_path.read_bytes()
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = run_pilot({"run_id": "ct", "config": {"sources": ["congress"], "limit": 3, "output_dir": str(tmp_path), "mode": "live"}})
    assert result["status"] == "ok"
    mp = tmp_path / "evidence_manifest.jsonl"
    assert mp.exists()
    raw = mp.read_text(encoding="utf-8").strip()
    lines = [x for x in raw.split(chr(10)) if x]
    assert len(lines) > 0
    for line in lines:
        entry = json.loads(line)
        ap = entry.get("raw_artifact_path", "")
        assert "_summary.json" not in ap, "points to summary instead of per-feed XML"
        assert ap.endswith(".xml"), f"non-XML: {ap}"
        dp = tmp_path / ap
        assert dp.exists(), f"not on disk: {dp}"
        dh = hashlib.sha256(dp.read_bytes()).hexdigest()
        mh = entry.get("raw_artifact_sha256", "")
        if mh:
            assert dh == mh, f"SHA mismatch: disk={dh} manifest={mh}"


# Output directory isolation


def test_completed_dir_rejected(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from market_radar.acquisition.storage import write_run_manifest
    from unittest import mock
    import pytest
    write_run_manifest(tmp_path, "prev", ["cisa"], "t1", "t2", "ok")
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})


def test_degraded_dir_rejected(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from market_radar.acquisition.storage import write_run_manifest
    from unittest import mock
    import pytest
    write_run_manifest(tmp_path, "prev", ["cisa"], "t1", "t2", "degraded")
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})


def test_empty_dir_allowed(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from unittest import mock
    fresh = tmp_path / "fresh"
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        result = run_pilot({"run_id": "fr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(fresh)}})
    assert result["status"] == "ok"


def test_failed_dir_rejected(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from market_radar.acquisition.storage import write_run_manifest
    from unittest import mock
    import pytest
    write_run_manifest(tmp_path, "prev_fail", ["cisa"], "t1", "t2", "failed")
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})


def test_corrupt_manifest_dir_rejected(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from unittest import mock
    import pytest
    (tmp_path / "run_manifest.json").write_text("not valid json{{")
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})


def test_nonempty_no_manifest_rejected(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from unittest import mock
    import pytest
    (tmp_path / "some_evidence.bin").write_bytes(b"pretend evidence")
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})


def test_rejection_leaves_files_unchanged(tmp_path):
    from market_radar.acquisition.pilot_runner import run_pilot
    from unittest import mock
    import pytest, hashlib
    original_data = b"original evidence bytes"
    orig_hash = hashlib.sha256(original_data).hexdigest()
    (tmp_path / "evidence.bin").write_bytes(original_data)
    with mock.patch("requests.get") as mg:
        r = mock.MagicMock()
        r.status_code = 200; r.content = (FIXTURE_DIR / "cisa_kev_sample.json").read_bytes()
        r.headers = {"Content-Type": "application/json"}
        mg.return_value = r
        with pytest.raises(RuntimeError):
            run_pilot({"run_id": "nr", "config": {"sources": ["cisa"], "limit": 3, "output_dir": str(tmp_path)}})
    # Verify existing files are byte-for-byte unchanged
    assert (tmp_path / "evidence.bin").read_bytes() == original_data, "file was modified"
    assert hashlib.sha256((tmp_path / "evidence.bin").read_bytes()).hexdigest() == orig_hash, "hash changed"
    # Verify no new files were created by run_pilot
    dir_contents = list(tmp_path.iterdir())
    assert len(dir_contents) == 1, f"expected only evidence.bin, got {dir_contents}"



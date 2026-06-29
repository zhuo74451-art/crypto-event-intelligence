import json
from pathlib import Path
from unittest import mock

import pytest

from market_radar.acquisition.contracts import SourceStatus
from market_radar.acquisition.sources.cisa_kev import acquire_cisa_kev
from market_radar.acquisition.sources.sec_press_releases import (
    acquire_sec_press_releases, ENV_USER_AGENT,
)
from market_radar.acquisition.storage import write_raw_evidence, write_run_manifest
from market_radar.acquisition.contracts import RawEvidenceArtifact

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "acquisition"


@pytest.fixture
def cisa_sample_bytes():
    with open(FIXTURE_DIR / "cisa_kev_sample.json", "rb") as f:
        return f.read()


def test_cisa_timeout():
    import requests
    with mock.patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_cisa_kev(limit=10, timeout=1)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_cisa_connection_error():
    import requests
    with mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("DNS failed")):
        result = acquire_cisa_kev(limit=10, timeout=5)
    assert result.health.status == SourceStatus.UNAVAILABLE


def test_sec_empty_response(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = b""
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    assert result.health.status in (SourceStatus.UNAVAILABLE, SourceStatus.SCHEMA_INVALID)


def test_sec_no_user_agent_no_network(monkeypatch):
    monkeypatch.delenv(ENV_USER_AGENT, raising=False)
    with mock.patch("requests.get") as mg:
        result = acquire_sec_press_releases()
        mg.assert_not_called()
    assert result.health.status == SourceStatus.CONFIGURATION_REQUIRED


def test_storage_hash_mismatch(tmp_path):
    art = RawEvidenceArtifact(
        source_id="test", relative_path="sources/test/raw.json",
        bytes_written=6, content_sha256="badhash",
        content_type="application/json", retrieved_at="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        write_raw_evidence(tmp_path, "test", b"hello!", art)


def test_run_manifest_overwrites(tmp_path):
    write_run_manifest(tmp_path, "run1", ["cisa"], "t1", "t2", "ok")
    write_run_manifest(tmp_path, "run1", ["bls"], "t3", "t4", "degraded")
    data = json.loads((tmp_path / "run_manifest.json").read_text())
    assert data["status"] == "degraded"
    assert data["sources"] == ["bls"]


def test_cli_resolve_all():
    from market_radar.acquisition.cli import resolve_sources
    result = resolve_sources("all")
    assert "cisa" in result
    assert "congress" in result
    assert "bls" in result
    assert "github_releases" in result


def test_github_rate_limit_headers():
    from market_radar.acquisition.sources.github_releases import acquire_github_releases
    sample = json.dumps([
        {"id": 1, "tag_name": "v1.0", "draft": False, "prerelease": False,
         "published_at": "2026-01-01T00:00:00Z", "name": "v1.0",
         "html_url": "https://github.com/test/repo/releases/tag/v1.0"},
    ]).encode()
    resp_headers = {"Content-Type": "application/json",
        "X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "58", "X-RateLimit-Reset": "1234567890"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = sample
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["test/repo"])
    prov = result.observations[0].raw_provenance
    assert prov["x_ratelimit_remaining"] == "58"

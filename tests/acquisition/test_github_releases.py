"""Tests for GitHub Releases adapter."""
import json
import hashlib
from unittest import mock
from pathlib import Path

import requests
import pytest

from market_radar.acquisition.contracts import SourceStatus, sha256_of_bytes
from market_radar.acquisition.sources.github_releases import (
    RELEASES_CONTRACT,
    DEFAULT_REPOS,
    _validate_releases_response,
    acquire_github_releases,
    SOURCE_ID,
)

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


@pytest.fixture
def releases_sample_bytes():
    path = FIXTURE_DIR / "github_releases_sample.json"
    with open(path, "rb") as f:
        return f.read()


def test_contract_properties():
    c = RELEASES_CONTRACT
    assert c.source_id == SOURCE_ID
    assert c.category.value == "software_release"
    assert len(DEFAULT_REPOS) == 2


def test_valid_response(releases_sample_bytes):
    data, err = _validate_releases_response(releases_sample_bytes)
    assert err is None
    assert isinstance(data, list)
    assert len(data) == 3


def test_malformed_json():
    data, err = _validate_releases_response(b"not json")
    assert data is None
    assert "malformed_json" in err


def test_not_a_list():
    data, err = _validate_releases_response(b'{"not":"a list"}')
    assert data is None
    assert "response_not_a_list" in err


def test_acquire_success(releases_sample_bytes):
    resp_headers = {"Content-Type": "application/json",
        "X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "58", "X-RateLimit-Reset": "1234567890"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=10)
    assert result.source_id == SOURCE_ID
    assert result.health.status == SourceStatus.HEALTHY
    # 2 repos x 2 non-draft releases each
    assert len(result.observations) == 6  # 3 non-draft per repo x 2 repos
    assert len(result.errors) == 0


def test_acquire_limit(releases_sample_bytes):
    resp_headers = {"Content-Type": "application/json"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=1)
    assert len(result.observations) == 2  # 1 per repo x 2 repos


def test_draft_excluded(releases_sample_bytes):
    """Draft releases must be excluded from observations."""
    raw_with_draft = json.dumps([
        {"id": 1, "tag_name": "v1.0", "draft": False, "prerelease": False,
         "published_at": "2026-01-01T00:00:00Z", "name": "v1.0",
         "html_url": "https://github.com/bitcoin/bitcoin/releases/tag/v1.0"},
        {"id": 2, "tag_name": "v2.0-draft", "draft": True, "prerelease": False,
         "published_at": "2026-02-01T00:00:00Z", "name": "v2.0-draft",
         "html_url": "https://github.com/bitcoin/bitcoin/releases/tag/v2.0-draft"},
    ]).encode()
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = raw_with_draft
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    assert len(result.observations) == 1
    assert result.observations[0].raw_provenance["tag"] == "v1.0"


def test_prerelease_retained(releases_sample_bytes):
    """Prerelease must be retained and marked."""
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    prereleases = [o for o in result.observations if o.raw_provenance.get("prerelease") == "True"]
    assert len(prereleases) == 1
    assert prereleases[0].raw_provenance["tag"] == "v27.0-rc1"


def test_acquire_http_404():
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 404
        resp.content = b'{"message":"Not Found"}'
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["unknown/repo"])
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_timeout():
    with mock.patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_github_releases(limit=10, timeout=1, repos=["bitcoin/bitcoin"])
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_rate_limit_headers_preserved(releases_sample_bytes):
    resp_headers = {"Content-Type": "application/json",
        "X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "58", "X-RateLimit-Reset": "1234567890"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    prov = result.observations[0].raw_provenance
    assert prov["x_ratelimit_limit"] == "60"
    assert prov["x_ratelimit_remaining"] == "58"


def test_deterministic_ids(releases_sample_bytes):
    resp_headers = {"Content-Type": "application/json"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        r1 = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
        r2 = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    for o1, o2 in zip(r1.observations, r2.observations):
        assert o1.observation_id == o2.observation_id


def test_sha256_integrity(releases_sample_bytes):
    expected = hashlib.sha256(releases_sample_bytes).hexdigest()
    resp_headers = {"Content-Type": "application/json"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    assert result.health.content_sha256 == expected


def test_result_serialisable(releases_sample_bytes):
    resp_headers = {"Content-Type": "application/json"}
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = releases_sample_bytes
        resp.headers = resp_headers
        mg.return_value = resp
        result = acquire_github_releases(limit=10, repos=["bitcoin/bitcoin"])
    d = result.to_dict()
    j = json.dumps(d)
    assert len(j) > 0

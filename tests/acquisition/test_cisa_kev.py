"""Tests for CISA KEV adapter."""
import json
import hashlib
from unittest import mock
from pathlib import Path

import requests
import pytest

from market_radar.acquisition.contracts import SourceStatus, sha256_of_bytes
from market_radar.acquisition.sources.cisa_kev import (
    CISA_CONTRACT,
    _build_observations,
    _validate_json_structure,
    acquire_cisa_kev,
)

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


@pytest.fixture
def cisa_sample_bytes():
    path = FIXTURE_DIR / "cisa_kev_sample.json"
    with open(path, "rb") as f:
        return f.read()


def test_module_imports():
    from market_radar.acquisition.sources import cisa_kev
    assert cisa_kev.CISA_CONTRACT.source_id == "cisa_kev"


def test_contract_properties():
    c = CISA_CONTRACT
    assert c.category.value == "security"
    assert c.auth_mode.value == "none"
    assert c.source_id == "cisa_kev"
    assert len(c.fallback_urls) == 1


def test_valid_json_structure(cisa_sample_bytes):
    data, err = _validate_json_structure(cisa_sample_bytes)
    assert err is None
    assert data is not None
    assert data["title"] == "Known Exploited Vulnerabilities Catalog"
    assert len(data["vulnerabilities"]) == 3


def test_malformed_json():
    data, err = _validate_json_structure(b"not json")
    assert data is None
    assert err is not None
    assert "malformed_json" in err


def test_empty_json():
    data, err = _validate_json_structure(b"{}")
    assert data is None
    assert err is not None
    assert "missing_top_level_keys" in err


def test_build_observations_limit(cisa_sample_bytes):
    data, _ = _validate_json_structure(cisa_sample_bytes)
    obs = _build_observations(data, "cisa_kev", "https://example.com",
        "2026-06-29T00:00:00+00:00", "abc123", limit=2, fallback_used=False,
        artifact_path="sources/cisa_kev/raw.json")
    assert len(obs) == 2


def test_build_observations_order(cisa_sample_bytes):
    data, _ = _validate_json_structure(cisa_sample_bytes)
    obs = _build_observations(data, "cisa_kev", "https://example.com",
        "2026-06-29T00:00:00+00:00", "abc123", limit=10, fallback_used=False,
        artifact_path="sources/cisa_kev/raw.json")
    assert len(obs) == 3
    assert obs[0].raw_provenance['record_key'] == 'CVE-2026-0002'
    assert obs[1].raw_provenance['record_key'] == 'CVE-2026-0001'
    assert obs[2].raw_provenance['record_key'] == 'CVE-2026-0003'


def test_deterministic_ids(cisa_sample_bytes):
    data, _ = _validate_json_structure(cisa_sample_bytes)
    obs1 = _build_observations(data, "cisa_kev", "https://example.com",
        "2026-06-29T00:00:00+00:00", "abc123", limit=10, fallback_used=False,
        artifact_path="sources/cisa_kev/raw.json")
    obs2 = _build_observations(data, "cisa_kev", "https://example.com",
        "2026-06-29T00:00:00+00:00", "abc123", limit=10, fallback_used=False,
        artifact_path="sources/cisa_kev/raw.json")
    for o1, o2 in zip(obs1, obs2):
        assert o1.observation_id == o2.observation_id


def test_acquire_primary_success(cisa_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = cisa_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_cisa_kev(limit=10)
    assert result.source_id == "cisa_kev"
    assert result.health.status == SourceStatus.HEALTHY
    assert result.health.fallback_used is False
    assert len(result.observations) == 3
    assert len(result.errors) == 0


def test_acquire_fallback_success(cisa_sample_bytes):
    def side_effect(url, **kw):
        resp = mock.MagicMock()
        if "cisa.gov" in url:
            resp.status_code = 403
            resp.content = b""
            resp.headers = {"Content-Type": "text/html"}
        else:
            resp.status_code = 200
            resp.content = cisa_sample_bytes
            resp.headers = {"Content-Type": "application/json"}
        return resp
    with mock.patch("requests.get", side_effect=side_effect):
        result = acquire_cisa_kev(limit=10)
    assert result.health.status == SourceStatus.DEGRADED
    assert result.health.fallback_used is True
    assert len(result.observations) == 3


def test_acquire_all_fail():
    def side_effect(url, **kw):
        resp = mock.MagicMock()
        resp.status_code = 500
        resp.content = b""
        resp.headers = {"Content-Type": "text/html"}
        return resp
    with mock.patch("requests.get", side_effect=side_effect):
        result = acquire_cisa_kev(limit=10)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_timeout():
    with mock.patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_cisa_kev(limit=10, timeout=1)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_malformed_primary_valid_fallback(cisa_sample_bytes):
    def side_effect(url, **kw):
        resp = mock.MagicMock()
        if "cisa.gov" in url:
            resp.status_code = 200
            resp.content = b"not json"
            resp.headers = {"Content-Type": "application/json"}
        else:
            resp.status_code = 200
            resp.content = cisa_sample_bytes
            resp.headers = {"Content-Type": "application/json"}
        return resp
    with mock.patch("requests.get", side_effect=side_effect):
        result = acquire_cisa_kev(limit=10)
    assert result.health.status == SourceStatus.DEGRADED
    assert result.health.fallback_used is True
    assert len(result.observations) == 3


def test_limit_respected(cisa_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = cisa_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_cisa_kev(limit=1)
    assert len(result.observations) == 1


def test_sha256_integrity(cisa_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = cisa_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_cisa_kev(limit=10)
    expected_hash = hashlib.sha256(cisa_sample_bytes).hexdigest()
    assert result.health.content_sha256 == expected_hash
    assert result.artifact.content_sha256 == expected_hash


def test_result_serialisable(cisa_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = cisa_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_cisa_kev(limit=10)
    d = result.to_dict()
    j = json.dumps(d)
    assert len(j) > 0

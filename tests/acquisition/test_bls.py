"""Tests for BLS adapter."""
import json
import hashlib
from unittest import mock
from pathlib import Path

import requests
import pytest

from market_radar.acquisition.contracts import SourceStatus, sha256_of_bytes
from market_radar.acquisition.sources.bls import (
    BLS_CONTRACT,
    DEFAULT_SERIES,
    _validate_bls_response,
    _build_observations,
    acquire_bls,
    SOURCE_ID,
)

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


@pytest.fixture
def bls_sample_bytes():
    path = FIXTURE_DIR / "bls_sample.json"
    with open(path, "rb") as f:
        return f.read()


def test_contract_properties():
    c = BLS_CONTRACT
    assert c.source_id == SOURCE_ID
    assert c.category.value == "macro"
    assert c.transport.value == "https_post"
    assert len(DEFAULT_SERIES) == 3


def test_valid_bls_response(bls_sample_bytes):
    data, err = _validate_bls_response(bls_sample_bytes)
    assert err is None
    assert data is not None
    assert data["status"] == "REQUEST_SUCCEEDED"


def test_malformed_json():
    data, err = _validate_bls_response(b"not json")
    assert data is None
    assert err is not None
    assert "malformed_json" in err


def test_bls_status_error(bls_sample_bytes):
    raw = bls_sample_bytes.replace(b"REQUEST_SUCCEEDED", b"FAILED")
    data, err = _validate_bls_response(raw)
    assert data is None
    assert err is not None
    assert "bls_status_error" in err


def test_empty_response():
    raw = json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": []}}).encode()
    data, err = _validate_bls_response(raw)
    assert data is None
    assert err is not None
    assert "empty_series_list" in err


def test_build_observations(bls_sample_bytes):
    data, _ = _validate_bls_response(bls_sample_bytes)
    obs = _build_observations(data, SOURCE_ID, "https://api.bls.gov/",
        "2026-06-29T00:00:00+00:00", "abc123", 10,
        "sources/bls/raw_response.json")
    assert len(obs) == 5  # 3 CPI + 2 unemployment
    assert obs[0].raw_provenance["series_id"] == "CUUR0000SA0"
    assert obs[3].raw_provenance["series_id"] == "LNS14000000"


def test_build_observations_limit(bls_sample_bytes):
    data, _ = _validate_bls_response(bls_sample_bytes)
    obs = _build_observations(data, SOURCE_ID, "https://api.bls.gov/",
        "2026-06-29T00:00:00+00:00", "abc123", 2,
        "sources/bls/raw_response.json")
    assert len(obs) == 2


def test_acquire_success(bls_sample_bytes):
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = bls_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_bls(limit=10)
    assert result.source_id == SOURCE_ID
    assert result.health.status == SourceStatus.HEALTHY
    assert len(result.observations) == 5
    assert len(result.errors) == 0


def test_acquire_http_error():
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 429
        resp.content = b""
        resp.headers = {"Content-Type": "text/html"}
        mg.return_value = resp
        result = acquire_bls(limit=10)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_timeout():
    with mock.patch("requests.post", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_bls(limit=10, timeout=1)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_deterministic_ids(bls_sample_bytes):
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = bls_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        r1 = acquire_bls(limit=10)
        r2 = acquire_bls(limit=10)
    for o1, o2 in zip(r1.observations, r2.observations):
        assert o1.observation_id == o2.observation_id


def test_sha256_integrity(bls_sample_bytes):
    expected = hashlib.sha256(bls_sample_bytes).hexdigest()
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = bls_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_bls(limit=10)
    assert result.health.content_sha256 == expected
    assert result.artifact.content_sha256 == expected


def test_result_serialisable(bls_sample_bytes):
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = bls_sample_bytes
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_bls(limit=10)
    d = result.to_dict()
    j = json.dumps(d)
    assert len(j) > 0


def test_business_status_failure(bls_sample_bytes):
    """HTTP 200 but business status FAILED must NOT be healthy."""
    raw = bls_sample_bytes.replace(b"REQUEST_SUCCEEDED", b"FAILED")
    raw = raw.replace(b'"message": ""', b'"message": "Invalid parameters"')
    with mock.patch("requests.post") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = raw
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = acquire_bls(limit=10)
    assert result.health.status != SourceStatus.HEALTHY
    assert len(result.observations) == 0

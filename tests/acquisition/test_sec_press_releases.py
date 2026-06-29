"""Tests for SEC Press Releases adapter."""
import json
from unittest import mock
from pathlib import Path

import requests
import pytest

from market_radar.acquisition.contracts import SourceStatus
from market_radar.acquisition.sources.sec_press_releases import (
    SEC_CONTRACT,
    _parse_rss_date,
    _parse_rss_items,
    _resolve_user_agent,
    acquire_sec_press_releases,
    ENV_USER_AGENT,
)

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


@pytest.fixture
def sec_sample_bytes():
    path = FIXTURE_DIR / "sec_press_releases_sample.xml"
    with open(path, "rb") as f:
        return f.read()


# ── Contract ─────────────────────────────────────────────────────────────────


def test_contract_properties():
    c = SEC_CONTRACT
    assert c.source_id == "sec_press_releases"
    assert c.category.value == "regulatory"
    assert c.auth_mode.value == "user_agent"


# ── User-Agent resolution ────────────────────────────────────────────────────


def test_resolve_ua_from_cli():
    assert _resolve_user_agent("MyBot/1.0") == "MyBot/1.0"


def test_resolve_ua_from_env(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "EnvBot/1.0")
    assert _resolve_user_agent() == "EnvBot/1.0"


def test_resolve_ua_cli_overrides_env(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "EnvBot/1.0")
    assert _resolve_user_agent("CliBot/1.0") == "CliBot/1.0"


def test_resolve_ua_none(monkeypatch):
    monkeypatch.delenv(ENV_USER_AGENT, raising=False)
    assert _resolve_user_agent() is None


# ── RSS date parsing ─────────────────────────────────────────────────────────


def test_parse_rfc822_date():
    result = _parse_rss_date("Mon, 15 Jun 2026 12:00:00 -0400")
    assert result is not None
    assert "T" in result


def test_parse_empty_date():
    assert _parse_rss_date("") is None


def test_parse_invalid_date():
    assert _parse_rss_date("not a date") is None


# ── RSS XML parsing ──────────────────────────────────────────────────────────


def test_parse_valid_rss(sec_sample_bytes):
    items, err = _parse_rss_items(sec_sample_bytes)
    assert err is None
    assert len(items) == 3
    assert items[0]["title"] == "SEC Press Release 2026000"
    assert items[0]["guid"] == "sec-pr-2026-000"


def test_parse_malformed_xml():
    items, err = _parse_rss_items(b"not xml")
    assert len(items) == 0
    assert err is not None
    assert "malformed_xml" in err


def test_parse_empty_feed():
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title></channel></rss>'
    items, err = _parse_rss_items(empty)
    assert len(items) == 0
    assert "empty_feed" in err


# ── acquire_sec_press_releases: no User-Agent ────────────────────────────────


def test_no_user_agent(monkeypatch):
    monkeypatch.delenv(ENV_USER_AGENT, raising=False)
    result = acquire_sec_press_releases()
    assert result.health.status == SourceStatus.CONFIGURATION_REQUIRED
    assert len(result.observations) == 0
    assert len(result.errors) > 0


# ── acquire_sec_press_releases: mocked HTTP ──────────────────────────────────


def test_acquire_success(sec_sample_bytes, monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases(limit=10)
    assert result.source_id == "sec_press_releases"
    assert result.health.status == SourceStatus.HEALTHY
    assert result.health.fallback_used is False
    assert len(result.observations) == 3
    assert len(result.errors) == 0


def test_acquire_limit(sec_sample_bytes, monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases(limit=1)
    assert len(result.observations) == 1


def test_acquire_http_error(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 403; resp.content = b""; resp.headers = {"Content-Type": "text/html"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_malformed_xml(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = b"not xml"
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    assert result.health.status == SourceStatus.SCHEMA_INVALID
    assert len(result.observations) == 0
    assert len(result.errors) > 0


def test_acquire_timeout(monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_sec_press_releases()
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_deterministic_ids(sec_sample_bytes, monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        r1 = acquire_sec_press_releases(limit=10)
        r2 = acquire_sec_press_releases(limit=10)
    for o1, o2 in zip(r1.observations, r2.observations):
        assert o1.observation_id == o2.observation_id


def test_sha256_integrity(sec_sample_bytes, monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    import hashlib
    expected = hashlib.sha256(sec_sample_bytes).hexdigest()
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    assert result.health.content_sha256 == expected
    assert result.artifact.content_sha256 == expected


def test_result_serialisable(sec_sample_bytes, monkeypatch):
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    d = result.to_dict()
    j = json.dumps(d)
    assert len(j) > 0

"""Additional SEC tests — missing pubDate, no-token check, replay consistency."""
import json
from unittest import mock
from pathlib import Path

from market_radar.acquisition.contracts import SourceStatus
from market_radar.acquisition.sources.sec_press_releases import (
    _parse_rss_items,
    _resolve_user_agent,
    acquire_sec_press_releases,
    ENV_USER_AGENT,
)


FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


def test_missing_pubdate_detected():
    """Items without pubDate must be flagged, not silently dropped."""
    xml = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>T</title>
<item><title>No Date</title><link>https://ex.com/1</link><guid>g1</guid><description>desc</description></item>
</channel>
</rss>"""
    items, err = _parse_rss_items(xml)
    assert len(items) == 0
    assert err is not None
    assert "missing_pubDate" in err


def test_empty_feed_detected():
    xml = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>T</title>
</channel>
</rss>"""
    items, err = _parse_rss_items(xml)
    assert len(items) == 0
    assert "empty_feed" in err


def test_no_tokens_in_report(sec_sample_bytes, monkeypatch):
    """Verify no sensitive headers/tokens appear in the result dict."""
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_sec_press_releases()
    d = result.to_dict()
    j = json.dumps(d)
    # No bot token, API key, or authorization header should be present
    assert "bot_token" not in j
    assert "api_key" not in j
    assert "authorization" not in j.lower()
    assert "Bearer" not in j


def test_sha256_integrity_sec(sec_sample_bytes, monkeypatch):
    """SHA-256 recorded in health and artifact must match actual bytes."""
    import hashlib
    monkeypatch.setenv(ENV_USER_AGENT, "TestBot/1.0")
    expected = hashlib.sha256(sec_sample_bytes).hexdigest()
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sec_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        r1 = acquire_sec_press_releases()
        r2 = acquire_sec_press_releases()
    # Both runs consistent
    assert r1.health.content_sha256 == expected
    assert r2.health.content_sha256 == expected
    assert r1.artifact.content_sha256 == r2.artifact.content_sha256
    # Observation IDs consistent across runs
    for o1, o2 in zip(r1.observations, r2.observations):
        assert o1.observation_id == o2.observation_id

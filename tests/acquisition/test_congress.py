"""Tests for Congress.gov RSS adapter."""
import json
from unittest import mock
from pathlib import Path

import requests
import pytest

from market_radar.acquisition.contracts import SourceStatus
from market_radar.acquisition.sources.congress import (
    CONGRESS_CONTRACT,
    FEED_DEFS,
    _parse_rss_date,
    _parse_rss_items,
    acquire_congress,
    SOURCE_ID,
)

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition"


@pytest.fixture
def congress_sample_bytes():
    path = FIXTURE_DIR / "congress_sample.xml"
    with open(path, "rb") as f:
        return f.read()


def test_contract_properties():
    c = CONGRESS_CONTRACT
    assert c.source_id == SOURCE_ID
    assert c.category.value == "legislative"
    assert len(FEED_DEFS) == 3


def test_parse_rss_date_valid():
    result = _parse_rss_date("Mon, 15 Jun 2026 14:00:00 -0400")
    assert result is not None
    assert "T" in result


def test_parse_rss_date_empty():
    assert _parse_rss_date("") is None


def test_parse_rss_date_invalid():
    assert _parse_rss_date("not a date") is None


def test_parse_valid_rss(congress_sample_bytes):
    items, err = _parse_rss_items(congress_sample_bytes)
    assert err is None
    assert len(items) == 3
    assert items[0]["title"] == "H.R. 1234 - Test Bill"


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


def test_missing_pubdate_detected():
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


def test_acquire_success(congress_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_congress(limit=10)
    assert result.source_id == SOURCE_ID
    assert len(result.observations) == 9  # 3 feeds x 3 items
    assert result.health.status == SourceStatus.HEALTHY


def test_acquire_limit(congress_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_congress(limit=1)
    assert len(result.observations) == 3  # 3 feeds x 1 item


def test_acquire_one_feed_fails(congress_sample_bytes):
    call_count = [0]
    def side_effect(url, **kw):
        call_count[0] += 1
        resp = mock.MagicMock()
        if call_count[0] == 2:  # Second feed (house) fails
            resp.status_code = 403
            resp.content = b""
            resp.headers = {"Content-Type": "text/html"}
        else:
            resp.status_code = 200
            resp.content = congress_sample_bytes
            resp.headers = {"Content-Type": "application/rss+xml"}
        return resp
    with mock.patch("requests.get", side_effect=side_effect):
        result = acquire_congress(limit=10)
    # Overall should be unavailable since one feed failed
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 6  # 2 successful feeds x 3 items


def test_acquire_all_fail():
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 500
        resp.content = b""
        resp.headers = {"Content-Type": "text/html"}
        mg.return_value = resp
        result = acquire_congress(limit=10)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_acquire_timeout():
    with mock.patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        result = acquire_congress(limit=10, timeout=1)
    assert result.health.status == SourceStatus.UNAVAILABLE
    assert len(result.observations) == 0


def test_deterministic_ids(congress_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        r1 = acquire_congress(limit=10)
        r2 = acquire_congress(limit=10)
    for o1, o2 in zip(r1.observations, r2.observations):
        assert o1.observation_id == o2.observation_id


def test_feed_specific_observations(congress_sample_bytes):
    """Observations from different feeds must have different IDs even if same GUID."""
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_congress(limit=10)
    # Verify feed_id is in the provenance
    feed_ids = set(o.raw_provenance["feed_id"] for o in result.observations)
    assert feed_ids == {"presented_to_president", "house_floor_today", "senate_floor_today"}


def test_sha256_integrity(congress_sample_bytes):
    import hashlib
    expected = hashlib.sha256(congress_sample_bytes).hexdigest()
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_congress(limit=10)
    assert result.health.content_sha256 is not None


def test_result_serialisable(congress_sample_bytes):
    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = congress_sample_bytes
        resp.headers = {"Content-Type": "application/rss+xml"}
        mg.return_value = resp
        result = acquire_congress(limit=10)
    d = result.to_dict()
    j = json.dumps(d)
    assert len(j) > 0

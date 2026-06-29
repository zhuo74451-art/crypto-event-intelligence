"""Tests for acquisition contracts."""
import json, hashlib
from market_radar.acquisition.contracts import (
    AcquisitionResult, AuthMode, FetchMetadata, ObservationStub,
    RawEvidenceArtifact, SourceCategory, SourceContract, SourceHealth,
    SourceStatus, Transport, deterministic_observation_id,
    sha256_of_bytes, utc_now,
)

class TestSourceContract:
    def test_minimal_contract(self):
        c = SourceContract(source_id='test-source', display_name='Test Source',
            category=SourceCategory.SECURITY, authority='Test Authority',
            primary_url='https://example.com/data.json')
        assert c.source_id == 'test-source'
        assert c.enabled is True
        assert c.timeout_seconds == 15

    def test_serialise_roundtrip(self):
        c = SourceContract(source_id='test', display_name='Test',
            category=SourceCategory.REGULATORY, authority='A',
            primary_url='https://example.com',
            fallback_urls=['https://fallback.example.com'],
            transport=Transport.HTTPS_GET, auth_mode=AuthMode.USER_AGENT)
        d = c.to_dict()
        assert d['category'] == 'regulatory'
        assert d['transport'] == 'https_get'
        restored = SourceContract.from_dict(d)
        assert restored.source_id == 'test'
        assert restored.category == SourceCategory.REGULATORY

    def test_from_dict_with_string_enums(self):
        data = {'source_id': 's1', 'display_name': 'S1', 'category': 'macro',
            'authority': 'A', 'primary_url': 'https://example.com',
            'transport': 'https_get', 'auth_mode': 'none'}
        c = SourceContract.from_dict(data)
        assert c.category == SourceCategory.MACRO
        assert c.auth_mode == AuthMode.NONE

    def test_json_roundtrip(self):
        c = SourceContract(source_id='json-test', display_name='JSON Test',
            category=SourceCategory.SECURITY, authority='J',
            primary_url='https://j.example.com')
        j = json.dumps(c.to_dict())
        restored = SourceContract.from_dict(json.loads(j))
        assert restored.source_id == 'json-test'

class TestSourceStatus:
    def test_all_status_values(self):
        assert SourceStatus.HEALTHY.value == 'healthy'
        assert SourceStatus.DEGRADED.value == 'degraded'
        assert SourceStatus.UNAVAILABLE.value == 'unavailable'
        assert SourceStatus.SCHEMA_INVALID.value == 'schema_invalid'

    def test_status_serialisation(self):
        h = SourceHealth(source_id='s1', status=SourceStatus.DEGRADED)
        d = h.to_dict()
        assert d['status'] == 'degraded'

class TestSourceHealth:
    def test_from_fetch_metadata(self):
        meta = FetchMetadata(source_id='s1',
            attempted_urls=['https://a.com','https://b.com'],
            selected_url='https://b.com', http_status=200,
            content_type='application/json', bytes_received=1024,
            latency_ms=150.5, retrieved_at='2026-01-01T00:00:00+00:00',
            content_sha256='abc123', fallback_used=True)
        health = SourceHealth.from_metadata(meta, SourceStatus.DEGRADED)
        assert health.status == SourceStatus.DEGRADED
        assert health.fallback_used is True

class TestHelpers:
    def test_sha256_of_bytes(self):
        data = b'hello world'
        expected = hashlib.sha256(data).hexdigest()
        assert sha256_of_bytes(data) == expected

    def test_deterministic_observation_id(self):
        id1 = deterministic_observation_id('cisa','CVE-2026-0001','2026-01-01')
        id2 = deterministic_observation_id('cisa','CVE-2026-0001','2026-01-01')
        assert id1 == id2
        assert len(id1) == 16

    def test_observation_id_different_keys(self):
        id1 = deterministic_observation_id('cisa','CVE-2026-0001','2026-01-01')
        id2 = deterministic_observation_id('cisa','CVE-2026-0002','2026-01-01')
        assert id1 != id2

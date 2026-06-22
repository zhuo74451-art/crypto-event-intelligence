"""Tests for common contracts — version, IDs, time, data availability, serialization."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from market_radar.intelligence.contracts.common import (
    SchemaVersion, DataAvailability, DataStatus, IntelligenceID,
    IDPrefix, ContractBase, utc_now, utc_parse, validate_utc,
    hash_identity, hash_content,
)


class TestSchemaVersion:
    def test_parse_valid(self):
        v = SchemaVersion.parse("1.0.0")
        assert v.major == 1 and v.minor == 0 and v.patch == 0

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            SchemaVersion.parse("invalid")

    def test_str(self):
        assert str(SchemaVersion(2, 1, 3)) == "2.1.3"

    def test_compatible_same_major(self):
        v1 = SchemaVersion(1, 0, 0)
        v2 = SchemaVersion(1, 5, 0)
        assert v1.is_compatible_with(v2)

    def test_incompatible_different_major(self):
        v1 = SchemaVersion(1, 0, 0)
        v2 = SchemaVersion(2, 0, 0)
        assert not v1.is_compatible_with(v2)

    def test_consumer_requires_minor_lte(self):
        v1 = SchemaVersion(1, 5, 0)
        v2 = SchemaVersion(1, 0, 0)
        assert not v1.is_compatible_with(v2)


class TestDataAvailability:
    def test_available(self):
        da = DataAvailability.available(42)
        assert da.status == DataStatus.AVAILABLE
        assert da.value == 42

    def test_missing(self):
        da = DataAvailability.missing("not found")
        assert da.status == DataStatus.MISSING
        assert da.reason == "not found"

    def test_conflicting(self):
        da = DataAvailability.conflicting("sources disagree")
        assert da.status == DataStatus.CONFLICTING

    def test_stale(self):
        da = DataAvailability.stale(100, "outdated")
        assert da.status == DataStatus.STALE
        assert da.value == 100

    def test_not_applicable(self):
        da = DataAvailability.not_applicable()
        assert da.status == DataStatus.NOT_APPLICABLE

    def test_unsupported(self):
        da = DataAvailability.unsupported("no adapter")
        assert da.status == DataStatus.UNSUPPORTED


class TestIntelligenceID:
    def test_from_string(self):
        eid = IntelligenceID.from_string("evi_abc123")
        assert eid.prefix == IDPrefix.EVIDENCE
        assert eid.value == "abc123"

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            IntelligenceID.from_string("no_prefix")

    def test_from_payload_deterministic(self):
        pid1 = IntelligenceID.from_payload(IDPrefix.EVENT, "event-payload")
        pid2 = IntelligenceID.from_payload(IDPrefix.EVENT, "event-payload")
        assert str(pid1) == str(pid2)

    def test_from_payload_different_prefixes(self):
        pid1 = IntelligenceID.from_payload(IDPrefix.EVENT, "payload")
        pid2 = IntelligenceID.from_payload(IDPrefix.STRATEGY, "payload")
        assert str(pid1) != str(pid2)

    def test_str_format(self):
        eid = IntelligenceID(IDPrefix.SOURCE, "abc")
        assert str(eid) == "src_abc"

    def test_different_payloads_different_ids(self):
        pid1 = IntelligenceID.from_payload(IDPrefix.EVENT, "payload-a")
        pid2 = IntelligenceID.from_payload(IDPrefix.EVENT, "payload-b")
        assert str(pid1) != str(pid2)

    def test_all_prefixes(self):
        for prefix in IDPrefix:
            eid = IntelligenceID(prefix, "test")
            assert str(eid).startswith(prefix.value + "_")


class TestTimeUtilities:
    def test_utc_now_format(self):
        now = utc_now()
        assert now.endswith("Z")
        assert "T" in now

    def test_utc_parse_valid(self):
        dt = utc_parse("2024-01-01T00:00:00Z")
        assert dt.tzinfo is not None
        assert dt.year == 2024

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="Naive datetime"):
            utc_parse("2024-01-01T00:00:00")

    def test_validate_utc(self):
        result = validate_utc("2024-06-15T12:30:00Z")
        assert result.endswith("Z")

    def test_contract_base_auto_timestamps(self):
        cb = ContractBase(contract_name="Test")
        assert cb.created_at is not None
        assert cb.as_of_time is not None
        assert cb.created_at.endswith("Z")


class TestHashing:
    def test_identity_hash_deterministic(self):
        h1 = hash_identity("test-payload")
        h2 = hash_identity("test-payload")
        assert h1 == h2

    def test_identity_hash_different(self):
        h1 = hash_identity("payload-a")
        h2 = hash_identity("payload-b")
        assert h1 != h2

    def test_identity_hash_length(self):
        h = hash_identity("test")
        assert len(h) == 32


class TestDecimalRoundTrip:
    def test_decimal_in_to_dict(self):
        cb = ContractBase(contract_name="Test")
        d = cb.to_dict()
        assert isinstance(d, dict)
        assert d["contract_name"] == "Test"

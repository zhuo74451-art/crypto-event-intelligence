"""Tests for serialization — canonical JSON, hashing, schema drift."""

import json
import pytest
from market_radar.intelligence.serialization.canonical_json import canonical_json, canonical_json_bytes
from market_radar.intelligence.serialization.hashing import (
    compute_identity_hash, compute_content_hash, compute_revision_hash,
)


class TestCanonicalJSON:
    def test_deterministic_output(self):
        data = {"b": 2, "a": 1, "c": {"z": 3, "x": 4}}
        j1 = canonical_json(data)
        j2 = canonical_json(data)
        assert j1 == j2

    def test_bytes_equal(self):
        data = {"key": "value"}
        b1 = canonical_json_bytes(data)
        b2 = canonical_json_bytes(data)
        assert b1 == b2

    def test_enum_serialized_as_value(self):
        from enum import Enum
        class Color(Enum):
            RED = "red"
        data = {"color": Color.RED}
        j = canonical_json(data)
        assert '"red"' in j

    def test_decimal_serialized(self):
        from decimal import Decimal
        data = {"amount": Decimal("123.45")}
        j = canonical_json(data)
        assert '123.45' in j


class TestHashing:
    def test_identity_hash_deterministic(self):
        h1 = compute_identity_hash("evidence", "payload")
        h2 = compute_identity_hash("evidence", "payload")
        assert h1 == h2

    def test_identity_hash_different_payloads(self):
        h1 = compute_identity_hash("evidence", "payload-a")
        h2 = compute_identity_hash("evidence", "payload-b")
        assert h1 != h2

    def test_identity_hash_different_namespaces(self):
        h1 = compute_identity_hash("evidence", "payload")
        h2 = compute_identity_hash("event", "payload")
        assert h1 != h2

    def test_content_hash_deterministic(self):
        data = {"a": 1, "b": 2}
        h1 = compute_content_hash(data)
        h2 = compute_content_hash(data)
        assert h1 == h2

    def test_content_hash_different(self):
        h1 = compute_content_hash({"a": 1})
        h2 = compute_content_hash({"a": 2})
        assert h1 != h2

    def test_revision_hash_excludes_metadata(self):
        data1 = {"a": 1, "created_at": "2024-01-01", "updated_at": "2024-06-01"}
        data2 = {"a": 1, "created_at": "2024-02-01", "updated_at": "2024-07-01"}
        h1 = compute_revision_hash(data1)
        h2 = compute_revision_hash(data2)
        assert h1 == h2

    def test_revision_hash_detects_content_change(self):
        data1 = {"a": 1, "created_at": "2024-01-01"}
        data2 = {"a": 2, "created_at": "2024-01-01"}
        h1 = compute_revision_hash(data1)
        h2 = compute_revision_hash(data2)
        assert h1 != h2


class TestSchemaDrift:
    def test_schema_export_import(self):
        from market_radar.intelligence.serialization.schema_export import export_schema, check_schema_drift
        from market_radar.intelligence.contracts.evidence import EvidenceItem
        schema = export_schema(EvidenceItem)
        assert schema["title"] == "EvidenceItem"
        assert "$schema" in schema

"""Tests for schema drift detection."""

import os
import json
import tempfile
import pytest
from market_radar.intelligence.serialization.schema_export import (
    export_schema, check_schema_drift, write_schema,
)
from market_radar.intelligence.contracts.evidence import EvidenceItem


class TestSchemaDrift:
    def test_export_creates_valid_schema(self):
        schema = export_schema(EvidenceItem, "EvidenceItem")
        assert schema["title"] == "EvidenceItem"
        assert "$schema" in schema
        assert "properties" in schema
        assert "evidence_id" in schema["properties"]

    def test_check_no_drift_when_matches(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            schema = export_schema(EvidenceItem, "EvidenceItem")
            json.dump(schema, f, sort_keys=True)
            f.flush()
            assert check_schema_drift(EvidenceItem, f.name)
        os.unlink(f.name)

    def test_drift_detected_when_file_missing(self):
        assert not check_schema_drift(EvidenceItem, "/nonexistent/path/schema.json")

    def test_drift_detected_when_model_changed(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Write a deliberately different schema
            bad_schema = {"title": "EvidenceItem", "$schema": "draft-07",
                          "properties": {"wrong_field": {"type": "string"}}}
            json.dump(bad_schema, f, sort_keys=True)
            f.flush()
            assert not check_schema_drift(EvidenceItem, f.name)
        os.unlink(f.name)

    def test_all_exported_schemas_valid(self):
        """Verify all schema files in schemas/intelligence/v1/ parse as valid JSON."""
        schema_dir = "schemas/intelligence/v1"
        if not os.path.isdir(schema_dir):
            pytest.skip("Schema directory not found")
        for fname in os.listdir(schema_dir):
            if fname.endswith(".json"):
                with open(os.path.join(schema_dir, fname)) as f:
                    schema = json.load(f)
                assert "title" in schema
                assert "$schema" in schema

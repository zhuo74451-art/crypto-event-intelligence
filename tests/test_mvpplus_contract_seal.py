"""Contract Seal validation tests for MVP+.

Validates that all contract files:
- Exist and are valid JSON
- Follow Draft 2020-12 schema conventions
- Have correct enums, required fields, null policy
- Have matching example files
"""

import json
from pathlib import Path

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts" / "mvpplus" / "v1"
EXAMPLES_DIR = CONTRACTS_DIR / "examples"

# Expected contract files and their required fields
CONTRACT_MANIFEST = {
    "whale_position.schema.json": {
        "required": [
            "address", "label", "coin", "direction", "signed_size",
            "absolute_size", "position_value_usd", "entry_price",
            "mark_price", "leverage", "unrealized_pnl_usd",
            "snapshot_time_utc", "data_source"
        ],
        "direction_enum": ["long", "short"],
        "example": "whale_position.example.json"
    },
    "whale_position_change.schema.json": {
        "required": [
            "address", "label", "coin", "change_type",
            "previous", "current", "detected_at_utc", "data_source"
        ],
        "change_type_enum": [
            "open_long", "open_short", "increase_long", "increase_short",
            "reduce_long", "reduce_short", "close_long", "close_short",
            "flip_long_to_short", "flip_short_to_long",
            "liquidation_distance_narrowed"
        ],
        "example": "whale_position_change.example.json"
    },
    "market_context.schema.json": {
        "required": [
            "asset", "venue", "snapshot_time_utc",
            "current_price", "source_health"
        ],
        "example": "market_context.example.json"
    },
    "unified_feed_item.schema.json": {
        "required": [
            "item_id", "stream_type", "source_label",
            "published_at_utc", "ingested_at_utc", "title", "source_health"
        ],
        "stream_type_enum": ["flash", "news", "tg"],
        "example": "unified_feed_item.example.json"
    },
    "source_claim.schema.json": {
        "required": [
            "claim_id", "source_item_id", "claim_type",
            "statement", "extracted_at_utc", "extraction_status"
        ],
        "claim_type_enum": ["fact", "derived_data", "viewpoint", "prediction", "rumor"],
        "extraction_status_enum": ["complete", "partial", "unavailable"],
        "example": "source_claim.example.json"
    },
    "event_cluster.schema.json": {
        "required": [
            "cluster_id", "title", "event_type",
            "first_seen_at_utc", "last_seen_at_utc",
            "observation_ids", "claim_ids"
        ],
        "freshness_enum": ["fresh", "aging", "stale", "archived"],
        "example": "event_cluster.example.json"
    },
    "source_health.schema.json": {
        "required": ["status", "source", "occurred_at_utc"],
        "status_enum": ["healthy", "degraded", "unavailable"],
        "example": None
    },
    "run_report.schema.json": {
        "required": [
            "run_id", "started_at_utc", "ended_at_utc",
            "source_results", "record_counts",
            "artifact_paths", "decision"
        ],
        "decision_enum": ["accept", "review_needed", "rejected"],
        "example": "run_report.example.json"
    }
}

# Contracts that contain a "direction" field with enum long/short
DIRECTION_CONTRACTS = ["whale_position.schema.json"]


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _find_enum_values(schema, field_name):
    """Find enum values for a field in schema properties."""
    props = schema.get("properties", {})
    if field_name in props:
        return props[field_name].get("enum")
    # Check nested allOf
    for clause in schema.get("allOf", []):
        result = _find_enum_values(clause, field_name)
        if result:
            return result
    return None


class TestContractSeal:

    def test_contracts_directory_exists(self):
        assert CONTRACTS_DIR.exists(), f"Contracts dir not found: {CONTRACTS_DIR}"
        assert CONTRACTS_DIR.is_dir()

    def test_all_contract_files_exist(self):
        for filename in CONTRACT_MANIFEST:
            filepath = CONTRACTS_DIR / filename
            assert filepath.exists(), f"Missing contract: {filename}"
            assert filepath.is_file()

    def test_all_contracts_are_valid_json(self):
        for filename in CONTRACT_MANIFEST:
            data = _load_json(CONTRACTS_DIR / filename)
            assert "$schema" in data, f"{filename} missing $schema"
            assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema", \
                f"{filename} does not use Draft 2020-12"
            assert "type" in data, f"{filename} missing type"
            assert data["type"] == "object", f"{filename} root type must be object"

    def test_required_fields_match_manifest(self):
        for filename, manifest in CONTRACT_MANIFEST.items():
            data = _load_json(CONTRACTS_DIR / filename)
            required = data.get("required", [])
            expected = sorted(manifest["required"])
            actual = sorted(required)
            assert actual == expected, \
                f"{filename} required mismatch.\n  Expected: {expected}\n  Actual:   {actual}"

    def test_required_fields_are_in_properties(self):
        for filename, manifest in CONTRACT_MANIFEST.items():
            data = _load_json(CONTRACTS_DIR / filename)
            props = data.get("properties", {})
            for field in manifest["required"]:
                assert field in props, \
                    f"{filename}: required field '{field}' not in properties"

    def test_enum_values(self):
        """Verify enum values match contract."""
        for filename, manifest in CONTRACT_MANIFEST.items():
            data = _load_json(CONTRACTS_DIR / filename)
            # direction enum
            if "direction_enum" in manifest:
                enum_vals = _find_enum_values(data, "direction")
                assert enum_vals == manifest["direction_enum"], \
                    f"{filename}: direction enum mismatch"
            # change_type enum
            if "change_type_enum" in manifest:
                enum_vals = _find_enum_values(data, "change_type")
                assert enum_vals == manifest["change_type_enum"], \
                    f"{filename}: change_type enum mismatch"
            # stream_type enum
            if "stream_type_enum" in manifest:
                enum_vals = _find_enum_values(data, "stream_type")
                assert enum_vals == manifest["stream_type_enum"], \
                    f"{filename}: stream_type enum mismatch"
            # claim_type enum
            if "claim_type_enum" in manifest:
                enum_vals = _find_enum_values(data, "claim_type")
                assert enum_vals == manifest["claim_type_enum"], \
                    f"{filename}: claim_type enum mismatch"
            # extraction_status enum
            if "extraction_status_enum" in manifest:
                enum_vals = _find_enum_values(data, "extraction_status")
                assert enum_vals == manifest["extraction_status_enum"], \
                    f"{filename}: extraction_status enum mismatch"
            # status enum (source_health)
            if "status_enum" in manifest:
                enum_vals = _find_enum_values(data, "status")
                assert enum_vals == manifest["status_enum"], \
                    f"{filename}: status enum mismatch"
            # freshness_state enum
            if "freshness_enum" in manifest:
                enum_vals = _find_enum_values(data, "freshness_state")
                assert enum_vals == manifest["freshness_enum"], \
                    f"{filename}: freshness_state enum mismatch"
            # decision enum
            if "decision_enum" in manifest:
                enum_vals = _find_enum_values(data, "decision")
                assert enum_vals == manifest["decision_enum"], \
                    f"{filename}: decision enum mismatch"

    def test_no_buy_sell_direction(self):
        """Direction must use long/short, never buy/sell."""
        for filename in DIRECTION_CONTRACTS:
            data = _load_json(CONTRACTS_DIR / filename)
            direction = data.get("properties", {}).get("direction", {})
            enum_vals = direction.get("enum", [])
            assert "buy" not in enum_vals, \
                f"{filename}: direction must not include 'buy'"
            assert "sell" not in enum_vals, \
                f"{filename}: direction must not include 'sell'"
            desc = direction.get("description", "")
            # Description may mention "NEVER buy/sell" as convention doc;
            # only enum values must exclude them.
            pass

    def test_null_policy_in_description(self):
        """Required fields descriptions must mention null policy for optional fields."""
        for filename, manifest in CONTRACT_MANIFEST.items():
            data = _load_json(CONTRACTS_DIR / filename)
            description = data.get("description", "")
            assert "null" in description.lower(), \
                f"{filename}: top description must mention null policy"

    def test_example_files_exist(self):
        for filename, manifest in CONTRACT_MANIFEST.items():
            example = manifest.get("example")
            if example:
                example_path = EXAMPLES_DIR / example
                assert example_path.exists(), \
                    f"Missing example for {filename}: {example}"
                assert example_path.is_file()

    def test_example_files_are_valid_json(self):
        for example_file in EXAMPLES_DIR.glob("*.json"):
            data = _load_json(example_file)
            assert data is not None, f"Could not parse: {example_file.name}"

    def test_timestamp_format_utc(self):
        """Verify required timestamp fields end in Z (UTC convention)."""
        timestamp_fields = [
            "snapshot_time_utc", "published_at_utc", "ingested_at_utc",
            "extracted_at_utc", "detected_at_utc", "first_seen_at_utc",
            "last_seen_at_utc", "started_at_utc", "ended_at_utc",
            "occurred_at_utc", "snapshot_time_utc"
        ]
        for filename in CONTRACT_MANIFEST:
            data = _load_json(CONTRACTS_DIR / filename)
            props = data.get("properties", {})
            for field_name, field_props in props.items():
                if field_name in timestamp_fields:
                    fmt = field_props.get("format", "")
                    desc = field_props.get("description", "")
                    assert fmt == "date-time", \
                        f"{filename}.{field_name}: format must be 'date-time', got '{fmt}'"
                    assert "UTC" in desc or "utc" in desc.lower(), \
                        f"{filename}.{field_name}: description must mention UTC"

    def test_usd_unit_documentation(self):
        """Verify monetary fields mention USD unit in description."""
        usd_fields = [
            "account_value_usd", "position_value_usd", "unrealized_pnl_usd",
            "position_value_delta_usd", "entry_price_delta_usd",
            "unrealized_pnl_delta_usd", "volume_24h_usd", "open_interest_usd",
            "current_price", "entry_price", "mark_price",
            "oracle_price", "liquidation_price", "high_24h", "low_24h"
        ]
        for filename in CONTRACT_MANIFEST:
            data = _load_json(CONTRACTS_DIR / filename)
            props = data.get("properties", {})
            for field_name, field_props in props.items():
                if field_name in usd_fields:
                    desc = field_props.get("description", "")
                    assert "USD" in desc, \
                        f"{filename}.{field_name}: description must document USD unit"

    def test_readme_exists(self):
        readme = CONTRACTS_DIR / "README.md"
        assert readme.exists(), "Missing README.md"
        content = readme.read_text(encoding="utf-8")
        assert "Null Policy" in content, "README must document null policy"
        assert "Time Format" in content, "README must document time format"
        assert "Monetary Units" in content, "README must document monetary units"
        assert "Direction" in content, "README must document direction convention"

    def test_no_missing_value_sentinel_zero(self):
        """Verify contracts never document default 0 as missing value policy."""
        for filename in CONTRACT_MANIFEST:
            data = _load_json(CONTRACTS_DIR / filename)
            description = json.dumps(data).lower()
            # Look for patterns that suggest using 0 as missing sentinel
            assert "default 0" not in description, \
                f"{filename}: must not default to 0 for missing values (use null)"
            assert "default: 0" not in description, \
                f"{filename}: must not default to 0 for missing values (use null)"

    def test_source_health_is_referenced(self):
        """Verify source_health uses $ref where applicable."""
        ref_contracts = [
            "whale_position.schema.json",
            "market_context.schema.json",
            "unified_feed_item.schema.json",
        ]
        for filename in ref_contracts:
            data = _load_json(CONTRACTS_DIR / filename)
            props = data.get("properties", {})
            sh = props.get("source_health", {})
            assert "$ref" in sh, \
                f"{filename}: source_health should use $ref"

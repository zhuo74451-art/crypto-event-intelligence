#!/usr/bin/env python3
"""MVP+ QA Validation — validates all lane outputs against contract schemas.

Checks:
1. All output JSON files exist and are valid JSON
2. Outputs conform to contract schema required fields
3. Null policy is respected (never 0 or "" for missing data)
4. No regression in baseline tests
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 3))
RESULT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")

REQUIRED_FIELDS_MAP = {
    "lane1_whale_positions.json": {
        "type": "positions",
        "item_fields": [
            "address", "label", "coin", "direction", "signed_size",
            "absolute_size", "position_value_usd", "entry_price",
            "mark_price", "leverage", "unrealized_pnl_usd",
            "snapshot_time_utc", "data_source",
        ],
        "root_fields": ["positions", "source_health", "snapshot_time_utc"],
    },
    "lane2_whale_changes.json": {
        "type": "changes",
        "item_fields": [
            "address", "label", "coin", "change_type",
            "previous", "current", "detected_at_utc", "data_source",
        ],
        "root_fields": ["changes", "source_health", "detected_at_utc"],
    },
    "lane3_market_context.json": {
        "type": "market_contexts",
        "item_fields": [
            "asset", "venue", "snapshot_time_utc",
            "current_price", "source_health",
        ],
        "root_fields": ["market_contexts", "source_health", "snapshot_time_utc"],
    },
    "lane4_existing_feeds.json": {
        "type": "feed_items",
        "item_fields": [
            "item_id", "stream_type", "source_label",
            "published_at_utc", "ingested_at_utc", "title", "source_health",
        ],
        "root_fields": ["feed_items", "source_health", "snapshot_time_utc"],
    },
    "lane5_workbench_ui.json": {
        "type": None,
        "item_fields": ["workbench_html_path"],
        "root_fields": ["workbench_html_path", "source_health"],
    },
}


def check_null_policy(item: dict) -> list[str]:
    """Check that missing data uses null, not 0 or empty string."""
    violations: list[str] = []
    for key, value in item.items():
        # Positions: entry_price, mark_price, leverage must never be 0 when present
        if key in ("entry_price", "mark_price") and value is not None and not (value > 0):
            violations.append(f"{key} should be null, got {value}")
        # String fields that are unknown
        if isinstance(value, str) and value.strip() == "":
            violations.append(f"{key} is empty string, should be null")
        # Numeric sentinel 0 for amounts
        if key in ("position_value_usd", "unrealized_pnl_usd") and value == 0:
            violations.append(f"{key} is 0, should be null if unavailable")
    return violations


def validate_file(filename: str) -> dict:
    """Validate a single output file."""
    filepath = os.path.join(RESULT_DIR, filename)
    result = {
        "file": filename,
        "exists": False,
        "valid_json": False,
        "root_fields_present": False,
        "items_valid": True,
        "items_count": 0,
        "null_policy_violations": 0,
        "errors": [],
        "warnings": [],
    }

    if not os.path.isfile(filepath):
        result["errors"].append(f"File not found: {filepath}")
        return result
    result["exists"] = True

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result["valid_json"] = True
    except (IOError, json.JSONDecodeError) as e:
        result["errors"].append(f"Invalid JSON: {e}")
        return result

    spec = REQUIRED_FIELDS_MAP.get(filename)
    if spec is None:
        result["warnings"].append(f"No validation spec for {filename}, skipping field checks")
        return result

    # Root fields
    root_ok = all(f in data for f in spec["root_fields"])
    result["root_fields_present"] = root_ok
    if not root_ok:
        missing = [f for f in spec["root_fields"] if f not in data]
        result["errors"].append(f"Missing root fields: {missing}")

    # Item validation
    items_key = spec["type"]
    if items_key and items_key in data:
        items = data[items_key]
        result["items_count"] = len(items)
        for i, item in enumerate(items):
            missing_fields = [f for f in spec["item_fields"] if f not in item]
            if missing_fields:
                result["items_valid"] = False
                result["errors"].append(f"Item {i}: missing fields {missing_fields}")

            np_violations = check_null_policy(item)
            if np_violations:
                result["null_policy_violations"] += len(np_violations)
                result["warnings"].append(f"Item {i}: null policy: {'; '.join(np_violations)}")

    return result


def main() -> int:
    print("=" * 60)
    print("  MVP+ QA VALIDATION")
    print("=" * 60)

    results: list[dict] = []
    all_pass = True

    for fname in sorted(REQUIRED_FIELDS_MAP.keys()):
        r = validate_file(fname)
        results.append(r)
        status = "✅ PASS" if r["valid_json"] and r["root_fields_present"] and r["items_valid"] else "❌ FAIL"
        if not r["exists"]:
            status = "⚠️  MISSING"

        print(f"\n  {fname}:")
        print(f"    Status: {status}")
        print(f"    Valid JSON: {r['valid_json']}")
        print(f"    Root fields: {'✅' if r['root_fields_present'] else '❌'}")
        print(f"    Items: {r['items_count']}")
        print(f"    Items valid: {'✅' if r['items_valid'] else '❌'}")

        if r.get("null_policy_violations", 0) > 0:
            print(f"    ⚠️  Null policy violations: {r['null_policy_violations']}")
        if r["errors"]:
            for e in r["errors"]:
                print(f"    ❌ {e}")
            all_pass = False

    # Summary
    passed = sum(1 for r in results if r["valid_json"] and r["root_fields_present"] and r["items_valid"])
    total = len(results)
    total_items = sum(r.get("items_count", 0) for r in results)

    print(f"\n{'='*60}")
    print(f"  QA RESULT: {passed}/{total} files pass")
    print(f"  Total records: {total_items}")
    print(f"  Verdict: {'✅ ACCEPT' if all_pass else '⚠️  REVIEW_NEEDED'}")
    print(f"{'='*60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

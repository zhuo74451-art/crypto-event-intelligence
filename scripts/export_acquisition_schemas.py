#!/usr/bin/env python3
"""Export acquisition JSON schemas and verify they exist and are valid."""
import argparse
import json
import os
import sys

SCHEMA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "schemas", "acquisition", "v1"))
SCHEMA_FILES = [
    "source_contract.schema.json",
    "source_registry.schema.json",
    "acquisition_timestamp.schema.json",
    "raw_document.schema.json",
    "normalized_observation.schema.json",
    "revision.schema.json",
    "source_health.schema.json",
    "replay_snapshot.schema.json",
    "evidence_manifest.schema.json",
]


def check_schemas() -> bool:
    all_ok = True
    for fname in SCHEMA_FILES:
        path = os.path.join(SCHEMA_DIR, fname)
        if not os.path.exists(path):
            print(f"MISSING: {fname}")
            all_ok = False
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            print(f"OK: {fname} — {schema.get('title', 'untitled')} (v{schema.get('$schema', '?')})")
        except json.JSONDecodeError as e:
            print(f"INVALID JSON: {fname} — {e}")
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Export/check acquisition schemas")
    parser.add_argument("--check", action="store_true", help="Check schemas only")
    args = parser.parse_args()

    ok = check_schemas()
    if args.check:
        sys.exit(0 if ok else 1)
    else:
        print(f"\n{'All schemas valid.' if ok else 'Some schemas have issues.'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

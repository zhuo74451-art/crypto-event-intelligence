#!/usr/bin/env python
"""
Export validation schemas and optionally validate them against reference files.
"""
import json
import sys
from pathlib import Path


SCHEMAS_DIR = Path("schemas/validation/v1")
SCHEMA_FILES = [
    "dataset.schema.json",
    "data_availability.schema.json",
    "label.schema.json",
    "split.schema.json",
    "prediction.schema.json",
    "experiment_spec.schema.json",
    "experiment_result.schema.json",
    "calibration_artifact.schema.json",
    "evaluation_report.schema.json",
    "reproducibility_manifest.schema.json",
]


def export_schemas(output_dir: str = "schemas/validation/v1") -> list[Path]:
    """Export all schema files and return their paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in SCHEMA_FILES:
        src = SCHEMAS_DIR / name
        if src.exists():
            paths.append(src)
            print(f"  [OK] {name}")
        else:
            print(f"  [WARN] {name} not found at {src}")
    return paths


def check_schemas() -> bool:
    """Validate that all schema files parse correctly."""
    import jsonschema

    all_ok = True
    for name in SCHEMA_FILES:
        path = SCHEMAS_DIR / name
        if not path.exists():
            print(f"  [MISSING] {name}")
            all_ok = False
            continue
        try:
            with open(path) as f:
                schema = json.load(f)
            jsonschema.Draft7Validator.check_schema(schema)
            print(f"  [VALID] {name}")
        except Exception as e:
            print(f"  [INVALID] {name}: {e}")
            all_ok = False
    return all_ok


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export/validate validation schemas")
    parser.add_argument("--check", action="store_true", help="Validate schemas")
    args = parser.parse_args()

    if args.check:
        print("Checking validation schemas...")
        ok = check_schemas()
        sys.exit(0 if ok else 1)
    else:
        print("Exporting validation schemas...")
        export_schemas()
        print("Done.")


if __name__ == "__main__":
    main()

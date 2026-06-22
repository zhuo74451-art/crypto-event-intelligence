"""Export and validate JSON schemas."""
import json
import sys
from pathlib import Path

SCHEMA_DIR = Path("schemas/strategies/macro_scheduled/v1")
REQUIRED_SCHEMAS = [
    "release_calendar.schema.json", "expectation_snapshot.schema.json",
    "official_release.schema.json", "macro_surprise.schema.json",
    "component_interpretation.schema.json", "market_confirmation.schema.json",
    "priced_in.schema.json", "macro_assessment_proposal.schema.json",
    "validation_record.schema.json", "case_record.schema.json",
]


def validate_schemas():
    errors = []
    for name in REQUIRED_SCHEMAS:
        path = SCHEMA_DIR / name
        if not path.exists():
            errors.append(f"MISSING: {name}")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert "type" in data, f"{name}: missing 'type'"
            assert "properties" in data, f"{name}: missing 'properties'"
        except (json.JSONDecodeError, AssertionError) as e:
            errors.append(f"INVALID: {name} - {e}")
    return errors


if __name__ == "__main__":
    check = "--check" in sys.argv
    name = sys.argv[sys.argv.index("--check") + 1] if check and len(sys.argv) > sys.argv.index("--check") + 1 else None
    if name:
        path = SCHEMA_DIR / name
        if not path.exists():
            print(f"MISSING: {name}")
            sys.exit(1)
        with open(path) as f:
            json.load(f)
        print(f"VALID: {name}")
    else:
        errors = validate_schemas()
        if errors:
            for e in errors:
                print(e)
            sys.exit(1)
        print(f"All {len(REQUIRED_SCHEMAS)} schemas valid.")

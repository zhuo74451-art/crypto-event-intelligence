#!/usr/bin/env python3
"""Export all research intelligence dataclasses as JSON Schema v1 files.

Usage:
    python scripts/research_intelligence/export_schemas.py
    python scripts/research_intelligence/export_schemas.py --check
"""

import sys
import json
from dataclasses import MISSING, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Optional, Union, get_type_hints

# ── Add project root to sys.path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Imports ───────────────────────────────────────────────────────────────
from research.intelligence.contracts.source_record import ResearchSourceRecord
from research.intelligence.contracts.claim import ResearchClaim
from research.intelligence.contracts.conflict import ClaimConflict
from research.intelligence.contracts.coverage import CoverageDomain
from research.intelligence.contracts.knowledge_gap import KnowledgeGap
from research.intelligence.contracts.knowledge_decay import KnowledgeDecayRecord
from research.intelligence.contracts.unexplained_event import UnexplainedEvent
from research.intelligence.contracts.hypothesis import ResearchHypothesis
from research.intelligence.contracts.trader_profile import TraderProfile
from research.intelligence.contracts.capability import Capability
from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.contracts.strategy_candidate import (
    DatasetSpec,
    LabelSpec,
    BaselineSpec,
    SplitSpec,
    Specification,
    StrategyCandidate,
)
from research.intelligence.contracts.errors import ResearchError

# ── Schema output directory ──────────────────────────────────────────────
SCHEMA_DIR = PROJECT_ROOT / "schemas" / "research_intelligence" / "v1"

# ── All schema-able dataclasses ──────────────────────────────────────────
SCHEMA_CLASSES: list[tuple[str, type]] = [
    ("ResearchSourceRecord", ResearchSourceRecord),
    ("ResearchClaim", ResearchClaim),
    ("ClaimConflict", ClaimConflict),
    ("CoverageDomain", CoverageDomain),
    ("KnowledgeGap", KnowledgeGap),
    ("KnowledgeDecayRecord", KnowledgeDecayRecord),
    ("UnexplainedEvent", UnexplainedEvent),
    ("ResearchHypothesis", ResearchHypothesis),
    ("TraderProfile", TraderProfile),
    ("Capability", Capability),
    ("StrategySeed", StrategySeed),
    ("DatasetSpec", DatasetSpec),
    ("LabelSpec", LabelSpec),
    ("BaselineSpec", BaselineSpec),
    ("SplitSpec", SplitSpec),
    ("Specification", Specification),
    ("StrategyCandidate", StrategyCandidate),
    ("ResearchError", ResearchError),
]


def type_to_jsonschema(tp: type) -> dict:
    """Roughly map Python types to JSON Schema type objects."""
    origin = getattr(tp, "__origin__", None)
    if origin is not None:
        # GenericAlias like list[str], dict[str, Any], Optional[str]
        if origin is list:
            item_type = tp.__args__[0] if tp.__args__ else str
            return {"type": "array", "items": type_to_jsonschema(item_type)}
        if origin is dict:
            return {"type": "object", "additionalProperties": True}
        if origin is Union:
            # Handle Optional[X] → Union[X, None]
            args = [a for a in tp.__args__ if a is not type(None)]
            if len(args) == 1:
                return type_to_jsonschema(args[0])
            return {"oneOf": [type_to_jsonschema(a) for a in args]}

    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp in (Any,):
        return {}
    if isinstance(tp, type) and issubclass(tp, (str, int, float, bool)):
        return {"type": "string"}  # enum subclass
    if isinstance(tp, type) and issubclass(tp, Exception):
        return {"type": "object"}
    return {"type": "string"}


def dataclass_to_jsonschema(cls: type) -> dict:
    """Convert a dataclass to a JSON Schema draft-07 schema."""
    assert is_dataclass(cls), f"{cls.__name__} is not a dataclass"
    hints = get_type_hints(cls)
    properties = {}
    required = []

    for f in fields(cls):
        f_type = hints.get(f.name, str)
        prop = type_to_jsonschema(f_type)

        # Add description from field metadata if available
        if f.metadata:
            desc = f.metadata.get("description", "")
            if desc:
                prop["description"] = desc

        # Check for default → not required
        is_required = (
            f.default is MISSING
            and f.default_factory is MISSING  # type: ignore[comparison-overlap]
        )
        # Optional fields (Union[X, None]) are never required
        origin = getattr(f_type, "__origin__", None)
        if origin is Union and type(None) in f_type.__args__:
            is_required = False

        if is_required:
            required.append(f.name)

        properties[f.name] = prop

    schema: dict = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://research-intelligence/v1/schemas/{cls.__name__}.json",
        "title": cls.__name__,
        "description": (cls.__doc__ or "").strip(),
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def export_schemas(check: bool = False) -> bool:
    """Export all schemas to SCHEMA_DIR. If check=True, only verify they match.

    Returns True if all schemas are up-to-date (check mode) or exported (write mode).
    """
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for name, cls in SCHEMA_CLASSES:
        schema = dataclass_to_jsonschema(cls)
        file_path = SCHEMA_DIR / f"{name}.json"

        if check:
            if file_path.exists():
                existing = json.loads(file_path.read_text(encoding="utf-8"))
                if existing != schema:
                    print(f"[CHECK-FAILED] {name}.json differs from generated schema")
                    all_ok = False
                else:
                    print(f"[OK] {name}.json")
            else:
                print(f"[MISSING] {name}.json does not exist")
                all_ok = False
        else:
            file_path.write_text(json.dumps(schema, indent=2, default=str), encoding="utf-8")
            print(f"[EXPORTED] {name}.json")

    return all_ok


def main() -> None:
    check = "--check" in sys.argv
    ok = export_schemas(check=check)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

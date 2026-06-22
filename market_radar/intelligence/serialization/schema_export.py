"""Schema export — deterministic JSON Schema generation from Python models.

Python models are the single source of truth. JSON Schema files are
deterministically exported and checked for drift.
"""

from __future__ import annotations

import json
import os
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, get_type_hints, _GenericAlias  # type: ignore


def _type_to_schema_type(tp: Any) -> dict:
    """Convert a Python type to a JSON Schema type definition."""
    origin = getattr(tp, "__origin__", None)
    args = getattr(tp, "__args__", ())

    if origin is list:
        item_type = args[0] if args else Any
        return {"type": "array", "items": _type_to_schema_type(item_type)}
    elif origin is dict:
        return {"type": "object"}
    elif origin is Optional or origin is Union:  # noqa: F821
        # Check if it's Optional[SomeType]
        non_none = [a for a in args if a is not type(None)]  # noqa: E721
        if non_none:
            schema = _type_to_schema_type(non_none[0])
            # Don't add null — JSON Schema handles this differently
            return schema
        return {}

    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp in (Decimal,):
        return {"type": "string", "pattern": r"^-?\d+(\.\d+)?$"}
    if tp in (datetime,):
        return {"type": "string", "format": "date-time"}
    if isinstance(tp, type) and issubclass(tp, Enum):
        return {
            "type": "string",
            "enum": [e.value for e in tp],
        }
    if is_dataclass(tp):
        return _dataclass_to_schema(tp)

    return {}


def _is_optional(tp: Any) -> bool:
    """Check if a type is Optional."""
    origin = getattr(tp, "__origin__", None)
    if origin is Union:  # noqa: F821
        args = getattr(tp, "__args__", ())
        return type(None) in args  # noqa: E721
    return False


def _dataclass_to_schema(dc: type) -> dict:
    """Convert a dataclass type to a JSON Schema object definition."""
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for f in fields(dc):
        if f.name.startswith("_"):
            continue
        # Skip Optional fields as "not required" in JSON Schema sense
        is_optional = _is_optional(f.type)
        if not is_optional:
            schema["required"].append(f.name)

        prop_schema = _type_to_schema_type(f.type)
        if f.default is not None and f.default != dataclasses.MISSING:  # noqa: F821
            prop_schema.setdefault("default", _get_default(f))
        schema["properties"][f.name] = prop_schema

    if not schema["required"]:
        schema.pop("required")
    return schema


def _get_default(f) -> Any:
    """Get the default value for a dataclass field."""
    import dataclasses  # noqa: F811
    if f.default is not dataclasses.MISSING:
        if isinstance(f.default, Enum):
            return f.default.value
        if is_dataclass(f.default):
            return None  # Can't represent a complex default
        return f.default
    if f.default_factory is not dataclasses.MISSING:
        return None  # Factory defaults are dynamic
    return None


def export_schema(model_class: type, title: str = "") -> dict:
    """Export a Python model class to a JSON Schema dict."""
    schema = _dataclass_to_schema(model_class)
    schema["title"] = title or model_class.__name__
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["version"] = "1.0.0"
    return schema


def write_schema(model_class: type, output_path: str) -> None:
    """Export a model to JSON Schema and write to a file."""
    schema = export_schema(model_class)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False, sort_keys=True)


def check_schema_drift(model_class: type, schema_path: str) -> bool:
    """Check if the on-disk schema matches the model.

    Returns True if they match (no drift), False if drift is detected.
    """
    if not os.path.exists(schema_path):
        return False

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            on_disk = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    current = export_schema(model_class)

    # Canonical comparison
    return json.dumps(on_disk, sort_keys=True) == json.dumps(current, sort_keys=True)


# Import needed for type checking in _is_optional
from typing import Union as Union  # noqa: F811, E402
import dataclasses  # noqa: F402, E402

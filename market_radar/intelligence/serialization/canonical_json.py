"""Canonical JSON serialization — deterministic, key-sorted, UTC-normalized."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


def _canonical_value(val: Any) -> Any:
    """Convert a value to its canonical JSON-safe form."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val:  # NaN
            return "NaN"
        if val == float('inf'):
            return "Infinity"
        if val == float('-inf'):
            return "-Infinity"
        return round(val, 10)
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, datetime):
        if val.tzinfo is None:
            raise ValueError(f"Naive datetime cannot be serialized: {val}")
        return val.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
    if isinstance(val, dict):
        return {str(k): _canonical_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_canonical_value(v) for v in val]
    if hasattr(val, "to_dict"):
        return _canonical_value(val.to_dict())
    return str(val)


def canonical_json(data: Any, indent: int = 2) -> str:
    """Serialize data to canonical JSON (key-sorted, deterministic).

    Same input always produces byte-identical output.
    """
    cleaned = _canonical_value(data)
    return json.dumps(
        cleaned,
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        allow_nan=False,
    )


def canonical_json_bytes(data: Any, indent: int = 2) -> bytes:
    """Serialize data to canonical JSON bytes."""
    return canonical_json(data, indent).encode("utf-8")

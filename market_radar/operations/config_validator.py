"""Configuration validation for operations tasks.

Validates a config dict against a schema of required and optional fields.
No business domain constants.
"""

from __future__ import annotations

from typing import Any, Optional


def validate_config(
    config: dict[str, Any],
    required: Optional[list[str]] = None,
    allowed: Optional[list[str]] = None,
    types: Optional[dict[str, type]] = None,
) -> list[str]:
    """Validate a config dict.

    Args:
        config: The config dict to validate.
        required: Fields that must be present and non-None.
        allowed: If given, only these field names are permitted.
        types: If given, {field: expected_type} assertions.

    Returns:
        List of violation strings (empty = valid).
    """
    violations: list[str] = []

    if required:
        for field in required:
            if field not in config or config[field] is None:
                violations.append(f"missing required field: '{field}'")

    if allowed is not None:
        for key in config:
            if key not in allowed:
                violations.append(f"unknown config field: '{key}'")

    if types:
        for field, expected in types.items():
            if field in config and config[field] is not None:
                if not isinstance(config[field], expected):
                    violations.append(
                        f"field '{field}' expected {expected.__name__}, "
                        f"got {type(config[field]).__name__}"
                    )

    return violations

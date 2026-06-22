"""Compatibility report for legacy-to-new contract mappings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FieldMapping:
    """Record of a single field mapping from legacy to new contract."""
    legacy_field: str = ""
    new_field: str = ""
    quality: str = "direct_map"  # direct_map | derived_map | lossy_map | unsupported | deprecated
    note: str = ""


@dataclass
class CompatibilityReport:
    """Summary of legacy compatibility for all mapped modules."""
    total_legacy_objects: int = 0
    successful_mappings: int = 0
    failed_mappings: int = 0
    lossy_fields: list[dict] = field(default_factory=list)
    unsupported_objects: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    field_mappings: list[FieldMapping] = field(default_factory=list)

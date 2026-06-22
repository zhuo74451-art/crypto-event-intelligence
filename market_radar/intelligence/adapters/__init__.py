"""Legacy read-only adapters for existing intelligence models."""

from .legacy_observation import LegacyObservationAdapter
from .legacy_signal_registry import LegacySignalRegistryAdapter
from .compatibility_report import CompatibilityReport, FieldMapping

__all__ = [
    "LegacyObservationAdapter", "LegacySignalRegistryAdapter",
    "CompatibilityReport", "FieldMapping",
]

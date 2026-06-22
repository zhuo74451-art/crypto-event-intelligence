"""
Validation dataset contract — immutable dataset specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import PointInTimeMode, ValidationEventIdentity, stable_fingerprint


@dataclass(frozen=True)
class SourceManifestEntry:
    source_id: str
    source_type: str
    retrieval_timestamps: list[datetime] = field(default_factory=list)
    content_hashes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EventManifestEntry:
    event_cluster_id: str
    primary_source_id: str
    event_type: str
    assets: list[str] = field(default_factory=list)
    revision_count: int = 0


@dataclass(frozen=True)
class DatasetManifest:
    """Immutable manifest for a validation dataset."""

    source_manifest: list[SourceManifestEntry] = field(default_factory=list)
    event_manifest: list[EventManifestEntry] = field(default_factory=list)
    revision_manifest: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class DatasetIdentity:
    """Identity and version for an immutable dataset."""

    dataset_id: str
    dataset_version: str
    created_at: datetime
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", self._compute_fingerprint())

    def _compute_fingerprint(self) -> str:
        data = {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
        }
        return stable_fingerprint(data)


@dataclass(frozen=True)
class DatasetSpecification:
    """Complete specification of a validation dataset."""

    dataset_id: str
    dataset_version: str
    created_at: datetime

    observation_cutoff_policy: str = "strict_as_known_then"
    label_maturity_policy: str = "require_mature"

    source_manifest: DatasetManifest = field(default_factory=DatasetManifest)

    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None

    point_in_time_mode: PointInTimeMode = PointInTimeMode.STRICT_AS_KNOWN_THEN

    known_leakage_risks: list[str] = field(default_factory=list)
    known_measurement_risks: list[str] = field(default_factory=list)
    known_missingness: list[str] = field(default_factory=list)

    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", self._compute_fingerprint())

    def _compute_fingerprint(self) -> str:
        data = {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "point_in_time_mode": self.point_in_time_mode.value,
            "observation_cutoff_policy": self.observation_cutoff_policy,
            "label_maturity_policy": self.label_maturity_policy,
            "known_leakage_risks": sorted(self.known_leakage_risks),
        }
        return stable_fingerprint(data)

    def assert_immutable(self) -> None:
        """Assert this dataset specification is frozen for use."""
        # In V1, immutability is enforced by convention and fingerprint.
        pass

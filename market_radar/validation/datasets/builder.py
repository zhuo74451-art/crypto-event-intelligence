"""
Immutable dataset builder — constructs validation datasets with fingerprinting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..contracts.dataset import DatasetSpecification, DatasetManifest
from ..contracts.common import stable_fingerprint
from ..contracts.errors import DatasetFingerprintMismatchError


@dataclass(frozen=True)
class BuiltDataset:
    """An immutable built dataset ready for use in experiments."""

    spec: DatasetSpecification
    records: list[dict[str, Any]] = field(default_factory=list)
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", self._compute_fingerprint())

    def _compute_fingerprint(self) -> str:
        data = {
            "spec_fingerprint": self.spec.fingerprint,
            "n_records": len(self.records),
        }
        return stable_fingerprint(data)

    def verify_fingerprint(self, expected_fingerprint: str) -> None:
        """Verify dataset integrity against an expected fingerprint."""
        if self.fingerprint != expected_fingerprint:
            raise DatasetFingerprintMismatchError(
                detail=(
                    f"Expected fingerprint {expected_fingerprint}, "
                    f"got {self.fingerprint}"
                ),
                object_id=self.spec.dataset_id,
                min_fix="Rebuild the dataset from the original specification",
            )


class DatasetBuilder:
    """Builds immutable validation datasets."""

    def __init__(self):
        self._built: dict[str, BuiltDataset] = {}

    def build_from_records(
        self,
        spec: DatasetSpecification,
        records: list[dict[str, Any]],
    ) -> BuiltDataset:
        """Build an immutable dataset from records."""
        dataset = BuiltDataset(spec=spec, records=records)
        self._built[spec.dataset_id] = dataset
        return dataset

    def get(self, dataset_id: str) -> Optional[BuiltDataset]:
        return self._built.get(dataset_id)

    def list_datasets(self) -> list[str]:
        return list(self._built.keys())

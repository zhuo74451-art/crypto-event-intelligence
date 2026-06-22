"""
Experiment registry — tracks all experiments with their status and artifacts.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..contracts.experiment import (
    ExperimentSpecification,
    ExperimentRegistration,
    TrialRecord,
    ReproducibilityManifest,
)
from ..contracts.common import ExperimentStatus
from ..contracts.errors import (
    InvalidExperimentStateError,
    ExperimentSpecNotFrozenError,
    FailedExperimentDeletedError,
)


class ExperimentRegistry:
    """Registry for managing experiment lifecycle.

    States: draft → frozen → running → completed | failed | invalidated | superseded
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._registrations: dict[str, ExperimentRegistration] = {}
        self._trials: dict[str, list[TrialRecord]] = {}
        self._storage_path = storage_path

    def register(self, spec: ExperimentSpecification) -> ExperimentRegistration:
        """Register a new experiment in draft state."""
        if spec.experiment_id in self._registrations:
            raise InvalidExperimentStateError(
                detail=f"Experiment {spec.experiment_id} already registered",
                object_id=spec.experiment_id,
                min_fix="Use a new experiment_id or create a new version",
            )

        reg = ExperimentRegistration(
            spec=spec,
            status=ExperimentStatus.DRAFT,
        )
        self._registrations[spec.experiment_id] = reg
        self._trials[spec.experiment_id] = []
        return reg

    def freeze(self, experiment_id: str) -> ExperimentRegistration:
        """Freeze an experiment specification (transition draft → frozen)."""
        reg = self._get(experiment_id)
        if reg.status != ExperimentStatus.DRAFT:
            raise InvalidExperimentStateError(
                detail=f"Cannot freeze experiment in state {reg.status.value}",
                object_id=experiment_id,
                min_fix="Only draft experiments can be frozen",
            )

        updated = ExperimentRegistration(
            spec=reg.spec,
            status=ExperimentStatus.FROZEN,
            data_fingerprint=reg.data_fingerprint,
            code_sha=reg.code_sha,
            python_version=reg.python_version,
            random_seed=reg.random_seed,
        )
        self._registrations[experiment_id] = updated
        return updated

    def start(self, experiment_id: str) -> ExperimentRegistration:
        """Start running an experiment (transition frozen → running)."""
        reg = self._get(experiment_id)
        if reg.status != ExperimentStatus.FROZEN:
            raise InvalidExperimentStateError(
                detail=f"Cannot start experiment in state {reg.status.value}",
                object_id=experiment_id,
                min_fix="Freeze the experiment specification first",
            )

        updated = ExperimentRegistration(
            spec=reg.spec,
            status=ExperimentStatus.RUNNING,
            data_fingerprint=reg.data_fingerprint,
            code_sha=reg.code_sha,
            python_version=reg.python_version,
            random_seed=reg.random_seed,
            started_at=datetime.now(),
        )
        self._registrations[experiment_id] = updated
        return updated

    def complete(
        self,
        experiment_id: str,
        output_artifacts: Optional[list[str]] = None,
        stdout_summary: str = "",
    ) -> ExperimentRegistration:
        """Mark experiment as completed."""
        reg = self._get(experiment_id)
        if reg.status != ExperimentStatus.RUNNING:
            raise InvalidExperimentStateError(
                detail=f"Cannot complete experiment in state {reg.status.value}",
                object_id=experiment_id,
                min_fix="Start the experiment first",
            )

        finished_at = datetime.now()
        duration = (
            (finished_at - reg.started_at).total_seconds()
            if reg.started_at
            else None
        )

        updated = ExperimentRegistration(
            spec=reg.spec,
            status=ExperimentStatus.COMPLETED,
            data_fingerprint=reg.data_fingerprint,
            code_sha=reg.code_sha,
            python_version=reg.python_version,
            random_seed=reg.random_seed,
            output_artifact_paths=output_artifacts or reg.output_artifact_paths,
            stdout_summary=stdout_summary or reg.stdout_summary,
            started_at=reg.started_at,
            finished_at=finished_at,
            duration_seconds=duration,
        )
        self._registrations[experiment_id] = updated
        return updated

    def fail(
        self,
        experiment_id: str,
        failure_reason: str = "",
        partial_results: Optional[list[str]] = None,
    ) -> ExperimentRegistration:
        """Mark experiment as failed."""
        reg = self._get(experiment_id)

        finished_at = datetime.now()
        duration = (
            (finished_at - reg.started_at).total_seconds()
            if reg.started_at
            else None
        )

        updated = ExperimentRegistration(
            spec=reg.spec,
            status=ExperimentStatus.FAILED,
            data_fingerprint=reg.data_fingerprint,
            code_sha=reg.code_sha,
            python_version=reg.python_version,
            random_seed=reg.random_seed,
            failure_reason=failure_reason,
            output_artifact_paths=partial_results or reg.output_artifact_paths,
            started_at=reg.started_at,
            finished_at=finished_at,
            duration_seconds=duration,
        )
        self._registrations[experiment_id] = updated
        return updated

    def invalidate(
        self,
        experiment_id: str,
        reason: str = "",
    ) -> ExperimentRegistration:
        """Invalidate an experiment (e.g., for leakage)."""
        reg = self._get(experiment_id)
        if reg.status == ExperimentStatus.COMPLETED:
            pass  # allow invalidation of completed experiments

        updated = ExperimentRegistration(
            spec=reg.spec,
            status=ExperimentStatus.INVALIDATED,
            data_fingerprint=reg.data_fingerprint,
            code_sha=reg.code_sha,
            python_version=reg.python_version,
            random_seed=reg.random_seed,
            failure_reason=reason or "Invalidated due to information leakage",
            started_at=reg.started_at,
            finished_at=reg.finished_at or datetime.now(),
        )
        self._registrations[experiment_id] = updated
        return updated

    def delete(self, experiment_id: str) -> None:
        """Delete an experiment — raises error."""
        raise FailedExperimentDeletedError(
            detail=f"Cannot delete experiment {experiment_id}",
            object_id=experiment_id,
            min_fix="Failed experiments must be preserved in the archive",
        )

    def add_trial(
        self,
        experiment_id: str,
        trial: TrialRecord,
    ) -> None:
        """Add a trial record to an experiment."""
        if experiment_id not in self._trials:
            self._trials[experiment_id] = []
        self._trials[experiment_id].append(trial)

    def get_trials(self, experiment_id: str) -> list[TrialRecord]:
        """Get all trials for an experiment."""
        return self._trials.get(experiment_id, [])

    def get(self, experiment_id: str) -> Optional[ExperimentRegistration]:
        """Get experiment registration."""
        return self._registrations.get(experiment_id)

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
    ) -> list[ExperimentRegistration]:
        """List all experiments, optionally filtered by status."""
        if status:
            return [
                reg for reg in self._registrations.values()
                if reg.status == status
            ]
        return list(self._registrations.values())

    def _get(self, experiment_id: str) -> ExperimentRegistration:
        if experiment_id not in self._registrations:
            raise InvalidExperimentStateError(
                detail=f"Experiment {experiment_id} not found",
                object_id=experiment_id,
                min_fix="Register the experiment first",
            )
        return self._registrations[experiment_id]

    def save(self) -> None:
        """Persist registry to disk if storage_path is configured."""
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            eid: {
                "status": reg.status.value,
                "experiment_id": reg.spec.experiment_id,
                "experiment_version": reg.spec.experiment_version,
                "data_fingerprint": reg.data_fingerprint,
                "code_sha": reg.code_sha,
                "failure_reason": reg.failure_reason,
            }
            for eid, reg in self._registrations.items()
        }
        path.write_text(json.dumps(data, indent=2, default=str))

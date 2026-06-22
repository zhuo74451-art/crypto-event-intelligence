"""
Validation error contracts — all error codes used by the validation system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class ValidationError(Exception):
    """Base validation error with stable error code."""

    code: str = "VALIDATION_ERROR"
    detail: str = ""
    object_id: str = ""
    min_fix: str = ""

    def __init__(
        self,
        code: str = "",
        detail: str = "",
        object_id: str = "",
        min_fix: str = "",
    ):
        self.code = code or self.code
        self.detail = detail or self.detail
        self.object_id = object_id or self.object_id
        self.min_fix = min_fix or self.min_fix
        super().__init__(f"[{self.code}] {self.detail} (object: {self.object_id})")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "object_id": self.object_id,
            "min_fix": self.min_fix,
        }


# ─── Dataset errors ──────────────────────────────────────────────────────────


class DatasetNotFoundError(ValidationError):
    code = "DATASET_NOT_FOUND"


class DatasetFingerprintMismatchError(ValidationError):
    code = "DATASET_FINGERPRINT_MISMATCH"


class DatasetNotPointInTimeError(ValidationError):
    code = "DATASET_NOT_POINT_IN_TIME"


# ─── Leakage errors ──────────────────────────────────────────────────────────


class FutureInformationLeakError(ValidationError):
    code = "FUTURE_INFORMATION_LEAK"


class LabelNotMatureError(ValidationError):
    code = "LABEL_NOT_MATURE"


class RevisionLeakError(ValidationError):
    code = "REVISION_LEAK"


class GroupSplitLeakError(ValidationError):
    code = "GROUP_SPLIT_LEAK"


class SourceDependenceLeakError(ValidationError):
    code = "SOURCE_DEPENDENCE_LEAK"


class TrainTestTimeOverlapError(ValidationError):
    code = "TRAIN_TEST_TIME_OVERLAP"


class PurgeWindowViolationError(ValidationError):
    code = "PURGE_WINDOW_VIOLATION"


class EmbargoViolationError(ValidationError):
    code = "EMBARGO_VIOLATION"


class HoldoutReusedForSelectionError(ValidationError):
    code = "HOLDOUT_REUSED_FOR_SELECTION"


class TargetInFeaturesError(ValidationError):
    code = "TARGET_IN_FEATURES"


# ─── Experiment errors ───────────────────────────────────────────────────────


class InvalidExperimentStateError(ValidationError):
    code = "INVALID_EXPERIMENT_STATE"


class ExperimentSpecNotFrozenError(ValidationError):
    code = "EXPERIMENT_SPEC_NOT_FROZEN"


# ─── Baseline errors ─────────────────────────────────────────────────────────


class BaselineMissingError(ValidationError):
    code = "BASELINE_MISSING"


# ─── Calibration errors ──────────────────────────────────────────────────────


class CalibrationSampleTooSmallError(ValidationError):
    code = "CALIBRATION_SAMPLE_TOO_SMALL"


class CalibrationArtifactMismatchError(ValidationError):
    code = "CALIBRATION_ARTIFACT_MISMATCH"


class ProbabilityOutOfRangeError(ValidationError):
    code = "PROBABILITY_OUT_OF_RANGE"


# ─── Testing errors ──────────────────────────────────────────────────────────


class MultipleTestingUndeclaredError(ValidationError):
    code = "MULTIPLE_TESTING_UNDECLARED"


class BootstrapMethodInvalidError(ValidationError):
    code = "BOOTSTRAP_METHOD_INVALID"


class RandomSeedMissingError(ValidationError):
    code = "RANDOM_SEED_MISSING"


class FailedExperimentDeletedError(ValidationError):
    code = "FAILED_EXPERIMENT_DELETED"


class PromotionNotAllowedError(ValidationError):
    code = "PROMOTION_NOT_ALLOWED"

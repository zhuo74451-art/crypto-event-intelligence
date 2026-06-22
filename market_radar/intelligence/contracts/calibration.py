"""Confidence and calibration contracts — P0 anti-spoofing for probability claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class ConfidenceType(str, Enum):
    QUALITATIVE = "qualitative"
    UNCALIBRATED_SCORE = "uncalibrated_score"
    EMPIRICAL_INTERVAL = "empirical_interval"
    CALIBRATED_PROBABILITY = "calibrated_probability"


@dataclass
class CalibrationArtifactRef(ContractBase):
    """Reference to a calibration artifact.

    Required for any `calibrated_probability` confidence statement.
    """
    contract_name: str = "CalibrationArtifactRef"
    schema_version: str = "1.0.0"

    calibration_artifact_id: str = ""
    calibration_method: str = ""
    validation_period: str = ""
    sample_size: int = 0
    out_of_sample: bool = True
    metric_summary: str = ""


@dataclass
class ConfidenceStatement(ContractBase):
    """A structured confidence statement.

    Rules:
    - calibrated_probability requires a CalibrationArtifactRef
    - uncalibrated_score must have production_probability=False
    - qualitative must state its basis
    """
    contract_name: str = "ConfidenceStatement"
    schema_version: str = "1.0.0"

    confidence_type: ConfidenceType = ConfidenceType.QUALITATIVE
    value: str = "medium"
    basis: str = ""

    # Calibrated probability fields
    probability_value: Optional[float] = None
    calibration_artifact: Optional[CalibrationArtifactRef] = None

    # Uncalibrated score marker
    production_probability: Optional[bool] = None

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.confidence_type, str):
            self.confidence_type = ConfidenceType(self.confidence_type)
        if isinstance(self.calibration_artifact, dict):
            self.calibration_artifact = CalibrationArtifactRef(**self.calibration_artifact)

    def validate(self) -> list[str]:
        """Validate confidence statement rules."""
        errors = []
        if self.confidence_type == ConfidenceType.CALIBRATED_PROBABILITY:
            if not self.calibration_artifact:
                errors.append("calibrated_probability requires a CalibrationArtifactRef")
            elif not self.calibration_artifact.calibration_artifact_id:
                errors.append("CalibrationArtifactRef must have an artifact ID")
            elif self.calibration_artifact.sample_size <= 0:
                errors.append("CalibrationArtifactRef must have sample_size > 0")
            elif not self.calibration_artifact.out_of_sample:
                errors.append("CalibrationArtifactRef must be out_of_sample=True")
        if self.confidence_type == ConfidenceType.UNCALIBRATED_SCORE:
            if self.production_probability is None:
                errors.append("uncalibrated_score must set production_probability=False")
            elif self.production_probability:
                errors.append("uncalibrated_score cannot have production_probability=True")
        if self.confidence_type == ConfidenceType.QUALITATIVE:
            if not self.basis:
                errors.append("qualitative confidence must state its basis")
        return errors


class CalibratorProtocol:
    """Interface for calibration providers.

    V1 only implements the interface and validation guards — no real calibrator.
    """

    @staticmethod
    def validate_calibrated_confidence(statement: ConfidenceStatement) -> list[str]:
        return statement.validate()


@dataclass
class NoCalibrationAvailable(ContractBase):
    """Sentinel for when no calibration data exists."""
    contract_name: str = "NoCalibrationAvailable"
    schema_version: str = "1.0.0"

    reason: str = "No calibration artifact available for this strategy/event pair"

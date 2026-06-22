"""
Validation Stub — Produces validation records from strategy proposals.

The ValidationStub bridges the gap between the macro strategy's
hypothesis/assessment pipeline and the formal validation layer.
Each validation record captures:

- The original proposal that was validated.
- A pass / fail / warning status.
- A human-readable message.
- Optional structured diagnostics for downstream debugging.

This stub will be replaced by a full validation engine in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from .intelligence_kernel_stub import (
    MacroAssessmentProposal,
    MacroStrategyHypothesisProposal,
    MacroTransmissionProposal,
)


# ---------------------------------------------------------------------------
# Validation record type
# ---------------------------------------------------------------------------
@dataclass
class ValidationRecord:
    """A single validation output produced by the stub.

    Attributes:
        record_id:      Unique identifier for this validation record.
        source_type:    Type of the validated proposal
                        ("hypothesis" | "assessment" | "transmission").
        source_id:      ID of the validated proposal.
        status:         "pass" | "fail" | "warning".
        message:        Human-readable explanation.
        validated_at:   When the validation was performed.
        diagnostics:    Optional structured details (e.g. field-level errors).
    """

    record_id: str
    source_type: str
    source_id: str
    status: str  # "pass" | "fail" | "warning"
    message: str
    validated_at: datetime
    diagnostics: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Validation stub
# ---------------------------------------------------------------------------
class ValidationStub:
    """Stub validator that produces validation records from proposals.

    In stub mode the validation always returns ``pass`` unless the
    proposal contains obviously malformed data (e.g. empty IDs,
    confidence out of range, negative scores).  This allows the
    pipeline to be exercised end-to-end without a real validation
    engine.

    Usage::

        stub = ValidationStub()
        record = stub.validate_hypothesis(hypothesis_proposal)
        record = stub.validate_assessment(assessment_proposal)
        record = stub.validate_transmission(transmission_proposal)
    """

    _counter: int = 0

    # ------------------------------------------------------------------
    # Hypothesis validation
    # ------------------------------------------------------------------
    def validate_hypothesis(
        self,
        proposal: MacroStrategyHypothesisProposal,
    ) -> ValidationRecord:
        """Validate a hypothesis proposal.

        Checks performed (stub level):
            - hypothesis_id is not empty.
            - direction is one of "bullish", "bearish", "neutral".
            - confidence is between 0 and 1.
        """
        self._counter += 1
        errors: list[str] = []
        warnings: list[str] = []

        # --- field checks ---
        if not proposal.hypothesis_id:
            errors.append("hypothesis_id is empty")

        if proposal.direction not in ("bullish", "bearish", "neutral"):
            errors.append(
                f"direction={proposal.direction!r} not in "
                f"{{bullish, bearish, neutral}}"
            )

        if not (Decimal("0") <= proposal.confidence <= Decimal("1")):
            errors.append(
                f"confidence={proposal.confidence} outside [0, 1]"
            )

        # --- status ---
        if errors:
            status = "fail"
            message = "; ".join(errors)
        elif warnings:
            status = "warning"
            message = "; ".join(warnings)
        else:
            status = "pass"
            message = "Hypothesis proposal validated successfully."

        return ValidationRecord(
            record_id=f"val_hyp_{self._counter}",
            source_type="hypothesis",
            source_id=proposal.hypothesis_id,
            status=status,
            message=message,
            validated_at=datetime.utcnow(),
            diagnostics={"errors": errors, "warnings": warnings}
            if (errors or warnings)
            else None,
        )

    # ------------------------------------------------------------------
    # Assessment validation
    # ------------------------------------------------------------------
    def validate_assessment(
        self,
        proposal: MacroAssessmentProposal,
    ) -> ValidationRecord:
        """Validate an assessment proposal.

        Checks performed (stub level):
            - assessment_id is not empty.
            - hypothesis_id is not empty.
            - score is between 0 and 100.
        """
        self._counter += 1
        errors: list[str] = []
        warnings: list[str] = []

        if not proposal.assessment_id:
            errors.append("assessment_id is empty")

        if not proposal.hypothesis_id:
            errors.append("hypothesis_id is empty")

        if not (0.0 <= proposal.score <= 100.0):
            errors.append(
                f"score={proposal.score} outside [0, 100]"
            )

        if errors:
            status = "fail"
            message = "; ".join(errors)
        else:
            status = "pass"
            message = "Assessment proposal validated successfully."

        return ValidationRecord(
            record_id=f"val_asm_{self._counter}",
            source_type="assessment",
            source_id=proposal.assessment_id,
            status=status,
            message=message,
            validated_at=datetime.utcnow(),
            diagnostics={"errors": errors} if errors else None,
        )

    # ------------------------------------------------------------------
    # Transmission validation
    # ------------------------------------------------------------------
    def validate_transmission(
        self,
        proposal: MacroTransmissionProposal,
    ) -> ValidationRecord:
        """Validate a transmission proposal.

        Checks performed (stub level):
            - transmission_id is not empty.
            - hypothesis and assessment are present.
            - signal is one of "long", "short", "flat", or None.
        """
        self._counter += 1
        errors: list[str] = []
        warnings: list[str] = []

        if not proposal.transmission_id:
            errors.append("transmission_id is empty")

        if not isinstance(proposal.hypothesis, MacroStrategyHypothesisProposal):
            errors.append("hypothesis is missing or wrong type")

        if not isinstance(proposal.assessment, MacroAssessmentProposal):
            errors.append("assessment is missing or wrong type")

        if proposal.signal not in ("long", "short", "flat", None):
            errors.append(
                f"signal={proposal.signal!r} not in "
                f"{{long, short, flat, None}}"
            )

        if errors:
            status = "fail"
            message = "; ".join(errors)
        else:
            status = "pass"
            message = "Transmission proposal validated successfully."

        return ValidationRecord(
            record_id=f"val_trn_{self._counter}",
            source_type="transmission",
            source_id=proposal.transmission_id,
            status=status,
            message=message,
            validated_at=datetime.utcnow(),
            diagnostics={"errors": errors} if errors else None,
        )

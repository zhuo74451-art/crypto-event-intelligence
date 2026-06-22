"""
Strategy Trace — Deterministic execution trace for the macro strategy.

A ``StrategyTrace`` records every meaningful step that the strategy took
during a single replay, including:

- Input fixtures and their sources.
- Point-in-time snapshot details.
- Hypothesis formation (direction, confidence, supporting facts).
- Assessment scoring and rationale.
- Signal derivation.
- Validation outcome.
- Timing information for each step.

Traces are fully deterministic given the same inputs.  They support
serialisation to dict and JSON for debugging, auditing, and comparison
across different runs or strategy versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from ..adapters.intelligence_kernel_stub import (
    MacroAssessmentProposal,
    MacroStrategyHypothesisProposal,
    MacroTransmissionProposal,
)
from ..adapters.validation_stub import ValidationRecord
from ..replay.point_in_time_snapshot import PointInTimeSnapshot


# ---------------------------------------------------------------------------
# Trace step types
# ---------------------------------------------------------------------------
@dataclass
class TraceStep:
    """A single step recorded during strategy execution.

    Attributes:
        step_name:   Human-readable name for this step.
        timestamp:   When the step was executed.
        inputs:      Key inputs consumed by the step.
        outputs:     Key outputs produced by the step.
        duration_ms: Wall-clock time in milliseconds (approximate).
    """

    step_name: str
    timestamp: datetime
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------
@dataclass
class StrategyTrace:
    """Deterministic execution trace for one strategy replay.

    Attributes:
        trace_id:            Unique trace identifier.
        release_event_id:    The macro release event that was replayed.
        strategy_version:    Version identifier for the strategy code.
        started_at:          When execution began.
        completed_at:        When execution finished.
        steps:               Ordered list of ``TraceStep`` records.
        hypothesis:          The hypothesis that was formed (optional).
        assessment:          The assessment that was produced (optional).
        transmission:        The transmission that was sent (optional).
        validation:          The validation outcome (optional).
        snapshot:            Point-in-time snapshot (optional).
        extra:               Free-form metadata.
    """

    trace_id: str
    release_event_id: str
    strategy_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: list[TraceStep] = field(default_factory=list)
    hypothesis: Optional[MacroStrategyHypothesisProposal] = None
    assessment: Optional[MacroAssessmentProposal] = None
    transmission: Optional[MacroTransmissionProposal] = None
    validation: Optional[ValidationRecord] = None
    snapshot: Optional[PointInTimeSnapshot] = None
    extra: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Step recording
    # ------------------------------------------------------------------
    def record_step(
        self,
        step_name: str,
        *,
        inputs: Optional[dict[str, Any]] = None,
        outputs: Optional[dict[str, Any]] = None,
        duration_ms: float = 0.0,
    ) -> TraceStep:
        """Append a step to the trace and return it.

        Args:
            step_name:  Name of the step (e.g. "load_fixtures").
            inputs:     Dict of inputs consumed.
            outputs:    Dict of outputs produced.
            duration_ms: Approximate wall-clock duration in ms.

        Returns:
            The newly created ``TraceStep``.
        """
        step = TraceStep(
            step_name=step_name,
            timestamp=datetime.utcnow(),
            inputs=inputs or {},
            outputs=outputs or {},
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------
    def complete(self) -> None:
        """Mark the trace as completed."""
        self.completed_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        def _safe(val: Any) -> Any:
            if isinstance(val, Decimal):
                return float(val)
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, PointInTimeSnapshot):
                return val.as_dict()
            return val

        return {
            "trace_id": self.trace_id,
            "release_event_id": self.release_event_id,
            "strategy_version": self.strategy_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "steps": [
                {
                    "step_name": s.step_name,
                    "timestamp": s.timestamp.isoformat(),
                    "inputs": _safe(s.inputs),
                    "outputs": _safe(s.outputs),
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "hypothesis": (
                {
                    "id": self.hypothesis.hypothesis_id,
                    "direction": self.hypothesis.direction,
                    "confidence": float(self.hypothesis.confidence),
                    "triggered_at": self.hypothesis.triggered_at.isoformat(),
                    "supporting_facts": _safe(
                        self.hypothesis.supporting_facts
                    ),
                }
                if self.hypothesis
                else None
            ),
            "assessment": (
                {
                    "id": self.assessment.assessment_id,
                    "score": self.assessment.score,
                    "rationale": self.assessment.rationale,
                    "assessed_at": self.assessment.assessed_at.isoformat(),
                }
                if self.assessment
                else None
            ),
            "transmission": (
                {
                    "id": self.transmission.transmission_id,
                    "signal": self.transmission.signal,
                    "transmitted_at": (
                        self.transmission.transmitted_at.isoformat()
                        if self.transmission.transmitted_at
                        else None
                    ),
                }
                if self.transmission
                else None
            ),
            "validation": (
                {
                    "id": self.validation.record_id,
                    "status": self.validation.status,
                    "message": self.validation.message,
                    "validated_at": self.validation.validated_at.isoformat(),
                }
                if self.validation
                else None
            ),
            "snapshot": (
                self.snapshot.as_dict() if self.snapshot else None
            ),
            "extra": self.extra,
        }

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------
    def diff(self, other: "StrategyTrace") -> dict[str, list[str]]:
        """Return a dict of differences between two traces.

        Useful for regression testing: two traces of the same event
        should be identical if the strategy version and data are the
        same.

        Returns:
            A dict mapping field names to lists of differing values::

                {"hypothesis_direction": ["bullish", "bearish"], ...}
        """
        diffs: dict[str, list[str]] = {}

        def _cmp(key: str, a: Any, b: Any) -> None:
            if a != b:
                diffs.setdefault(key, []).extend([str(a), str(b)])

        _cmp("release_event_id", self.release_event_id, other.release_event_id)
        _cmp("strategy_version", self.strategy_version, other.strategy_version)
        _cmp("steps_count", len(self.steps), len(other.steps))

        if self.hypothesis and other.hypothesis:
            _cmp(
                "hypothesis_direction",
                self.hypothesis.direction,
                other.hypothesis.direction,
            )
            _cmp(
                "hypothesis_confidence",
                self.hypothesis.confidence,
                other.hypothesis.confidence,
            )
        if self.assessment and other.assessment:
            _cmp(
                "assessment_score",
                self.assessment.score,
                other.assessment.score,
            )
        if self.validation and other.validation:
            _cmp(
                "validation_status",
                self.validation.status,
                other.validation.status,
            )

        return diffs

    def __len__(self) -> int:
        """Return number of recorded steps."""
        return len(self.steps)

    def __getitem__(self, idx: int) -> TraceStep:
        """Index into recorded steps."""
        return self.steps[idx]
